# Applies findings from the independent Verification and QA Report to the
# deduplicated building dataset, before resource_estimates_v3.py is run.
#
# This script exists so the QA re-check documented in the full project
# methodology (Section 3.5) is a reproducible pipeline step, not a manual
# one-off edit to the data file. Run this after dedup_buildings.py and
# before resource_estimates_v3.py.
import csv

IN_CSV = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_buildings_deduplicated.csv"

# Findings from the independent Verification and QA Report (Sections 4.2
# and 5). Each entry adds one or more CV_Flags values that
# resource_estimates_v3.py's exclusion logic checks for.
# COORDINATE_OUTSIDE_MALAYSIA triggers exclusion from the resource-
# estimation aggregate; BORDER_HUGGING_BOX_QA is informational only.
QA_FLAG_ADDITIONS = {
    # Building_ID -> list of flags to append.
    "14.5898243_121.1379526": ["COORDINATE_OUTSIDE_MALAYSIA"],  # Digital Halo JHB1 - resolves to Metro Manila, PH
    "1.522303_110.3404311": ["BORDER_HUGGING_BOX_QA"],          # MaNaDr Kuching
    "1.2934578_103.8602054": ["BORDER_HUGGING_BOX_QA", "COORDINATE_OUTSIDE_MALAYSIA"],  # STT Johor 1 - resolves to Marina Bay, Singapore (found via land-cover rollout, Section 5)
    "1.2832744_103.8508826": ["COORDINATE_OUTSIDE_MALAYSIA"],   # Empyrion Digital MY1 - same corridor as STT Johor 1, resolves to Singapore
    "6.5058846_100.4250382": ["BORDER_HUGGING_BOX_QA"],         # Area Group - Delapan SBEZ Campus
    "3.0661176_101.4857025": ["BORDER_HUGGING_BOX_QA"],         # Strateq DC-2
}

rows = list(csv.DictReader(open(IN_CSV)))
applied = 0
for r in rows:
    additions = QA_FLAG_ADDITIONS.get(r["Building_ID"], [])
    for addition in additions:
        if addition not in r["CV_Flags"]:
            r["CV_Flags"] = f"{r['CV_Flags']};{addition}" if r["CV_Flags"] else addition
            applied += 1

fields = list(rows[0].keys())
with open(IN_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"Applied {applied} QA flag(s) to {IN_CSV}")
