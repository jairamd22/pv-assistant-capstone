"""AEMS adverse-event query tool.

Two modes, selected with AEMS_MODE:

- "live"    — queries the openFDA backward-compatible drug/event endpoint
  (confirmed maintained through at least end of 2026 during the AEMS
  transition). This is the primary access path — a deliberate risk
  mitigation: the native AEMS API is still maturing, so the project builds
  against the explicitly-stable compatibility layer and treats native AEMS
  integration (webhooks) as a stretch goal.
- "fixture" (default) — bundled offline responses (data/aems_fixtures.json)
  so the full agent runs with no network and demos are deterministic.

This source is queried LIVE at answer time, never bulk-ingested: AEMS is
explicitly designed for real-time access, and a nightly ingestion would
undermine the freshness that is the platform's actual value.

IMPORTANT: every result carries the surveillance-data disclaimer. Adverse
event reports are voluntary/passive surveillance — a report does not
establish causation, and underreporting is a known FDA-acknowledged
limitation. The agent is instructed to repeat this in user-facing output.
"""

import json
import os
from pathlib import Path

DISCLAIMER = (
    "Adverse event reports are voluntary, passive-surveillance data: "
    "a report does not establish that the drug caused the event, report "
    "counts are affected by underreporting and stimulated reporting, and "
    "rates cannot be computed without exposure data."
)

AEMS_MODE = os.getenv("AEMS_MODE", "fixture")
OPENFDA_BASE = os.getenv("OPENFDA_BASE", "https://api.fda.gov/drug/event.json")
OPENFDA_API_KEY = os.getenv("OPENFDA_API_KEY", "")

FIXTURES_PATH = Path(os.getenv("AEMS_FIXTURES", "data/aems_fixtures.json"))


def _fixture_query(drug: str, reaction: str) -> dict:
    fixtures = json.loads(FIXTURES_PATH.read_text())
    key = f"{drug.lower().strip()}|{reaction.lower().strip()}"
    hit = fixtures.get(key)
    if hit is None:
        # fuzzy: same drug, reaction substring either way
        for k, v in fixtures.items():
            d, r = k.split("|")
            if d == drug.lower().strip() and (
                r in reaction.lower() or reaction.lower() in r
            ):
                hit = v
                break
    if hit is None:
        return {"drug": drug, "reaction": reaction, "reports": 0,
                "serious": 0, "note": "no fixture data for this pair",
                "mode": "fixture", "disclaimer": DISCLAIMER}
    return {"drug": drug, "reaction": reaction, **hit,
            "mode": "fixture", "disclaimer": DISCLAIMER}


def _live_query(drug: str, reaction: str) -> dict:
    import requests

    def count(extra=""):
        search = (
            f'patient.drug.medicinalproduct:"{drug}"'
            f'+AND+patient.reaction.reactionmeddrapt:"{reaction}"{extra}'
        )
        url = f"{OPENFDA_BASE}?search={search}&limit=1"
        if OPENFDA_API_KEY:
            url += f"&api_key={OPENFDA_API_KEY}"
        r = requests.get(url, timeout=30)
        if r.status_code == 404:  # openFDA returns 404 for zero matches
            return 0
        r.raise_for_status()
        return r.json().get("meta", {}).get("results", {}).get("total", 0)

    total = count()
    serious = count("+AND+serious:1")
    return {"drug": drug, "reaction": reaction, "reports": total,
            "serious": serious, "mode": "live",
            "source": "openFDA drug/event (AEMS backward-compatible endpoint)",
            "disclaimer": DISCLAIMER}


def query_aems(drug: str, reaction: str) -> dict:
    """Report counts for a drug/reaction pair (live API or fixture)."""
    if AEMS_MODE == "live":
        try:
            return _live_query(drug, reaction)
        except Exception as e:  # fall back rather than fail the whole answer
            result = _fixture_query(drug, reaction)
            result["note"] = f"live query failed ({e}); served fixture data"
            return result
    return _fixture_query(drug, reaction)
