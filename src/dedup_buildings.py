import csv
from collections import defaultdict

TARGETS = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_cv_targets_final.csv"
V2 = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_carbon_estimates_v2.csv"
OUT = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_buildings_deduplicated.csv"

DISCLOSED_MW = {
    "Princeton Digital JH1": 150, "STT Johor Campus": 120,
    "STACK Infrastructure JHB01 Campus": 216,
    "AirTrunk Johor Bahru - JHB2": 270, "AirTrunk Johor Bahru - JHB3": 138,
    "AirTrunk Johor Bahru - JHB4": 142, "BDC MY06": 100, "K2 Sedenak Tech Park": 300,
}
# Genuinely distinct multi-building campuses sharing one imprecise geocode -
# independently verified (operator press release / per-building disclosed MW),
# so kept split rather than collapsed.
KEEP_SPLIT = {"AirTrunk Johor Bahru - JHB2", "AirTrunk Johor Bahru - JHB3", "AirTrunk Johor Bahru - JHB4"}
# STACK JHB01A/JHB01B are sub-buildings already summed into "STACK Infrastructure
# JHB01 Campus" (216MW disclosed ~ matches 220MW campus total per DCD press coverage) -
# drop the sub-entries to avoid counting the same campus twice.
DROP_REDUNDANT = {"STACK Infrastructure JHB01A", "STACK Infrastructure JHB01B"}

targets = list(csv.DictReader(open(TARGETS)))
v2rows = {r["Data_Center_Name"]: r for r in csv.DictReader(open(V2))}

by_coord = defaultdict(list)
for t in targets:
    by_coord[(t["Latitude"], t["Longitude"])].append(t["Data_Center_Name"])

out_rows = []
for coord, names in by_coord.items():
    names = [n for n in names if n not in DROP_REDUNDANT]
    if not names:
        continue
    split_members = [n for n in names if n in KEEP_SPLIT]
    if split_members:
        rows_for_coord = [[n] for n in names]  # each name its own row (mix of split + maybe none else here)
    else:
        rows_for_coord = [names]  # collapse all into one row

    for group in rows_for_coord:
        primary = group[0]
        v2 = v2rows.get(primary, {})
        area = v2.get("Extracted_Area_m2_v2", "")
        conf = v2.get("Confidence", "")
        flags = v2.get("V2_Flags", "")
        disclosed = [DISCLOSED_MW[n] for n in group if n in DISCLOSED_MW]
        out_rows.append({
            "Building_ID": f"{coord[0]}_{coord[1]}",
            "Latitude": coord[0], "Longitude": coord[1],
            "Tenant_Names": "; ".join(group),
            "N_Tenant_Names": len(group),
            "Area_m2": area, "CV_Confidence": conf, "CV_Flags": flags,
            "Disclosed_MW": sum(disclosed) if disclosed else "",
        })

fields = list(out_rows[0].keys())
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out_rows)

n_multi = sum(1 for r in out_rows if r["N_Tenant_Names"] > 1)
print(f"Original named entries: {len(targets)}")
print(f"Deduplicated physical-resource rows: {len(out_rows)}")
print(f"Rows representing 2+ tenant names collapsed into one building: {n_multi}")
