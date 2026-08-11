import os
import csv

# Path Architecture
GSA_DIR = "/Users/dhuralumin/Desktop/Development/04 side_projects/GSA"
PROCESSED_DIR = os.path.join(GSA_DIR, "data", "processed")

CLEAN_CSV = os.path.join(PROCESSED_DIR, "gsa_spatial_targets_clean.csv")
MANUAL_CSV = os.path.join(PROCESSED_DIR, "gsa_manual_review.csv")
CV_READY_CSV = os.path.join(PROCESSED_DIR, "gsa_cv_targets_final.csv")
POLICY_GHOST_CSV = os.path.join(PROCESSED_DIR, "gsa_policy_ghost_facilities.csv")

def finalize_datasets():
    cv_records = []
    ghost_records = []
    fieldnames = []

    # 1. Ingest the 124 automatically clean records
    with open(CLEAN_CSV, mode='r', encoding='utf-8') as clean_in:
        reader = csv.DictReader(clean_in)
        fieldnames = reader.fieldnames
        for row in reader:
            cv_records.append(row)

    # 2. Ingest the 5 manual records (3 resolved, 2 unresolved)
    with open(MANUAL_CSV, mode='r', encoding='utf-8') as manual_in:
        reader = csv.DictReader(manual_in)
        for row in reader:
            if row["Latitude"] != "NaN" and row["Longitude"] != "NaN" and row["Latitude"] != "":
                row["Resolved_Address"] = "Resolved via Manual CV Intervention"
                cv_records.append(row)
            else:
                row["Resolved_Address"] = "Ghost Facility - Diverted to Policy Audit"
                ghost_records.append(row)

    # 3. Export 127 verifiable spatial targets for the CV pipeline
    with open(CV_READY_CSV, mode='w', newline='', encoding='utf-8') as cv_out:
        writer = csv.DictWriter(cv_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cv_records)

    # 4. Export 2 missing facilities for the SOP-02 Policy Audit
    if ghost_records:
        with open(POLICY_GHOST_CSV, mode='w', newline='', encoding='utf-8') as ghost_out:
            writer = csv.DictWriter(ghost_out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(ghost_records)

    print("Unified Dataset Finalization Complete.")
    print(f" - {len(cv_records)} targets secured for S_i Computer Vision ingestion: {CV_READY_CSV}")
    print(f" - {len(ghost_records)} unbuilt/conceptual facilities diverted to Policy Audit: {POLICY_GHOST_CSV}")

if __name__ == "__main__":
    finalize_datasets()