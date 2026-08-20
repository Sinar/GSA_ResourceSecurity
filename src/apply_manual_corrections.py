"""Merges manually-reviewed polygons (from tools/annotate/annotate.html,
exported as gsa_manual_corrections.json) back into the v4 dataset.

For each corrected Building_ID:
- if a polygon was drawn, replaces Area_m2 (recomputed via the shoelace
  formula on the reviewer's polygon) and Polygon, and adds a
  MANUALLY_VERIFIED flag
- if marked "no confident building visible", sets CV_Flags to
  NO_CONFIDENT_DETECTION and excludes it from resource totals, same as an
  automated non-detection

Run after the RA exports her corrections file, then re-run
resource_estimates_v4.py -> finalize_v4.py -> build_manifest_v4.py in that
order to propagate the corrections through to the site.
"""
import csv, json, sys

GSA_DIR = "/sessions/relaxed-sharp-turing/mnt/GSA"
V4_DEDUP = GSA_DIR + "/data/processed/gsa_buildings_deduplicated_v3.csv"
OUT = GSA_DIR + "/data/processed/gsa_buildings_deduplicated_v3.csv"  # overwrites in place; v3 CSV is the dedup output resource_estimates_v4.py reads
PIXEL_TO_M2 = 0.348

def polygon_area_px(points):
    # shoelace formula
    n = len(points)
    area = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0

def main(corrections_path):
    corrections = json.load(open(corrections_path))
    rows = list(csv.DictReader(open(V4_DEDUP)))

    # Building_ID collides for facilities sharing one imprecise geocode (e.g. the
    # AirTrunk JHB2/3/4 split rows) - skip applying a Building_ID-keyed correction
    # to any row whose Building_ID isn't unique in this dataset, since we can't
    # tell which of the tied rows it was meant for. Tenant_Names-keyed corrections
    # (the current tool format) don't have this problem and are applied normally.
    from collections import Counter
    bid_counts = Counter(r["Building_ID"] for r in rows)

    applied = 0
    skipped_ambiguous = []
    for r in rows:
        c = corrections.get(r["Tenant_Names"])
        if not c and bid_counts[r["Building_ID"]] == 1:
            c = corrections.get(r["Building_ID"])
        if not c and bid_counts[r["Building_ID"]] > 1 and r["Building_ID"] in corrections:
            skipped_ambiguous.append(r["Tenant_Names"])
            continue
        if not c:
            continue
        applied += 1
        if c.get("no_building"):
            r["Area_m2"] = ""
            r["CV_Flags"] = "NO_CONFIDENT_DETECTION"
            r["Polygon"] = ""
            r["QC_Flag"] = "MANUALLY_REVIEWED:NO_BUILDING"
        else:
            # Multi-block facilities (separate physical buildings on one row) are
            # reviewed as several independent polygons, not one connected shape -
            # sum each block's area rather than treating them as one contour, which
            # would self-intersect and give a meaningless shoelace result.
            blocks = c.get("blocks") or ([c["polygon"]] if c.get("polygon") else [])
            area_m2 = round(sum(polygon_area_px(b) for b in blocks) * PIXEL_TO_M2, 2)
            r["Area_m2"] = area_m2
            r["Polygon"] = json.dumps(blocks)  # list of blocks, each a list of [x,y] points
            existing_flags = [f for f in r["CV_Flags"].split(";") if f]
            if "MANUALLY_VERIFIED" not in existing_flags:
                existing_flags.append("MANUALLY_VERIFIED")
            r["CV_Flags"] = ";".join(existing_flags)
            n_blocks = len(blocks)
            r["QC_Flag"] = f"MANUALLY_REVIEWED_BY:{c.get('reviewer','unspecified')}" + (f":{n_blocks}_BLOCKS" if n_blocks > 1 else "")

    fields = list(rows[0].keys())
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Applied {applied} manual corrections to {OUT}")
    if skipped_ambiguous:
        print(f"Skipped {len(skipped_ambiguous)} row(s) sharing a Building_ID with another row (ambiguous which the correction was meant for):")
        for name in skipped_ambiguous:
            print(f"  - {name}")
        print("These need a Tenant_Names-keyed correction (current tool version) before they can be applied.")
    print("Next: re-run resource_estimates_v4.py, then finalize_v4.py, then build_manifest_v4.py")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 apply_manual_corrections.py gsa_manual_corrections.json")
        sys.exit(1)
    main(sys.argv[1])
