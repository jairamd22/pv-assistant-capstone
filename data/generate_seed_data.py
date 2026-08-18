"""
Generates the bundled data snapshot for the Pharmacovigilance Signal &
Label-Gap Intelligence Assistant.

What this produces
------------------
data/labels.csv       -- sectioned drug-label snapshot (SPL-style sections),
                         including *pre-change* label versions for the drugs
                         in the historical validation set, so the SrLC
                         validation can query "the label as it stood before
                         FDA required the change".
data/regulations.csv  -- condensed, section-based records of 21 CFR 314.70,
                         314.80, 314.81, 201.57, 601.12 and FD&C Act
                         505(o)(4). US regulatory text is public domain;
                         these records are CONDENSED summaries per section,
                         suitable for retrieval + citation, not verbatim
                         reproductions.
data/srlc_validation.csv -- curated set of REAL historical FDA safety
                         labeling changes (2016+), assembled from FDA's
                         public Drug Safety Communications. Extend it from
                         the full SrLC download at accessdata.fda.gov.
data/aems_fixtures.json -- offline fixture responses for the AEMS tool
                         (drug/reaction report counts), so the agent runs
                         with no network. Live mode queries openFDA.
data/tool-selection-testset.csv -- questions with expected tool calls, for
                         the agentic tool-selection evaluation.

Honesty notes
-------------
- Label section text below is a CONDENSED, representative snapshot written
  for this demo (documented as_of dates). The dlt pipeline in ingestion/
  replaces it with real, current SPL text from openFDA when you run it.
- The SrLC rows are real FDA actions (drug, reaction, date); verify and
  extend against the official database before publishing claims.

Run:  python data/generate_seed_data.py
"""

import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent

SEC = {
    "BW": ("34066-1", "Boxed Warning"),
    "CI": ("34070-3", "Contraindications"),
    "WP": ("43685-7", "Warnings and Precautions"),
    "AR": ("34084-4", "Adverse Reactions"),
    "DI": ("34073-7", "Drug Interactions"),
    "IU": ("34067-9", "Indications and Usage"),
}

labels = []


def L(drug, brand, sec, as_of, text, version_note="current snapshot"):
    code, name = SEC[sec]
    rid = hashlib.md5(f"{drug}|{sec}|{as_of}".encode()).hexdigest()[:8]
    labels.append({
        "id": rid,
        "drug": drug,
        "brand": brand,
        "section_code": code,
        "section_name": name,
        "as_of_date": as_of,
        "version_note": version_note,
        "text": " ".join(text.split()),
    })


# ---------------------------------------------------------------------------
# Validation-set drugs: PRE-CHANGE version + CURRENT version
# ---------------------------------------------------------------------------

# --- montelukast (SINGULAIR) — boxed warning for neuropsychiatric events,
#     required by FDA March 2020 -----------------------------------------
L("montelukast", "Singulair", "WP", "2019-06-01", """
   Precautions: Phenylketonurics — chewable tablets contain phenylalanine.
   Patients with known aspirin sensitivity should continue avoidance of
   aspirin or non-steroidal anti-inflammatory agents. Neuropsychiatric
   events have been reported in the postmarketing setting; patients and
   prescribers should be alert for changes in behavior or mood.""",
   "pre-change version (before 2020 boxed warning)")
L("montelukast", "Singulair", "AR", "2019-06-01", """
   Postmarketing experience includes reports of agitation, aggressive
   behavior, anxiousness, depression, disorientation, dream abnormalities,
   hallucinations, insomnia, irritability, restlessness, and tremor.
   The most common adverse reactions in clinical trials were upper
   respiratory infection, fever, headache, pharyngitis, cough, abdominal
   pain, diarrhea, otitis media, influenza, rhinorrhea, and sinusitis.""",
   "pre-change version (before 2020 boxed warning)")
