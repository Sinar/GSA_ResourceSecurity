"""Builds the final site manifest.json from the polygon-corrected (v4) master
CSV, plus regenerates images/thumbs from the v3 polygon-overlay captures
(previously the site used the v2 bounding-box overlay images).

Adds per-sqft resource intensity and a relatable, Malaysia-flavoured
comparison line (rice cooker / home EV charger equivalents) per the site
request, and fixes the "Setul" -> "Sentul" source-data typo in the tenant name.
"""
import csv, json, os
from PIL import Image

GSA_DIR = "/sessions/relaxed-sharp-turing/mnt/GSA"
MASTER_V4 = os.path.join(GSA_DIR, "data", "processed", "GSA_Master_Facility_Database_v4.csv")
RAW_V3_DIR = os.path.join(GSA_DIR, "data", "satellite_captures_v3")
OUT_DIR = "/sessions/relaxed-sharp-turing/mnt/outputs/site_build_v4"
IMG_DIR = os.path.join(OUT_DIR, "images")
THUMB_DIR = os.path.join(OUT_DIR, "thumbs")
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

RICE_COOKER_W = 800     # typical continuous draw, Malaysian household rice cooker
EV_CHARGER_KW = 7       # typical home Level-2 EV charger draw

def safe_name(name):
    return "".join([c if c.isalnum() else "_" for c in name])

def fun_comparison(power_kw):
    if not power_kw:
        return ""
    n_cookers = power_kw * 1000 / RICE_COOKER_W
    n_cars = power_kw / EV_CHARGER_KW
    if n_cookers < 1000:
        cooker_str = f"~{n_cookers:,.0f} rice cookers"
    else:
        cooker_str = f"~{n_cookers/1000:,.1f}k rice cookers"
    if n_cars < 1000:
        car_str = f"~{n_cars:,.0f} home EV chargers"
    else:
        car_str = f"~{n_cars/1000:,.1f}k home EV chargers"
    return f"Running continuously, this facility's estimated power draw is comparable to {cooker_str} left on non-stop, or {car_str} all charging at once, around the clock."

rows = list(csv.DictReader(open(MASTER_V4)))
manifest = []
for r in rows:
    primary_tenant = r["Tenant_Names"].split(";")[0].strip()
    fname = f"{safe_name(primary_tenant)}_bbox_v3"
    src_png = os.path.join(RAW_V3_DIR, f"{fname}.png")
    img_jpg = f"images/{fname}.jpg"
    thumb_jpg = f"thumbs/{fname}.jpg"

    if os.path.exists(src_png):
        im = Image.open(src_png).convert("RGB")
        im.save(os.path.join(IMG_DIR, f"{fname}.jpg"), "JPEG", quality=85)
        thumb = im.copy()
        thumb.thumbnail((300, 300))
        thumb.save(os.path.join(THUMB_DIR, f"{fname}.jpg"), "JPEG", quality=80)
    else:
        img_jpg = ""
        thumb_jpg = ""

    power_kw = float(r["Est_Facility_Power_kW"]) if r["Est_Facility_Power_kW"] else None

    manifest.append({
        "id": r["Building_ID"],
        "tenants": r["Tenant_Names"],
        "n_tenants": r["N_Tenant_Names"],
        "lat": float(r["Building_ID"].split("_")[0]),
        "lon": float(r["Building_ID"].split("_")[1]),
        "area_m2": r["Area_m2"],
        "bbox_area_m2": r.get("Bbox_Area_m2", ""),
        "confidence": "",
        "flags": r["CV_Flags"],
        "qc_flag": r.get("QC_Flag", ""),
        "polygon": r.get("Polygon", ""),
        "disclosed_mw": r["Est_Facility_Power_kW"] and ("DISCLOSED" in r["Power_Source"] and r["Power_Source"].split("(")[1].split(" MW")[0]) or "",
        "power_kw": r["Est_Facility_Power_kW"],
        "energy_mwh_yr": r["Est_Annual_Energy_MWh"],
        "carbon_tco2e_yr": r["Est_Annual_Carbon_tCO2e"],
        "water_optimized_l_yr": r["Est_Water_Optimized_L_yr"],
        "water_regional_l_yr": r["Est_Water_Regional_L_yr"],
        "waste_heat_gj_yr": r["Est_Waste_Heat_GJ_yr"],
        "power_w_per_sqft": r["Power_W_per_sqft"],
        "water_l_per_sqft_yr": r["Water_L_per_sqft_yr"],
        "carbon_kg_per_sqft_yr": r["Carbon_kg_per_sqft_yr"],
        "fun_comparison": fun_comparison(power_kw),
        "power_source": r["Power_Source"],
        "status": r["Status"],
        "qa_notes": r["QA_Notes"],
        "image": img_jpg,
        "thumb": thumb_jpg,
    })

with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=1)

missing_images = sum(1 for m in manifest if not m["image"])
print(f"Manifest built: {len(manifest)} facilities, {missing_images} missing source images (kept blank, site already handles this with a placeholder).")
print(f"Written to {os.path.join(OUT_DIR, 'manifest.json')}")
print(f"Images: {IMG_DIR}\nThumbs: {THUMB_DIR}")
