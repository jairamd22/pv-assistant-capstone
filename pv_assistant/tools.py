"""Tool schemas and dispatch for the agent.

Four tools:
- query_aems           — live adverse-event report counts (never ingested)
- search_labels        — hybrid retrieval over sectioned FDA label text,
                         optional drug filter and as-of-date (historical)
- search_regulations   — hybrid retrieval over 21 CFR / FD&C Act sections
- lookup_srlc_history  — curated historical safety labeling changes
"""

import json
import os

import pandas as pd

from pv_assistant import aems
from pv_assistant.search import get_label_index, get_regulation_index

SRLC_PATH = os.getenv("SRLC_PATH", "data/srlc_validation.csv")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_aems",
            "description": (
                "Query the FDA adverse event monitoring system (AEMS, via the "
                "openFDA-compatible endpoint) for report counts on a specific "
                "drug and reaction pair. Use when the question involves how "
                "many reports exist, report trends, or whether a signal is "
                "being reported. Returns counts plus a mandatory "
                "surveillance-data disclaimer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "drug": {"type": "string", "description": "Generic drug name, e.g. 'gabapentin'"},
                    "reaction": {"type": "string", "description": "Adverse reaction / MedDRA-style term, e.g. 'respiratory depression'"},
                },
                "required": ["drug", "reaction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_labels",
            "description": (
                "Search the FDA drug label corpus (sectioned SPL text: Boxed "
                "Warning, Warnings and Precautions, Adverse Reactions, etc.). "
                "Use to check what a drug's label currently says about a "
                "reaction. Pass as_of (YYYY-MM-DD) to search the label as it "
                "stood at a historical date."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "drug": {"type": "string", "description": "Optional generic drug name filter"},
                    "as_of": {"type": "string", "description": "Optional YYYY-MM-DD historical date"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_regulations",
            "description": (
                "Search the regulatory corpus: 21 CFR 314.70/314.80/314.81, "
                "201.57, 601.12 and FD&C Act 505(o)(4). Use for questions "
                "about reporting duties, timelines, supplement types (PAS, "
                "CBE-30, CBE-0), or when a label must be revised."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_srlc_history",
            "description": (
                "Look up historical FDA safety labeling changes (SrLC, 2016+) "
                "matching a drug and/or reaction. Use to check whether FDA "
                "has previously required a label change for a similar "
                "drug/reaction pattern."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "drug": {"type": "string"},
                    "reaction": {"type": "string"},
                },
            },
        },
    },
]


def _search_labels(query, drug=None, as_of=None):
    results = get_label_index().search(query, drug=drug, as_of=as_of, num_results=5)
    return [
        {k: r[k] for k in ("drug", "brand", "section_name", "as_of_date", "text")
         if k in r}
        for r in results
    ]


def _search_regulations(query):
    results = get_regulation_index().search(query, num_results=5)
    return [{k: r[k] for k in ("citation", "title", "text") if k in r}
            for r in results]


def _lookup_srlc(drug=None, reaction=None):
    df = pd.read_csv(SRLC_PATH)
    if drug:
        df = df[df.drug.str.contains(drug.lower().strip(), case=False)]
    if reaction:
        terms = [w for w in reaction.lower().split() if len(w) > 3]
        if terms:
            mask = df.reaction.str.lower().apply(
                lambda x: any(t in x for t in terms)
            ) | df.meddra_term.str.lower().apply(
                lambda x: any(t in x for t in terms)
            )
            df = df[mask]
    if df.empty:
        return {"matches": [], "note": "no historical SrLC match in the curated set"}
    return {"matches": df.to_dict(orient="records")}


def dispatch(name: str, arguments: str):
    """Execute a tool call; returns a JSON-serializable result."""
    args = json.loads(arguments or "{}")
    if name == "query_aems":
        return aems.query_aems(args["drug"], args["reaction"])
    if name == "search_labels":
        return _search_labels(args["query"], args.get("drug"), args.get("as_of"))
    if name == "search_regulations":
        return _search_regulations(args["query"])
    if name == "lookup_srlc_history":
        return _lookup_srlc(args.get("drug"), args.get("reaction"))
    return {"error": f"unknown tool {name}"}