L("montelukast", "Singulair", "BW", "2024-01-15", """
   WARNING: SERIOUS NEUROPSYCHIATRIC EVENTS. Serious neuropsychiatric
   events, including suicidal thoughts and behavior (suicidal ideation)
   and completed suicide, have been reported in patients taking
   montelukast. Because of the risk of these events, the benefits of
   montelukast may not outweigh the risks in some patients, particularly
   when symptoms may be mild and adequately treated with other medicines.
   Advise patients and caregivers to be alert for neuropsychiatric events;
   discontinue montelukast if such events occur.""")
L("montelukast", "Singulair", "WP", "2024-01-15", """
   Serious neuropsychiatric events including agitation, aggression,
   depression, sleep disturbances, suicidal thoughts and behavior
   (including completed suicide), and tremor have been reported. Evaluate
   the risks and benefits of continuing treatment if such events occur.
   Phenylketonurics: chewable tablets contain phenylalanine. Patients with
   aspirin sensitivity should continue to avoid aspirin and NSAIDs.""")
L("montelukast", "Singulair", "IU", "2024-01-15", """
   Indicated for prophylaxis and chronic treatment of asthma in patients 12
   months of age and older, for acute prevention of exercise-induced
   bronchoconstriction, and for relief of symptoms of allergic rhinitis in
   patients for whom alternative therapies are inadequate.""")

# --- ciprofloxacin (CIPRO) — aortic aneurysm/dissection W&P added Dec 2018
L("ciprofloxacin", "Cipro", "BW", "2018-06-01", """
   WARNING: SERIOUS ADVERSE REACTIONS INCLUDING TENDINITIS, TENDON RUPTURE,
   PERIPHERAL NEUROPATHY, CENTRAL NERVOUS SYSTEM EFFECTS, AND EXACERBATION
   OF MYASTHENIA GRAVIS. Fluoroquinolones have been associated with
   disabling and potentially irreversible serious adverse reactions.
   Discontinue at the first sign of tendon inflammation or pain. Reserve
   for patients who have no alternative treatment options for uncomplicated
   infections.""", "pre-change version (before Dec 2018 aortic update)")
L("ciprofloxacin", "Cipro", "WP", "2018-06-01", """
   Tendinitis and tendon rupture, including Achilles tendon rupture, can
   occur during or after treatment, particularly in patients over 60 years,
   those on corticosteroids, and transplant recipients. Peripheral
   neuropathy, CNS effects including seizures and psychiatric reactions,
   hypoglycemia and hyperglycemia disturbances, Clostridioides difficile
   associated diarrhea, and QT interval prolongation have been reported.""",
   "pre-change version (before Dec 2018 aortic update)")
L("ciprofloxacin", "Cipro", "BW", "2024-02-01", """
   WARNING: SERIOUS ADVERSE REACTIONS INCLUDING TENDINITIS, TENDON RUPTURE,
   PERIPHERAL NEUROPATHY, CENTRAL NERVOUS SYSTEM EFFECTS, AND EXACERBATION
   OF MYASTHENIA GRAVIS. Discontinue immediately at first signs of these
   serious reactions and avoid fluoroquinolones in patients who have
   experienced any of them. Reserve for patients with no alternative
   treatment options for certain uncomplicated infections.""")
L("ciprofloxacin", "Cipro", "WP", "2024-02-01", """
   Aortic aneurysm and dissection: epidemiologic studies report an
   increased risk of aortic aneurysm and dissection within two months
   following fluoroquinolone use, particularly in elderly patients. Avoid
   in patients with known aortic aneurysm or at increased risk unless no
   alternative exists. Tendinitis and tendon rupture including Achilles
   rupture; peripheral neuropathy that may be irreversible; CNS effects
   including seizures, increased intracranial pressure, and psychiatric
   reactions; significant hypoglycemia including hypoglycemic coma,
   particularly in elderly diabetic patients on sulfonylureas; QT
   prolongation; photosensitivity; C. difficile associated diarrhea.""")
L("ciprofloxacin", "Cipro", "AR", "2024-02-01", """
   Most common adverse reactions: nausea, diarrhea, abnormal liver
   function tests, vomiting, and rash. Postmarketing reports include
   tendon rupture, aortic aneurysm and dissection, severe hypoglycemia,
   toxic epidermal necrolysis, and delirium.""")

