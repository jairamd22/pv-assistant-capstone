"""dlt ingestion pipeline for the two REFERENCE corpora (labels and
regulations) into Postgres + pgvector.

Deliberately NOT for AEMS: adverse-event data is queried live at answer
time (see pv_assistant/aems.py) because AEMS is designed for real-time
access — bulk-ingesting it nightly would undermine the freshness that is
the platform's point. This pipeline handles the corpora that genuinely
change on a slower cadence (labels are versioned documents; regulations
change rarely).

Two sources:
- bundled snapshot (default): loads data/labels.csv + data/regulations.csv
- live openFDA labels (--live): fetches current SPL sections for the drugs
  in DRUGS from the openFDA drug/label endpoint, replacing the snapshot

Run:
    python ingestion/pipeline.py            # snapshot -> postgres
    python ingestion/pipeline.py --live     # openFDA -> postgres
Schedule it (cron / compose 'ingestion' service) to keep labels fresh.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import dlt
import pandas as pd
import requests

DRUGS = [
    "montelukast", "ciprofloxacin", "canagliflozin", "febuxostat",
    "gabapentin", "tofacitinib", "empagliflozin", "warfarin", "metformin",
    "atorvastatin", "sertraline", "lisinopril",
]

SPL_FIELDS = {
    "boxed_warning": "Boxed Warning",
    "contraindications": "Contraindications",
    "warnings_and_cautions": "Warnings and Precautions",
    "adverse_reactions": "Adverse Reactions",
    "drug_interactions": "Drug Interactions",
    "indications_and_usage": "Indications and Usage",
}


@dlt.resource(name="labels", write_disposition="replace")
def snapshot_labels():
    yield from pd.read_csv("data/labels.csv").to_dict(orient="records")


@dlt.resource(name="regulations", write_disposition="replace")
def snapshot_regulations():
    yield from pd.read_csv("data/regulations.csv").to_dict(orient="records")


@dlt.resource(name="labels", write_disposition="replace")
def live_labels():
    import hashlib
    from datetime import date
    for drug in DRUGS:
        url = ("https://api.fda.gov/drug/label.json"
               f'?search=openfda.generic_name:"{drug}"&limit=1')
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            print(f"  skip {drug}: HTTP {r.status_code}")
            continue
        results = r.json().get("results", [])
        if not results:
            continue
        spl = results[0]
        brand = (spl.get("openfda", {}).get("brand_name") or [drug])[0]
        for field, section_name in SPL_FIELDS.items():
            texts = spl.get(field)
            if not texts:
                continue
            text = " ".join(texts)[:8000]
            rid = hashlib.md5(f"{drug}|{field}|live".encode()).hexdigest()[:8]
            yield {
                "id": rid, "drug": drug, "brand": brand,
                "section_code": field, "section_name": section_name,
                "as_of_date": date.today().isoformat(),
                "version_note": "live openFDA fetch", "text": text,
            }


def embed_and_index():
    """After dlt load: add pgvector embeddings + tsvector columns."""
    import psycopg2
    from openai import OpenAI

    client = OpenAI()
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database=os.getenv("POSTGRES_DB", "pv_assistant"),
        user=os.getenv("POSTGRES_USER", "user"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
    )
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        for table, text_expr in [
            ("labels", "drug || ' ' || section_name || ' ' || text"),
            ("regulations", "citation || ' ' || title || ' ' || text"),
        ]:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS embedding vector(1536)")
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tsv tsvector")
            cur.execute(f"UPDATE {table} SET tsv = to_tsvector('english', {text_expr})")
            cur.execute(f"SELECT id, {text_expr} FROM {table} WHERE embedding IS NULL")
            rows = cur.fetchall()
            for i in range(0, len(rows), 64):
                batch = rows[i:i + 64]
                embs = client.embeddings.create(model=model, input=[r[1] for r in batch])
                for (rid, _), e in zip(batch, embs.data):
                    cur.execute(f"UPDATE {table} SET embedding = %s WHERE id = %s",
                                (e.embedding, rid))
            print(f"  embedded {len(rows)} rows in {table}")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="Fetch current labels from openFDA instead of the snapshot")
    args = parser.parse_args()

    pipeline = dlt.pipeline(
        pipeline_name="pv_corpora",
        destination=dlt.destinations.postgres(
            f"postgresql://{os.getenv('POSTGRES_USER','user')}:"
            f"{os.getenv('POSTGRES_PASSWORD','password')}@"
            f"{os.getenv('POSTGRES_HOST','localhost')}:5432/"
            f"{os.getenv('POSTGRES_DB','pv_assistant')}"
        ),
        dataset_name="public",
    )
    sources = [live_labels() if args.live else snapshot_labels(),
               snapshot_regulations()]
    info = pipeline.run(sources)
    print(info)
    print("Embedding + indexing for hybrid search...")
    embed_and_index()
    print("Done.")
