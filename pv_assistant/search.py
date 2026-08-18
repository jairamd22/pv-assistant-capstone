"""Retrieval layer for the two reference corpora (labels, regulations).

Two backends, selected with SEARCH_BACKEND:

- "memory"  (default) — vendored minsearch keyword index. Zero infra, used
  for local dev, offline demos, and as the keyword baseline in evaluation.
- "pgvector" — hybrid search in Postgres: semantic (vector cosine over
  OpenAI embeddings) + keyword (Postgres full-text ts_rank), fused with
  Reciprocal Rank Fusion (RRF). This is the production path and the
  portfolio's first hybrid-search implementation.

Why hybrid here and not in earlier projects: this domain's queries are
dense with exact identifiers — drug names, MedDRA terms, CFR citations —
where keyword matching adds real value over pure semantic similarity.
That claim is *measured* in notebooks/retrieval-eval.ipynb, not assumed.
"""

import os

import pandas as pd

from pv_assistant.minsearch import Index

SEARCH_BACKEND = os.getenv("SEARCH_BACKEND", "memory")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536

LABELS_PATH = os.getenv("LABELS_PATH", "data/labels.csv")
REGS_PATH = os.getenv("REGS_PATH", "data/regulations.csv")


# ---------------------------------------------------------------------------
# In-memory keyword backend
# ---------------------------------------------------------------------------

class MemoryLabelIndex:
    """Keyword search over the label snapshot, with as-of-date filtering.

    as_of filtering matters for the SrLC historical validation: "search the
    label as it stood BEFORE FDA required the change".
    """

    def __init__(self, path=LABELS_PATH):
        self.df = pd.read_csv(path)
        self._fit(self.df)

    def _fit(self, df):
        self.docs = df.to_dict(orient="records")
        self.index = Index(
            text_fields=["drug", "brand", "section_name", "text"],
            keyword_fields=["id", "drug"],
        )
        self.index.fit(self.docs)

    def search(self, query, drug=None, as_of=None, num_results=5):
        if as_of:
            # restrict to versions in effect at `as_of`: latest version per
            # (drug, section) with as_of_date <= as_of
            df = self.df[self.df.as_of_date <= as_of]
            df = (df.sort_values("as_of_date")
                    .groupby(["drug", "section_code"], as_index=False)
                    .tail(1))
            sub = MemoryLabelIndex.__new__(MemoryLabelIndex)
            sub.df = df
            sub._fit(df)
            return sub.search(query, drug=drug, num_results=num_results)

        filter_dict = {"drug": drug} if drug else {}
        return self.index.search(
            query=query, filter_dict=filter_dict,
            boost_dict={"drug": 1.5, "section_name": 0.8, "text": 1.6},
            num_results=num_results,
        )


class MemoryRegIndex:
    def __init__(self, path=REGS_PATH):
        docs = pd.read_csv(path).to_dict(orient="records")
        self.index = Index(
            text_fields=["citation", "title", "text"],
            keyword_fields=["id"],
        )
        self.index.fit(docs)

    def search(self, query, num_results=5):
        return self.index.search(
            query=query, filter_dict={},
            boost_dict={"citation": 2.0, "title": 1.2, "text": 1.5},
            num_results=num_results,
        )


# ---------------------------------------------------------------------------
# pgvector hybrid backend
# ---------------------------------------------------------------------------

HYBRID_SQL = """
WITH semantic AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(qvec)s::vector) AS rank
    FROM {table} {where}
    ORDER BY embedding <=> %(qvec)s::vector
    LIMIT 20
),
keyword AS (
    SELECT id, ROW_NUMBER() OVER (
        ORDER BY ts_rank_cd(tsv, plainto_tsquery('english', %(q)s)) DESC) AS rank
    FROM {table}
    WHERE tsv @@ plainto_tsquery('english', %(q)s) {where_kw}
    LIMIT 20
)
SELECT d.*, COALESCE(1.0/(60+s.rank), 0) + COALESCE(1.0/(60+k.rank), 0) AS rrf
FROM {table} d
LEFT JOIN semantic s ON d.id = s.id
LEFT JOIN keyword  k ON d.id = k.id
WHERE s.id IS NOT NULL OR k.id IS NOT NULL
ORDER BY rrf DESC
LIMIT %(k)s;
"""


class PgHybridIndex:
    """Hybrid semantic + keyword search over a pgvector-backed table.

    Tables are created/populated by ingestion/pipeline.py. Embeddings use
    the OpenAI embeddings API (no local model download needed in Docker).
    """

    def __init__(self, table):
        import psycopg2
        from openai import OpenAI
        self.table = table
        self.client = OpenAI()
        self.conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            database=os.getenv("POSTGRES_DB", "pv_assistant"),
            user=os.getenv("POSTGRES_USER", "user"),
            password=os.getenv("POSTGRES_PASSWORD", "password"),
        )

    def embed(self, text):
        resp = self.client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return resp.data[0].embedding

    def search(self, query, drug=None, as_of=None, num_results=5, mode="hybrid"):
        from psycopg2.extras import RealDictCursor
        qvec = self.embed(query) if mode in ("hybrid", "semantic") else None

        where, where_kw = "", ""
        params = {"q": query, "qvec": qvec, "k": num_results}
        if drug:
            where = "WHERE drug = %(drug)s"
            where_kw = "AND drug = %(drug)s"
            params["drug"] = drug
        if as_of:
            clause = "as_of_date <= %(as_of)s"
            where = (where + (" AND " if where else "WHERE ") + clause)
            where_kw += f" AND {clause}"
            params["as_of"] = as_of

        sql = HYBRID_SQL.format(table=self.table, where=where, where_kw=where_kw)
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

_label_index = None
_reg_index = None


def get_label_index():
    global _label_index
    if _label_index is None:
        _label_index = (PgHybridIndex("labels") if SEARCH_BACKEND == "pgvector"
                        else MemoryLabelIndex())
    return _label_index


def get_regulation_index():
    global _reg_index
    if _reg_index is None:
        _reg_index = (PgHybridIndex("regulations") if SEARCH_BACKEND == "pgvector"
                      else MemoryRegIndex())
    return _reg_index
