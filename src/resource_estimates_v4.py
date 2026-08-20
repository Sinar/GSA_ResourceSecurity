"""Same formulas as resource_estimates_v3.py, run against the v3 (polygon-area,
QC-flagged) deduplicated building set instead of the v2 (bounding-box area) set.
"""
import csv

IN_CSV = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_buildings_deduplicated_v3.csv"
OUT_CSV = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_resource_extraction_estimates_v4.csv"

POWER_DENSITY_KW_M2 = 1.5
PUE = 1.4
GRID_EF = 0.54
HOURS_YEAR = 8760
WUE_OPTIMIZED_L_KWH = 0.15
WUE_REGIONAL_L_KWH = 2.2

rows = list(csv.DictReader(open(IN_CSV)))
out_rows = []

for r in rows:
    flags = r["CV_Flags"]
    # A missing/no-confident-detection footprint should only exclude a facility
    # from resource totals when we also have no other basis for its power figure.
    # Disclosed-capacity facilities get their MW from the operator, not from
    # image area, so a reviewer being unable to visually confirm the building in
    # a low-quality or out-of-date satellite frame should not zero out an
    # independently confirmed capacity. A bad coordinate (genuinely wrong
    # location) is a different problem and excludes regardless of disclosure.
    coordinate_bad = "COORDINATE_OUTSIDE_MALAYSIA" in flags
    no_footprint = "NO_CONFIDENT_DETECTION" in flags or not r["Area_m2"]
    excluded = coordinate_bad or (no_footprint and not r["Disclosed_MW"])

    base = {
        "Building_ID": r["Building_ID"], "Tenant_Names": r["Tenant_Names"],
        "N_Tenant_Names": r["N_Tenant_Names"], "Area_m2": r["Area_m2"],
        "Bbox_Area_m2": r["Bbox_Area_m2"],
        "CV_Flags": flags, "QC_Flag": r.get("QC_Flag", ""), "Polygon": r.get("Polygon", ""),
    }

    if excluded:
        out_rows.append({**base, "Est_Facility_Power_kW": "", "Est_Annual_Energy_MWh": "",
                          "Est_Annual_Carbon_tCO2e": "", "Est_Water_Optimized_L_yr": "",
                          "Est_Water_Regional_L_yr": "", "Est_Waste_Heat_GJ_yr": "",
                          "Power_Source": "",
                          "Status": "EXCLUDED - unconfirmed location"})
        continue

    area = float(r["Area_m2"]) if r["Area_m2"] else None
    if r["Disclosed_MW"]:
        facility_power_kw = float(r["Disclosed_MW"]) * 1000
        power_source = f"DISCLOSED ({r['Disclosed_MW']} MW)"
        status = "OK - disclosed capacity" if area else "OK - disclosed capacity (no confirmed footprint image)"
    else:
        facility_power_kw = area * POWER_DENSITY_KW_M2 * PUE
        power_source = "MODELED (unvalidated coefficient)"
        status = "MODELED - low confidence"

    it_power_kw = facility_power_kw / PUE
    it_energy_kwh = it_power_kw * HOURS_YEAR
    facility_energy_kwh = facility_power_kw * HOURS_YEAR
    carbon_t = (facility_energy_kwh * GRID_EF) / 1000
    water_opt_l = it_energy_kwh * WUE_OPTIMIZED_L_KWH
    water_reg_l = it_energy_kwh * WUE_REGIONAL_L_KWH
    waste_heat_gj = facility_energy_kwh * 3.6 / 1000

    out_rows.append({**base,
        "Est_Facility_Power_kW": round(facility_power_kw, 1),
        "Est_Annual_Energy_MWh": round(facility_energy_kwh / 1000, 1),
        "Est_Annual_Carbon_tCO2e": round(carbon_t, 1),
        "Est_Water_Optimized_L_yr": round(water_opt_l, 0),
        "Est_Water_Regional_L_yr": round(water_reg_l, 0),
        "Est_Waste_Heat_GJ_yr": round(waste_heat_gj, 1),
        "Power_Source": power_source, "Status": status,
    })

fields = list(out_rows[0].keys())
with open(OUT_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out_rows)

included = [r for r in out_rows if r["Est_Facility_Power_kW"] != ""]
disclosed = [r for r in included if "DISCLOSED" in r["Power_Source"]]
modeled = [r for r in included if "MODELED" in r["Power_Source"]]

def agg(rs, key): return sum(r[key] for r in rs)

print(f"Deduplicated rows: {len(out_rows)} | Included: {len(included)} (disclosed={len(disclosed)}, modeled={len(modeled)}) | Excluded: {len(out_rows)-len(included)}")
print(f"Aggregate power: {agg(included,'Est_Facility_Power_kW')/1000:.1f} MW  (disclosed: {agg(disclosed,'Est_Facility_Power_kW')/1000:.1f} MW, modeled: {agg(modeled,'Est_Facility_Power_kW')/1000:.1f} MW)")
print(f"Aggregate annual energy: {agg(included,'Est_Annual_Energy_MWh')/1000:.1f} GWh/yr")
print(f"Aggregate annual carbon: {agg(included,'Est_Annual_Carbon_tCO2e'):,.0f} tCO2e/yr")
print(f"Aggregate water (optimized): {agg(included,'Est_Water_Optimized_L_yr')/1e6:,.1f} million L/yr")
print(f"Aggregate water (regional/tropical): {agg(included,'Est_Water_Regional_L_yr')/1e6:,.1f} million L/yr")
print(f"Aggregate waste heat: {agg(included,'Est_Waste_Heat_GJ_yr'):,.0f} GJ/yr")
print(f"As % of Peninsular Malaysia annual grid generation (~155,000 GWh/yr): {100*agg(included,'Est_Annual_Energy_MWh')/1000/155000:.1f}%")