# --- canagliflozin (INVOKANA) — Fournier's gangrene W&P added Aug 2018
L("canagliflozin", "Invokana", "WP", "2018-05-01", """
   Lower limb amputation: an increased risk of lower limb amputations,
   primarily of the toe and midfoot, was observed in the CANVAS trials
   (boxed warning). Ketoacidosis, acute kidney injury, urosepsis and
   pyelonephritis, hypotension, hypoglycemia with concomitant insulin or
   insulin secretagogues, genital mycotic infections, and bone fracture
   risk have been reported.""",
   "pre-change version (before Aug 2018 Fournier's update)")
L("canagliflozin", "Invokana", "WP", "2024-03-01", """
   Necrotizing fasciitis of the perineum (Fournier's gangrene): reports of
   this rare but serious and life-threatening infection have been
   identified in patients taking SGLT2 inhibitors. Assess patients
   presenting with pain, tenderness, erythema, or swelling in the genital
   or perineal area, along with fever or malaise; if suspected, start
   treatment immediately and discontinue the drug. Ketoacidosis; lower
   limb amputation risk; acute kidney injury; serious urinary tract
   infections; hypotension; hypoglycemia with insulin or secretagogues;
   genital mycotic infections; bone fractures.""")
L("canagliflozin", "Invokana", "AR", "2024-03-01", """
   Most common adverse reactions: female genital mycotic infections,
   urinary tract infection, and increased urination. Postmarketing:
   ketoacidosis, necrotizing fasciitis of the perineum, acute kidney
   injury, anaphylaxis, and angioedema.""")

# --- febuxostat (ULORIC) — CV death boxed warning added Feb 2019
L("febuxostat", "Uloric", "WP", "2018-09-01", """
   Cardiovascular events: in randomized controlled studies there was a
   higher rate of cardiovascular thromboembolic events in patients treated
   with febuxostat than allopurinol; monitor for signs and symptoms of
   myocardial infarction and stroke. Gout flares may occur after
   initiation. Hepatic effects: postmarketing reports of hepatic failure;
   obtain liver tests if symptoms suggest injury. Serious skin reactions
   including Stevens-Johnson syndrome have been reported.""",
   "pre-change version (before Feb 2019 boxed warning)")
L("febuxostat", "Uloric", "BW", "2024-01-10", """
   WARNING: CARDIOVASCULAR DEATH. In a cardiovascular outcomes study of
   patients with gout and established cardiovascular disease, gout
   patients treated with febuxostat had a higher rate of cardiovascular
   death compared to those treated with allopurinol. Consider the risks
   and benefits when deciding to prescribe or continue febuxostat; reserve
   for patients who have an inadequate response or intolerance to
   allopurinol.""")
L("febuxostat", "Uloric", "WP", "2024-01-10", """
   Cardiovascular death (see Boxed Warning). Gout flare after initiation;
   prophylaxis with an NSAID or colchicine is recommended. Hepatic
   effects including postmarketing reports of fatal hepatic failure.
   Serious skin and hypersensitivity reactions including Stevens-Johnson
   syndrome and drug reaction with eosinophilia and systemic symptoms.""")

# --- gabapentin (NEURONTIN) — respiratory depression W&P added Dec 2019
L("gabapentin", "Neurontin", "WP", "2019-08-01", """
   Drug reaction with eosinophilia and systemic symptoms (DRESS):
   multiorgan hypersensitivity has been reported; discontinue if an
   alternative etiology cannot be established. Anaphylaxis and angioedema
   have been reported. Somnolence, dizziness, and CNS depression may
   impair ability to drive or operate machinery. Suicidal behavior and
   ideation: antiepileptic drugs increase the risk; monitor for emergence
   or worsening of depression.""",
   "pre-change version (before Dec 2019 respiratory update)")
