"""Same collapsing/exception logic as dedup_buildings.py, pointed at the v3
QC'd, polygon-corrected detection output instead of v2 (bounding-box area).
See dedup_buildings.py for the DISCLOSED_MW / KEEP_SPLIT / DROP_REDUNDANT
provenance notes, unchanged here.
"""
import csv
from collections import defaultdict

TARGETS = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_cv_targets_final.csv"
V3 = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_carbon_estimates_v3_qc.csv"
OUT = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_buildings_deduplicated_v3.csv"

DISCLOSED_MW = {
    "Princeton Digital JH1": 150, "STT Johor Campus": 120,
    "STACK Infrastructure JHB01 Campus": 216,
    "AirTrunk Johor Bahru - JHB2": 270, "AirTrunk Johor Bahru - JHB3": 138,
    "AirTrunk Johor Bahru - JHB4": 142, "BDC MY06": 100, "K2 Sedenak Tech Park": 300,
}
KEEP_SPLIT = {"AirTrunk Johor Bahru - JHB2", "AirTrunk Johor Bahru - JHB3", "AirTrunk Johor Bahru - JHB4"}
DROP_REDUNDANT = {"STACK Infrastructure JHB01A", "STACK Infrastructure JHB01B"}

targets = list(csv.DictReader(open(TARGETS)))
v3rows = {r["Data_Center_Name"]: r for r in csv.DictReader(open(V3))}

by_coord = defaultdict(list)
for t in targets:
    by_coord[(t["Latitude"], t["Longitude"])].append(t["Data_Center_Name"])

out_rows = []
for coord, names in by_coord.items():
    names = [n for n in names if n not in DROP_REDUNDANT]
    if not names:
        continue
    split_members = [n for n in names if n in KEEP_SPLIT]
    rows_for_coord = [[n] for n in names] if split_members else [names]

    for group in rows_for_coord:
        primary = group[0]
        v3 = v3rows.get(primary, {})
        area = v3.get("Extracted_Area_m2_v3", "")
        bbox_area = v3.get("Extracted_Area_m2_bbox", "")
        conf = v3.get("Confidence", "")
        flags = v3.get("V3_Flags", "")
        qc_flag = v3.get("QC_Flag", "")
        polygon = v3.get("Polygon", "")
        disclosed = [DISCLOSED_MW[n] for n in group if n in DISCLOSED_MW]
        out_rows.append({
            "Building_ID": f"{coord[0]}_{coord[1]}",
            "Latitude": coord[0], "Longitude": coord[1],
            "Tenant_Names": "; ".join(group),
            "N_Tenant_Names": len(group),
            "Area_m2": area, "Bbox_Area_m2": bbox_area,
            "CV_Confidence": conf, "CV_Flags": flags, "QC_Flag": qc_flag,
            "Polygon": polygon,
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
print(f"Written to {OUT}")
