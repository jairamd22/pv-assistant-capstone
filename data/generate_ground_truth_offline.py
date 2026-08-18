"""
Offline ground-truth generator for retrieval evaluation — labels and
regulations corpora, evaluated separately.

Questions are template-generated with deliberate MedDRA-vs-lay-terminology
variation ("Fournier's gangrene" vs "flesh-eating infection of the groin",
"suicidal ideation" vs "suicidal thoughts") so keyword search's terminology
gap — the documented motivation for hybrid search in this project — can be
MEASURED, not assumed.

The LLM-generated alternative is notebooks/evaluation-data-generation.ipynb
(same output columns: id, question).

Run:  python data/generate_ground_truth_offline.py
"""

import csv
import random
from pathlib import Path

import pandas as pd

random.seed(7)
HERE = Path(__file__).parent

# MedDRA-ish term -> lay synonyms (used to induce a measurable synonym gap)
SYN = {
    "suicidal ideation": ["suicidal thoughts", "thoughts of self-harm"],
    "aortic aneurysm": ["tear in the aorta", "bulge in the main artery"],
    "necrotizing fasciitis of the perineum": ["Fournier's gangrene",
                                              "flesh-eating infection of the groin"],
    "cardiovascular death": ["dying from heart problems", "fatal heart events"],
    "respiratory depression": ["dangerously slowed breathing", "breathing suppression"],
    "angioedema": ["severe facial and throat swelling"],
    "rhabdomyolysis": ["severe muscle breakdown"],
    "lactic acidosis": ["dangerous lactic acid buildup"],
    "hemorrhage": ["major bleeding", "serious bleeds"],
    "serotonin syndrome": ["serotonin toxicity"],
    "tendon rupture": ["Achilles tendon tear"],
    "hypoglycemia": ["dangerously low blood sugar"],
}

LABEL_TEMPLATES = [
    "Does the {drug} label mention {term}?",
    "Which section of the {brand} label covers {term}?",
    "Is {term} in the boxed warning for {drug}?",
    "What does the {drug} prescribing information say about {term}?",
    "Are there warnings about {term} for patients on {brand}?",
]

REG_TEMPLATES = [
    "What does {citation} cover?",
    "Which regulation addresses {topic}?",
    "What are the requirements under {citation}?",
    "Where is {topic} defined in the regulations?",
    "What's the rule for {topic}?",
]

REG_TOPICS = {
    "21 CFR 314.80(c)(1)": ["15-day alert reports", "expedited reporting of serious unexpected events"],
    "21 CFR 314.80(a)": ["the definition of a serious adverse drug experience",
                         "what counts as an unexpected adverse experience"],
    "21 CFR 314.80(b)": ["the duty to review adverse event information from all sources"],
    "21 CFR 314.80(c)(2)": ["periodic adverse experience reports", "quarterly safety reporting"],
    "21 CFR 314.80(e)": ["adverse event recordkeeping requirements"],
    "21 CFR 314.70(b)": ["prior approval supplements for major changes"],
    "21 CFR 314.70(c)": ["CBE-30 supplements"],
    "21 CFR 314.70(c)(6)(iii)(A)": ["adding a warning without waiting for FDA approval",
                                    "CBE-0 labeling changes"],
    "21 CFR 314.81(b)(2)": ["annual report content on new safety information"],
    "21 CFR 201.57(c)(6)": ["when the Warnings and Precautions section must be revised",
                            "the reasonable-evidence-of-causal-association standard"],
    "21 CFR 201.57(c)(1)": ["when a boxed warning is required"],
    "21 CFR 601.12(f)": ["labeling change reporting for biologics"],
    "FD&C Act 505(o)(4)(A)": ["FDA notifying a sponsor about new safety information"],
    "FD&C Act 505(o)(4)(B)": ["the 30-day response to an FDA safety labeling notification"],
    "FD&C Act 505(o)(4)(C-E)": ["FDA's authority to order a safety labeling change"],
    "FD&C Act 505-1(b)": ["the definition of new safety information"],
}

# reaction keywords present in each drug's label sections (used to pair
# questions with the correct record)
LABEL_TERMS = {
    "montelukast": ["suicidal ideation", "neuropsychiatric events"],
    "ciprofloxacin": ["aortic aneurysm", "tendon rupture", "hypoglycemia"],
    "canagliflozin": ["necrotizing fasciitis of the perineum", "lower limb amputation"],
    "febuxostat": ["cardiovascular death", "hepatic failure"],
    "gabapentin": ["respiratory depression", "angioedema"],
    "tofacitinib": ["thrombosis", "malignancy"],
    "empagliflozin": ["necrotizing fasciitis of the perineum", "ketoacidosis"],
    "warfarin": ["hemorrhage", "tissue necrosis"],
    "metformin": ["lactic acidosis", "vitamin B12 deficiency"],
    "atorvastatin": ["rhabdomyolysis", "myopathy"],
    "sertraline": ["serotonin syndrome", "suicidal thoughts"],
    "lisinopril": ["angioedema", "fetal toxicity"],
}


def variants(term):
    """The term itself plus lay synonyms, if any."""
    return [term] + SYN.get(term, [])


def main():
    labels = pd.read_csv(HERE / "labels.csv")
    # ground truth targets CURRENT label versions only (pre-change versions
    # are reserved for the SrLC historical validation, not retrieval eval)
    current = labels[~labels.version_note.str.startswith("pre-change")]

    rows = []
    for _, rec in current.iterrows():
        drug, brand = rec["drug"], rec["brand"]
        terms = [t for t in LABEL_TERMS.get(drug, []) if t.lower() in rec["text"].lower()]
        if not terms:
            terms = [rec["section_name"].lower()]
        for term in terms:
            for phrasing in variants(term):
                t = random.choice(LABEL_TEMPLATES)
                rows.append({"id": rec["id"],
                             "question": t.format(drug=drug, brand=brand, term=phrasing)})

    out = HERE / "ground-truth-labels.csv"
    pd.DataFrame(rows).drop_duplicates().to_csv(out, index=False)
    print(f"labels ground truth: {len(rows)} -> {out.name}")

    regs = pd.read_csv(HERE / "regulations.csv")
    rrows = []
    for _, rec in regs.iterrows():
        cite = rec["citation"]
        topics = REG_TOPICS.get(cite, [rec["title"].lower()])
        for topic in topics:
            for t in REG_TEMPLATES:
                q = t.format(citation=cite, topic=topic)
                rrows.append({"id": rec["id"], "question": q})

    out = HERE / "ground-truth-regulations.csv"
    pd.DataFrame(rrows).drop_duplicates().to_csv(out, index=False)
    print(f"regulations ground truth: {len(rrows)} -> {out.name}")


if __name__ == "__main__":
    main()