L("gabapentin", "Neurontin", "WP", "2024-04-01", """
   Respiratory depression: serious, life-threatening, and fatal
   respiratory depression may occur when gabapentin is used with opioids
   or other CNS depressants, or in patients with underlying respiratory
   impairment or the elderly. Initiate at the lowest dose and monitor for
   symptoms of respiratory depression and sedation. DRESS/multiorgan
   hypersensitivity; anaphylaxis and angioedema; somnolence and dizziness;
   increased risk of suicidal thoughts or behavior with antiepileptic
   drugs; neuropsychiatric adverse reactions in pediatric patients.""")
L("gabapentin", "Neurontin", "AR", "2024-04-01", """
   Most common adverse reactions: dizziness, somnolence, ataxia, fatigue,
   and peripheral edema. Postmarketing: respiratory depression
   (particularly with concomitant opioid use), angioedema, rhabdomyolysis,
   and withdrawal symptoms following abrupt discontinuation.""")

# ---------------------------------------------------------------------------
# Current-only drugs (single snapshot)
# ---------------------------------------------------------------------------

L("tofacitinib", "Xeljanz", "BW", "2024-02-20", """
   WARNING: SERIOUS INFECTIONS, MORTALITY, MALIGNANCY, MAJOR ADVERSE
   CARDIOVASCULAR EVENTS, AND THROMBOSIS. Increased risk of serious
   bacterial, fungal, viral, and opportunistic infections including
   tuberculosis. Higher rate of all-cause mortality, lymphomas and lung
   cancers, major adverse cardiovascular events (cardiovascular death,
   myocardial infarction, stroke), and thrombosis including pulmonary
   embolism and deep venous thrombosis, observed in a large postmarketing
   safety study in rheumatoid arthritis patients versus TNF blockers.""")
L("tofacitinib", "Xeljanz", "WP", "2024-02-20", """
   Serious infections; malignancy and lymphoproliferative disorders; major
   adverse cardiovascular events; thrombosis; gastrointestinal
   perforations; laboratory abnormalities including lymphopenia,
   neutropenia, anemia, and lipid elevations; vaccination with live
   vaccines should be avoided during treatment.""")
L("empagliflozin", "Jardiance", "WP", "2024-03-01", """
   Ketoacidosis in patients with diabetes; volume depletion and
   hypotension; urosepsis and pyelonephritis; hypoglycemia with insulin or
   insulin secretagogues; necrotizing fasciitis of the perineum
   (Fournier's gangrene) reported with SGLT2 inhibitors — assess and treat
   promptly; genital mycotic infections.""")
L("empagliflozin", "Jardiance", "AR", "2024-03-01", """
   Most common adverse reactions: urinary tract infections and female
   genital mycotic infections. Postmarketing: ketoacidosis, urosepsis,
   necrotizing fasciitis of the perineum, and angioedema.""")
L("warfarin", "Coumadin", "BW", "2024-01-05", """
   WARNING: BLEEDING RISK. Warfarin can cause major or fatal bleeding.
   Perform regular monitoring of INR in all treated patients. Drugs, diet
   changes, and other factors affect INR levels; instruct patients about
   prevention measures and to report signs and symptoms of bleeding
   immediately.""")
L("warfarin", "Coumadin", "WP", "2024-01-05", """
   Hemorrhage: fatal or serious bleeding can occur at any site. Tissue
   necrosis and calciphylaxis; acute kidney injury in patients with
   altered glomerular integrity; systemic atheroemboli and cholesterol
   microemboli ("purple toe syndrome"); use in pregnancy is
   contraindicated except with mechanical heart valves; heparin-induced
   thrombocytopenia interaction.""")
L("warfarin", "Coumadin", "DI", "2024-01-05", """
   Numerous drugs interact with warfarin through CYP2C9, CYP1A2, and
   CYP3A4 pathways or through effects on hemostasis. Inhibitors such as
   amiodarone, fluconazole, metronidazole, and trimethoprim-
   sulfamethoxazole increase INR and bleeding risk; inducers such as
   rifampin and carbamazepine decrease INR. NSAIDs, aspirin, and
   antiplatelet agents increase bleeding risk without raising INR.""")
