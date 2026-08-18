"""Pump synthetic conversations + tool calls + SrLC results into Postgres so
the 9-panel Grafana dashboard has data. One insert per second until stopped."""

import os
import random
import time
import uuid
from datetime import date

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("POSTGRES_HOST", "localhost")

from pv_assistant import db  # noqa: E402

QA = [
    ("Reports of respiratory depression with gabapentin — label covered?",
     "The current label's Warnings and Precautions section covers serious respiratory depression with CNS depressants (Warnings and Precautions, gabapentin). VERDICT: COVERED",
     "COVERED", ["query_aems", "search_labels"]),
    ("Is Fournier's gangrene in the empagliflozin label?",
     "Yes — necrotizing fasciitis of the perineum appears in Warnings and Precautions (empagliflozin). VERDICT: COVERED",
     "COVERED", ["search_labels"]),
    ("Aortic dissection reports for ciprofloxacin — what must we do?",
     "The label covers aortic aneurysm and dissection (Warnings and Precautions); 15-day alert reporting applies to serious unexpected events per 21 CFR 314.80(c)(1). VERDICT: COVERED",
     "COVERED", ["query_aems", "search_labels", "search_regulations"]),
    ("Does the 2019 montelukast label reflect suicidal ideation?",
     "The 2019-era sections list agitation and depression but not suicidal ideation — potential gap flagged for human review. VERDICT: POTENTIAL_GAP",
     "POTENTIAL_GAP", ["query_aems", "search_labels", "lookup_srlc_history"]),
    ("What does 21 CFR 314.80(c)(1) require?",
     "Serious AND unexpected adverse experiences must be reported within 15 calendar days (21 CFR 314.80(c)(1)).",
     "NONE", ["search_regulations"]),
]

RELEVANCE = ["RELEVANT", "RELEVANT", "RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT"]
MODELS = ["gpt-4o-mini", "gpt-4o"]

SRLC = [
    ("montelukast", "suicidal ideation and behavior", date(2020, 3, 4)),
    ("ciprofloxacin", "aortic aneurysm and dissection", date(2018, 12, 20)),
    ("canagliflozin", "necrotizing fasciitis of the perineum", date(2018, 8, 29)),
    ("febuxostat", "cardiovascular death", date(2019, 2, 21)),
    ("gabapentin", "serious respiratory depression", date(2019, 12, 19)),
    ("ciprofloxacin", "severe hypoglycemia", date(2018, 7, 10)),
]


def generate_conversation():
    q, a, verdict, tools = random.choice(QA)
    pt, ct = random.randint(1200, 3200), random.randint(120, 450)
    ept, ect = random.randint(150, 300), random.randint(30, 80)
    data = {
        "answer": a, "verdict": verdict, "tools_used": tools,
        "tool_log": [{"tool": t, "arguments": "{}"} for t in tools],
        "model_used": random.choice(MODELS),
        "response_time": random.uniform(1.5, 9.0),
        "relevance": random.choice(RELEVANCE),
        "relevance_explanation": "Synthetic monitoring data.",
        "prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct,
        "eval_prompt_tokens": ept, "eval_completion_tokens": ect,
        "eval_total_tokens": ept + ect,
        "openai_cost": random.uniform(0.0008, 0.02),
    }
    cid = str(uuid.uuid4())
    db.save_conversation(cid, q, data)
    if random.random() < 0.6:
        db.save_feedback(cid, random.choice([1, 1, 1, 1, -1]))
    if random.random() < 0.25:
        drug, reaction, d = random.choice(SRLC)
        flagged = random.random() < 0.83  # ~5/6 historical hit rate
        db.save_srlc_result(drug, reaction, d, flagged,
                            "POTENTIAL_GAP" if flagged else "COVERED")
    return cid


if __name__ == "__main__":
    print("Generating synthetic monitoring data (Ctrl+C to stop)...")
    while True:
        print("inserted", generate_conversation())
        time.sleep(1)
