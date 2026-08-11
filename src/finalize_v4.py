"""Final consolidation of the polygon-corrected (v4) dataset:
- excludes the 3 independently-confirmed out-of-country geocoding failures
  (same Building_IDs previously flagged via apply_qa_corrections.py)
- carries over existing QA_Notes from the published master CSV, keyed on
  Tenant_Names (not Building_ID - see the AirTrunk campus bug writeup for why)
- fixes "Setul" -> "Sentul" (source data typo; real KL district)
- adds per-m2 (and per-sqft) resource intensity and a relatable comparison line
"""
import csv

V4 = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_resource_extraction_estimates_v4.csv"
OLD_MASTER = "/sessions/relaxed-sharp-turing/mnt/GSA/docs/GSA_Master_Facility_Database.csv"
OUT = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/GSA_Master_Facility_Database_v4.csv"

OUTSIDE_MALAYSIA_IDS = {
    "1.2934578_103.8602054": "COORDINATE_OUTSIDE_MALAYSIA",  # STT Johor 1 / STT Johor Campus -> Marina Bay, SG
    "1.2832744_103.8508826": "COORDINATE_OUTSIDE_MALAYSIA",  # Empyrion Digital MY1 -> Marina Bay, SG
    "14.5898243_121.1379526": "COORDINATE_OUTSIDE_MALAYSIA", # Digital Halo JHB1 -> Metro Manila, PH
}

SQM_PER_SQFT = 0.092903

rows = list(csv.DictReader(open(V4)))
old_rows = {r["Tenant_Names"]: r for r in csv.DictReader(open(OLD_MASTER))}

out_rows = []
for r in rows:
    bid = r["Building_ID"]
    tenants = r["Tenant_Names"].replace("Setul", "Sentul")
    qa_note = old_rows.get(r["Tenant_Names"], {}).get("QA_Notes", "")

    status = r["Status"]
    if bid in OUTSIDE_MALAYSIA_IDS:
        status = "EXCLUDED - unconfirmed location"
        r = {**r, "Est_Facility_Power_kW": "", "Est_Annual_Energy_MWh": "",
             "Est_Annual_Carbon_tCO2e": "", "Est_Water_Optimized_L_yr": "",
             "Est_Water_Regional_L_yr": "", "Est_Waste_Heat_GJ_yr": "", "Power_Source": ""}
        cv_flags = (r.get("CV_Flags", "") + ";" + OUTSIDE_MALAYSIA_IDS[bid]).strip(";")
    else:
        cv_flags = r.get("CV_Flags", "")

    area_m2 = float(r["Area_m2"]) if r["Area_m2"] else None
    power_kw = float(r["Est_Facility_Power_kW"]) if r["Est_Facility_Power_kW"] else None
    water_reg_l = float(r["Est_Water_Regional_L_yr"]) if r["Est_Water_Regional_L_yr"] else None
    carbon_t = float(r["Est_Annual_Carbon_tCO2e"]) if r["Est_Annual_Carbon_tCO2e"] else None

    per_sqft = {}
    if area_m2 and area_m2 > 0:
        area_sqft = area_m2 / SQM_PER_SQFT
        per_sqft["Power_W_per_sqft"] = round((power_kw * 1000 / area_sqft), 2) if power_kw else ""
        per_sqft["Water_L_per_sqft_yr"] = round((water_reg_l / area_sqft), 1) if water_reg_l else ""
        per_sqft["Carbon_kg_per_sqft_yr"] = round((carbon_t * 1000 / area_sqft), 2) if carbon_t else ""
    else:
        per_sqft = {"Power_W_per_sqft": "", "Water_L_per_sqft_yr": "", "Carbon_kg_per_sqft_yr": ""}

    out_rows.append({
        "Building_ID": bid, "Tenant_Names": tenants, "N_Tenant_Names": r["N_Tenant_Names"],
        "Area_m2": r["Area_m2"], "Bbox_Area_m2": r.get("Bbox_Area_m2", ""),
        "CV_Flags": cv_flags, "QC_Flag": r.get("QC_Flag", ""), "Polygon": r.get("Polygon", ""),
        "Est_Facility_Power_kW": r["Est_Facility_Power_kW"],
        "Est_Annual_Energy_MWh": r["Est_Annual_Energy_MWh"],
        "Est_Annual_Carbon_tCO2e": r["Est_Annual_Carbon_tCO2e"],
        "Est_Water_Optimized_L_yr": r["Est_Water_Optimized_L_yr"],
        "Est_Water_Regional_L_yr": r["Est_Water_Regional_L_yr"],
        "Est_Waste_Heat_GJ_yr": r["Est_Waste_Heat_GJ_yr"],
        "Power_Source": r["Power_Source"], "Status": status,
        **per_sqft,
        "QA_Notes": qa_note,
    })

fields = list(out_rows[0].keys())
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out_rows)

included = [r for r in out_rows if r["Est_Facility_Power_kW"] not in ("", None)]
disclosed = [r for r in included if "DISCLOSED" in r["Power_Source"]]
modeled = [r for r in included if "MODELED" in r["Power_Source"]]

def agg(rs, key): return sum(float(r[key]) for r in rs if r[key] not in ("", None))

print(f"Total rows: {len(out_rows)} | Included: {len(included)} (disclosed={len(disclosed)}, modeled={len(modeled)}) | Excluded: {len(out_rows)-len(included)}")
print(f"Aggregate power: {agg(included,'Est_Facility_Power_kW')/1000:.1f} MW  (disclosed: {agg(disclosed,'Est_Facility_Power_kW')/1000:.1f} MW, modeled: {agg(modeled,'Est_Facility_Power_kW')/1000:.1f} MW)")
print(f"Aggregate annual energy: {agg(included,'Est_Annual_Energy_MWh')/1000:.1f} GWh/yr")
print(f"Aggregate annual carbon: {agg(included,'Est_Annual_Carbon_tCO2e'):,.0f} tCO2e/yr")
print(f"Aggregate water (regional/tropical): {agg(included,'Est_Water_Regional_L_yr')/1e6:,.1f} million L/yr")
print(f"Written to {OUT}")