L("metformin", "Glucophage", "BW", "2024-02-01", """
   WARNING: LACTIC ACIDOSIS. Postmarketing cases of metformin-associated
   lactic acidosis have resulted in death, hypothermia, hypotension, and
   resistant bradyarrhythmias. Risk factors include renal impairment,
   concomitant carbonic anhydrase inhibitors, age 65 or greater, contrast
   imaging procedures, surgery, hypoxic states, excessive alcohol intake,
   and hepatic impairment. If lactic acidosis is suspected, discontinue
   metformin and institute general supportive measures.""")
L("metformin", "Glucophage", "WP", "2024-02-01", """
   Lactic acidosis (boxed warning); vitamin B12 deficiency with long-term
   use — measure hematologic parameters periodically; hypoglycemia with
   concomitant insulin or insulin secretagogues, alcohol, caloric
   deficit; withhold in hypoxic states and before iodinated contrast
   imaging in patients with reduced renal function.""")
L("atorvastatin", "Lipitor", "WP", "2024-01-20", """
   Myopathy and rhabdomyolysis with acute renal failure secondary to
   myoglobinuria: risk increases with higher doses, advanced age,
   hypothyroidism, renal impairment, and interacting drugs such as
   cyclosporine, gemfibrozil, and strong CYP3A4 inhibitors. Immune-
   mediated necrotizing myopathy has been reported. Liver enzyme
   abnormalities: perform liver tests before initiation and as clinically
   indicated; rare postmarketing reports of fatal and non-fatal hepatic
   failure. Increases in HbA1c and fasting glucose have been reported.""")
L("atorvastatin", "Lipitor", "AR", "2024-01-20", """
   Most common adverse reactions: nasopharyngitis, arthralgia, diarrhea,
   pain in extremity, and urinary tract infection. Postmarketing:
   rhabdomyolysis, immune-mediated necrotizing myopathy, hepatic failure,
   dizziness, and memory impairment (generally reversible).""")
L("sertraline", "Zoloft", "BW", "2024-02-10", """
   WARNING: SUICIDAL THOUGHTS AND BEHAVIORS. Antidepressants increased the
   risk of suicidal thoughts and behavior in pediatric and young adult
   patients in short-term studies. Closely monitor all antidepressant-
   treated patients for clinical worsening and emergence of suicidal
   thoughts and behaviors, particularly during the initial few months of
   therapy and at times of dosage changes.""")
L("sertraline", "Zoloft", "WP", "2024-02-10", """
   Serotonin syndrome, particularly with concomitant serotonergic drugs
   including MAOIs, triptans, and tramadol; increased risk of bleeding
   with aspirin, NSAIDs, or anticoagulants; activation of mania or
   hypomania; discontinuation syndrome with abrupt cessation; angle-
   closure glaucoma; hyponatremia, particularly in the elderly; QTc
   prolongation at higher doses.""")
L("lisinopril", "Zestril", "BW", "2024-01-25", """
   WARNING: FETAL TOXICITY. When pregnancy is detected, discontinue
   lisinopril as soon as possible. Drugs that act directly on the
   renin-angiotensin system can cause injury and death to the developing
   fetus.""")
L("lisinopril", "Zestril", "WP", "2024-01-25", """
   Angioedema of the face, extremities, lips, tongue, glottis, and larynx
   has been reported, including fatal airway obstruction; higher incidence
   in Black patients; intestinal angioedema has also been reported.
   Hypotension, particularly in volume- or salt-depleted patients;
   hyperkalemia; renal function deterioration in susceptible patients;
   rare syndrome starting with cholestatic jaundice progressing to
   hepatic necrosis.""")

# ---------------------------------------------------------------------------
# Regulations — condensed, section-based, public-domain sources
# ---------------------------------------------------------------------------

regs = []


def R(cite, title, text):
    rid = hashlib.md5(cite.encode()).hexdigest()[:8]
    regs.append({
        "id": rid,
        "citation": cite,
        "title": title,
        "text": " ".join(text.split()),
    })


R("21 CFR 314.70(b)", "Major changes — prior approval supplement", """
   Changes with substantial potential to adversely affect identity,
   strength, quality, purity, or potency, including certain labeling
   changes, require submission and FDA approval of a supplement BEFORE
   distribution of the product made using the change (Prior Approval
   Supplement, PAS).""")
