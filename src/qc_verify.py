"""QC verification pass, attempted and partially negative result documented here.

Original goal: flag detections that don't structurally resemble a real data
centre (e.g. missing cooling towers/chiller yards) by comparing each
candidate's texture signature (edge density, tonal variance, computed from
the polygon-cropped region) against a reference profile built from the
facilities with independently confirmed, operator-disclosed capacity.

Finding, from actually running this against the confirmed set: neither
detector confidence nor texture statistics reliably separate correct
detections from "real building, wrong building" errors like VADS CBJ8
(Section README/QA note - confidence 0.0482, grabbed a shopping mall rather
than the facility). The eight confirmed facilities span confidence 0.004 to
0.198, overlapping the full range seen across all 124 candidates, so a
confidence threshold cannot discriminate "confirmed real data centre" from
"low-confidence detection." The texture heuristic below did not flag the
known VADS CBJ8 misdetection either: a shopping mall has plenty of
structural edges, so edge density and tonal variance alone don't
distinguish it from an actual data centre building.

Conclusion: a heuristic pass on this feature set cannot reliably substitute
for object-level verification (e.g. detecting cooling towers, chiller
yards, generator enclosures specifically). That would need a trained
object detector with labelled positive/negative examples, which is future
work (see the Full Project Methodology's unindexed-facility-discovery
section for the closest existing scoping of that kind of build).

What this script does instead, honestly: surfaces the two flags the
detector already produces on legitimate geometric grounds (FAR_FROM_CENTER,
LOW_COMPACTNESS) as a single manual-review priority list, since those two
remain the most defensible automatic signal available without a trained
classifier.
"""
import csv, os

GSA_DIR = "/sessions/relaxed-sharp-turing/mnt/GSA"
V3_CSV = os.path.join(GSA_DIR, "data", "processed", "gsa_carbon_estimates_v3.csv")
OUT_CSV = os.path.join(GSA_DIR, "data", "processed", "gsa_carbon_estimates_v3_qc.csv")

def main():
    rows = list(csv.DictReader(open(V3_CSV)))
    out_rows = []
    flagged = 0
    for r in rows:
        flags = r.get("V3_Flags", "")
        needs_review = "FAR_FROM_CENTER" in flags or "LOW_COMPACTNESS" in flags or flags == "NO_CONFIDENT_DETECTION"
        qc_flag = "NEEDS_MANUAL_REVIEW" if needs_review else ""
        if qc_flag:
            flagged += 1
        out_rows.append({**r, "QC_Flag": qc_flag})

    fields = list(out_rows[0].keys())
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    print(f"{flagged}/{len(out_rows)} detections flagged NEEDS_MANUAL_REVIEW (FAR_FROM_CENTER, LOW_COMPACTNESS, or no detection).")
    print(f"Written to {OUT_CSV}")
    print("A texture-based reference-profile classifier was attempted and did not discriminate reliably")
    print("(see module docstring) - not shipped. Object-level verification remains future work.")

if __name__ == "__main__":
    main()
