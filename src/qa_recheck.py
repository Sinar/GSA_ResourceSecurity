# Independent verification re-check, run against the full deduplicated
# building set rather than the original detector's validation sample.
# Two checks: (1) a geometric re-check for border-touching/full-frame
# bounding boxes on the redesigned detector's output, and (2) a
# coordinate-region plausibility check comparing each building's
# coordinate against the Malaysian region implied by its recorded City
# field. See the Verification and QA Report for full findings and the
# full project methodology, Section 3.5, for a summary.
#
# This does not auto-apply findings; see apply_qa_corrections.py for that.
# It is a reporting/discovery script, run manually and reviewed before any
# flags are applied to the pipeline data.
import csv, os, cv2, numpy as np

BUILDINGS_CSV = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_buildings_deduplicated.csv"
SPATIAL_CSV = "/sessions/relaxed-sharp-turing/mnt/GSA/data/processed/gsa_spatial_targets_clean.csv"
CAPTURE_DIR = "/sessions/relaxed-sharp-turing/mnt/GSA/data/satellite_captures"
IMG_DIM = 600

REGIONS = [
    (1.2, 1.9, 103.3, 104.3, "Johor"),
    (2.8, 3.35, 101.3, 101.85, "Klang Valley/KL/Selangor"),
    (2.5, 2.85, 101.6, 102.1, "Negeri Sembilan"),
    (5.9, 6.7, 100.1, 100.6, "Kedah/Penang"),
    (5.2, 5.5, 100.1, 100.4, "Penang"),
    (1.4, 1.65, 110.2, 110.5, "Kuching/Sarawak"),
    (5.9, 6.2, 116.0, 116.3, "Kota Kinabalu/Sabah"),
    (3.6, 4.3, 103.0, 103.6, "Pahang"),
]

def safe_name(name):
    return "".join([c if c.isalnum() else "_" for c in name])

def find_green_box(bbox_path):
    img = cv2.imread(bbox_path)
    if img is None:
        return None
    b, g, r = cv2.split(img)
    mask = (g > 200) & (b < 80) & (r < 80)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())

def geometric_recheck(rows):
    issues = []
    for r in rows:
        sn = safe_name(r["Tenant_Names"].split(";")[0].strip())
        bbox_path = os.path.join(CAPTURE_DIR, f"{sn}_bbox.png")
        if not os.path.exists(bbox_path):
            continue
        box = find_green_box(bbox_path)
        if box is None:
            continue
        x0, y0, x1, y1 = box
        border_touches = sum([x0 <= 2, y0 <= 2, x1 >= IMG_DIM - 3, y1 >= IMG_DIM - 3])
        if border_touches >= 2 and not r["CV_Flags"].strip():
            issues.append((r["Building_ID"], r["Tenant_Names"], "BORDER_HUGGING_BOX or FULL_FRAME_BOX"))
    return issues

def region_for(lat, lon):
    lat, lon = float(lat), float(lon)
    for lat_min, lat_max, lon_min, lon_max, label in REGIONS:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return label
    return "UNMAPPED_REGION (check manually - may resolve outside Malaysia)"

def coordinate_region_recheck(rows, spatial):
    issues = []
    for r in rows:
        primary = r["Tenant_Names"].split(";")[0].strip()
        city = spatial.get(primary, {}).get("City", "N/A")
        if not r["Latitude"]:
            continue
        region = region_for(r["Latitude"], r["Longitude"])
        if "UNMAPPED_REGION" in region:
            issues.append((r["Building_ID"], primary, city, region))
    return issues

if __name__ == "__main__":
    rows = list(csv.DictReader(open(BUILDINGS_CSV)))
    spatial = {r["Data_Center_Name"]: r for r in csv.DictReader(open(SPATIAL_CSV))}

    print("=== Geometric re-check (unflagged border-hugging/full-frame boxes) ===")
    for issue in geometric_recheck(rows):
        print(f"  {issue[1]} (Building_ID={issue[0]}): {issue[2]}")

    print("\n=== Coordinate-region plausibility re-check (unmapped/out-of-region coordinates) ===")
    for issue in coordinate_region_recheck(rows, spatial):
        print(f"  {issue[1]} (Building_ID={issue[0]}): City='{issue[2]}', region check='{issue[3]}'")
    print("\nNote: this script flags candidates for manual review. It does not itself")
    print("determine ground truth; findings should be visually confirmed (as done for")
    print("Digital Halo JHB1) before being applied via apply_qa_corrections.py.")