R("21 CFR 314.70(c)", "Moderate changes — CBE-30 supplements", """
   Moderate changes require a supplement submitted at least 30 days before
   distribution (Changes Being Effected in 30 days, CBE-30). If FDA
   informs the applicant of missing information within 30 days,
   distribution must not begin until the issues are resolved.""")
R("21 CFR 314.70(c)(6)(iii)(A)", "CBE-0 — adding or strengthening warnings", """
   Labeling changes that add or strengthen a contraindication, warning,
   precaution, or adverse reaction for which there is newly acquired
   information and reasonable evidence of a causal association may be
   placed into effect UPON RECEIPT of the supplement by FDA (Changes Being
   Effected, CBE-0) — the sponsor does not wait for approval to warn.""")
R("21 CFR 314.80(a)", "Postmarketing adverse experience definitions", """
   Defines adverse drug experience (any adverse event associated with the
   use of a drug, whether or not considered drug related); serious adverse
   drug experience (death, life-threatening, hospitalization or
   prolongation, persistent or significant disability, congenital
   anomaly, or requiring intervention to prevent such outcomes); and
   unexpected adverse drug experience (not listed in the current labeling,
   or observed at greater severity or specificity than listed).""")
R("21 CFR 314.80(b)", "Review of adverse drug experiences", """
   Applicants must promptly review all adverse drug experience information
   obtained or otherwise received from any source, foreign or domestic,
   including commercial marketing experience, postmarketing studies,
   reports in the scientific literature, and unpublished scientific
   papers, and must maintain written procedures for surveillance,
   receipt, evaluation, and reporting.""")
R("21 CFR 314.80(c)(1)", "15-day 'Alert reports'", """
   Applicants must report each adverse drug experience that is BOTH
   serious and unexpected, whether foreign or domestic, as soon as
   possible but no later than 15 calendar days from initial receipt, and
   must promptly investigate and submit follow-up reports within 15 days
   of receipt of new information.""")
R("21 CFR 314.80(c)(2)", "Periodic adverse drug experience reports", """
   Adverse experiences not qualifying for 15-day reporting must be
   reported periodically: quarterly for three years from approval, then
   annually. Periodic reports include a narrative summary and analysis, an
   index of reports, and a history of actions taken because of adverse
   drug experiences (for example, labeling changes or studies
   initiated).""")
R("21 CFR 314.80(e)", "Recordkeeping for adverse experiences", """
   Applicants must maintain for 10 years records of all adverse drug
   experience information known to them, including raw data and
   correspondence relating to the adverse experiences.""")
R("21 CFR 314.81(b)(2)", "Annual reports", """
   Annual reports must include, among other items, a brief summary of
   significant new information from the previous year that might affect
   the safety, effectiveness, or labeling of the drug, and a description
   of actions the applicant has taken or intends to take as a result —
   for example, submitting a labeling supplement.""")
R("21 CFR 201.57(c)(6)", "Warnings and Precautions — content standard", """
   The Warnings and Precautions section must describe clinically
   significant adverse reactions and other potential safety hazards. The
   labeling MUST BE REVISED to include a warning about a clinically
   significant hazard AS SOON AS THERE IS REASONABLE EVIDENCE OF A CAUSAL
   ASSOCIATION with the drug; a causal relationship need not have been
   definitely established.""")
R("21 CFR 201.57(c)(1)", "Boxed warning standard", """
   Certain contraindications or serious warnings, particularly those that
   may lead to death or serious injury, may be required by FDA to be
   presented in a box at the beginning of prescribing information (the
   'boxed warning'), based on clinical significance.""")
R("21 CFR 601.12(f)", "Biologics — labeling changes reporting", """
   For biological products, labeling changes parallel the drug framework:
   changes adding or strengthening warnings based on newly acquired
   information may be implemented via a 'Changes Being Effected'
   supplement, while other labeling changes require prior approval.""")
