"""Re-run the (already-downloaded) raw satellite captures through the polygon-
aware detector in improved_cv.py, producing corrected footprint areas
(from the actual contour, not its bounding box) and a polygon outline per
facility for the visual library.

Does not re-download imagery (no new Static Maps API calls); operates on
the raw captures already saved under data/satellite_captures/*_raw.png from
the original acquisition run.
"""
import os, csv, sys
sys.path.insert(0, os.path.dirname(__file__))
from improved_cv import detect_building_box, draw_and_save

GSA_DIR = "/sessions/relaxed-sharp-turing/mnt/GSA"
RAW_DIR = os.path.join(GSA_DIR, "data", "satellite_captures")
TARGETS_CSV = os.path.join(GSA_DIR, "data", "processed", "gsa_cv_targets_final.csv")
OUT_CSV = os.path.join(GSA_DIR, "data", "processed", "gsa_carbon_estimates_v3.csv")
BBOX_OUT_DIR = os.path.join(GSA_DIR, "data", "satellite_captures_v3")
os.makedirs(BBOX_OUT_DIR, exist_ok=True)

def safe_name(name):
    return "".join([c if c.isalnum() else "_" for c in name])

def main():
    targets = list(csv.DictReader(open(TARGETS_CSV)))
    out_rows = []
    no_detection = 0
    for t in targets:
        name = t["Data_Center_Name"]
        raw_path = os.path.join(RAW_DIR, f"{safe_name(name)}_raw.png")
        bbox_path = os.path.join(BBOX_OUT_DIR, f"{safe_name(name)}_bbox_v3.png")
        if not os.path.exists(raw_path):
            print(f"[!] Missing raw capture for {name}, skipping")
            continue
        result = detect_building_box(raw_path)
        draw_and_save(raw_path, bbox_path, result)
        if result is None:
            no_detection += 1
            out_rows.append({
                "Data_Center_Name": name,
                "Extracted_Area_m2_v3": "",
                "Extracted_Area_m2_bbox": "",
                "Confidence": "",
                "V3_Flags": "NO_CONFIDENT_DETECTION",
                "Polygon": "",
            })
            continue
        out_rows.append({
            "Data_Center_Name": name,
            "Extracted_Area_m2_v3": result["area_m2"],
            "Extracted_Area_m2_bbox": result["bbox_area_m2"],
            "Confidence": result["confidence"],
            "V3_Flags": ";".join(result["flags"]),
            "Polygon": result["polygon"],
        })

    fields = ["Data_Center_Name", "Extracted_Area_m2_v3", "Extracted_Area_m2_bbox", "Confidence", "V3_Flags", "Polygon"]
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    detected = [r for r in out_rows if r["Extracted_Area_m2_v3"] != ""]
    if detected:
        polygon_total = sum(float(r["Extracted_Area_m2_v3"]) for r in detected)
        bbox_total = sum(float(r["Extracted_Area_m2_bbox"]) for r in detected)
        pct_change = 100 * (polygon_total - bbox_total) / bbox_total if bbox_total else 0
        print(f"Processed {len(out_rows)} targets: {len(detected)} detected, {no_detection} no-detection.")
        print(f"Sum of bounding-box areas:  {bbox_total:,.0f} m2")
        print(f"Sum of polygon (actual footprint) areas: {polygon_total:,.0f} m2")
        print(f"Polygon area is {pct_change:+.1f}% vs bounding-box area across the detected set.")
    print(f"Written to {OUT_CSV}")
    print(f"Annotated polygon overlays written to {BBOX_OUT_DIR}")

if __name__ == "__main__":
    main()