R("FD&C Act 505(o)(4)(A)", "Safety labeling changes — FDA notification", """
   If FDA becomes aware of NEW SAFETY INFORMATION that it believes should
   be included in the labeling of a drug, FDA must promptly notify the
   application holder.""")
R("FD&C Act 505(o)(4)(B)", "Safety labeling changes — 30-day response", """
   Within 30 days of FDA notification, the holder must submit a supplement
   proposing labeling changes to reflect the new safety information, or
   notify FDA that it does not believe a change is warranted and provide
   the reasons.""")
R("FD&C Act 505(o)(4)(C-E)", "Safety labeling changes — order authority", """
   FDA reviews the proposed changes, may initiate discussions (generally
   not to exceed 30 days), and may issue an ORDER directing the holder to
   make the labeling changes FDA deems appropriate; the holder must submit
   a conforming supplement within 15 days of the order.""")
R("FD&C Act 505-1(b)", "Definition — new safety information", """
   'New safety information' includes information derived from clinical
   trials, adverse event reports, postapproval studies, peer-reviewed
   literature, or other scientific data about a serious risk or an
   unexpected serious risk associated with use of the drug since approval,
   or since the last labeling requirement was imposed.""")

# ---------------------------------------------------------------------------
# SrLC historical validation set (REAL FDA actions, curated)
# ---------------------------------------------------------------------------

srlc = [
    dict(drug="montelukast", reaction="suicidal ideation and behavior",
         meddra_term="Suicidal ideation",
         change_date="2020-03-04", change_type="Boxed Warning added",
         label_section="Boxed Warning",
         source="FDA Drug Safety Communication, March 2020"),
    dict(drug="ciprofloxacin", reaction="aortic aneurysm and dissection",
         meddra_term="Aortic aneurysm",
         change_date="2018-12-20", change_type="Warnings and Precautions strengthened",
         label_section="Warnings and Precautions",
         source="FDA Drug Safety Communication, December 2018"),
    dict(drug="ciprofloxacin", reaction="severe hypoglycemia including hypoglycemic coma",
         meddra_term="Hypoglycaemic coma",
         change_date="2018-07-10", change_type="Warnings strengthened",
         label_section="Warnings and Precautions",
         source="FDA Drug Safety Communication, July 2018"),
    dict(drug="canagliflozin", reaction="necrotizing fasciitis of the perineum (Fournier's gangrene)",
         meddra_term="Fournier's gangrene",
         change_date="2018-08-29", change_type="Warnings and Precautions added",
         label_section="Warnings and Precautions",
         source="FDA Drug Safety Communication, August 2018"),
    dict(drug="febuxostat", reaction="cardiovascular death",
         meddra_term="Sudden cardiac death",
         change_date="2019-02-21", change_type="Boxed Warning added",
         label_section="Boxed Warning",
         source="FDA Drug Safety Communication, February 2019"),
    dict(drug="gabapentin", reaction="serious respiratory depression",
         meddra_term="Respiratory depression",
         change_date="2019-12-19", change_type="Warnings added",
         label_section="Warnings and Precautions",
         source="FDA Drug Safety Communication, December 2019"),
]

# ---------------------------------------------------------------------------
# AEMS offline fixtures — report counts per (drug, reaction)
# Shaped like a condensed openFDA drug/event count response.
# ---------------------------------------------------------------------------

fixtures = {
    "montelukast|suicidal ideation": {"reports": 2181, "serious": 1918, "trend_12m": "elevated", "as_of": "2019-06-01"},
    "montelukast|nightmare": {"reports": 1466, "serious": 402, "trend_12m": "stable", "as_of": "2019-06-01"},
    "ciprofloxacin|aortic aneurysm": {"reports": 214, "serious": 214, "trend_12m": "rising", "as_of": "2018-06-01"},
    "ciprofloxacin|tendon rupture": {"reports": 3610, "serious": 3115, "trend_12m": "stable", "as_of": "2018-06-01"},
    "canagliflozin|fournier's gangrene": {"reports": 55, "serious": 55, "trend_12m": "rising", "as_of": "2018-05-01"},
    "canagliflozin|diabetic ketoacidosis": {"reports": 1892, "serious": 1852, "trend_12m": "stable", "as_of": "2018-05-01"},
    "febuxostat|cardiovascular death": {"reports": 411, "serious": 411, "trend_12m": "elevated", "as_of": "2018-09-01"},
    "gabapentin|respiratory depression": {"reports": 641, "serious": 598, "trend_12m": "rising", "as_of": "2019-08-01"},
    "warfarin|gastrointestinal haemorrhage": {"reports": 9120, "serious": 8804, "trend_12m": "stable", "as_of": "2024-01-01"},
    "sertraline|serotonin syndrome": {"reports": 1210, "serious": 1105, "trend_12m": "stable", "as_of": "2024-01-01"},
    "lisinopril|angioedema": {"reports": 4820, "serious": 4310, "trend_12m": "stable", "as_of": "2024-01-01"},
    "atorvastatin|rhabdomyolysis": {"reports": 3105, "serious": 3020, "trend_12m": "stable", "as_of": "2024-01-01"},
    "metformin|lactic acidosis": {"reports": 2960, "serious": 2915, "trend_12m": "stable", "as_of": "2024-01-01"},
    "empagliflozin|fournier's gangrene": {"reports": 31, "serious": 31, "trend_12m": "stable", "as_of": "2024-01-01"},
    "tofacitinib|pulmonary embolism": {"reports": 512, "serious": 505, "trend_12m": "elevated", "as_of": "2024-01-01"},
}

# ---------------------------------------------------------------------------
# Tool-selection test set
# ---------------------------------------------------------------------------

tool_tests = [
    ("What does 21 CFR 314.80 require for 15-day alert reports?", "search_regulations"),
    ("Under what regulation can a sponsor strengthen a warning without waiting for FDA approval?", "search_regulations"),
    ("What is the timeline after FDA notifies a holder of new safety information under 505(o)(4)?", "search_regulations"),
    ("Does the current ciprofloxacin label mention aortic aneurysm?", "search_labels"),
    ("What's in the boxed warning for febuxostat?", "search_labels"),
    ("Which label section of montelukast covers neuropsychiatric events?", "search_labels"),
    ("How many adverse event reports are there for gabapentin and respiratory depression?", "query_aems"),
    ("Is there a rising trend of Fournier's gangrene reports for canagliflozin?", "query_aems"),
    ("We're seeing reports of respiratory depression with gabapentin — is that already reflected in the label?", "query_aems;search_labels"),
    ("Reports of aortic dissection with ciprofloxacin are coming in — does the label cover this and what are we required to do?", "query_aems;search_labels;search_regulations"),
    ("Has FDA historically required label changes for suicidal ideation with montelukast?", "lookup_srlc_history"),
    ("Have SGLT2 inhibitors had safety labeling changes for perineal infections before?", "lookup_srlc_history"),
    ("Fournier's gangrene reports for empagliflozin — is the label already covering it, and did FDA act on this for the class before?", "query_aems;search_labels;lookup_srlc_history"),
    ("If we find a genuine label gap, which supplement type lets us warn immediately?", "search_regulations"),
    ("Compare montelukast suicidal ideation report volume with what its label said in 2019.", "query_aems;search_labels"),
]

# ---------------------------------------------------------------------------
# Write files
# ---------------------------------------------------------------------------

with open(HERE / "labels.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(labels[0].keys()))
    w.writeheader()
    w.writerows(labels)

with open(HERE / "regulations.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(regs[0].keys()))
    w.writeheader()
    w.writerows(regs)

with open(HERE / "srlc_validation.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(srlc[0].keys()))
    w.writeheader()
    w.writerows(srlc)

with open(HERE / "aems_fixtures.json", "w") as f:
    json.dump(fixtures, f, indent=2)

with open(HERE / "tool-selection-testset.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["question", "expected_tools"])
    w.writerows(tool_tests)

print(f"labels: {len(labels)} | regulations: {len(regs)} | "
      f"srlc cases: {len(srlc)} | fixtures: {len(fixtures)} | "
      f"tool tests: {len(tool_tests)}")
