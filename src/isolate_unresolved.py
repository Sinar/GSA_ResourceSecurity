import os
import csv

# Path Architecture
GSA_DIR = "/Users/dhuralumin/Desktop/Development/04 side_projects/GSA"
PROCESSED_DIR = os.path.join(GSA_DIR, "data", "processed")

INPUT_CSV = os.path.join(PROCESSED_DIR, "gsa_spatial_targets.csv")
VALID_CSV = os.path.join(PROCESSED_DIR, "gsa_spatial_targets_clean.csv")
MANUAL_CSV = os.path.join(PROCESSED_DIR, "gsa_manual_review.csv")

def triage_data():
    valid_records = []
    manual_records = []
    junk_count = 0

    with open(INPUT_CSV, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        for row in reader:
            if "Invalid Facility Name" in row["Resolved_Address"]:
                junk_count += 1
                continue
            elif row["Latitude"] == "NaN" or row["Longitude"] == "NaN":
                manual_records.append(row)
            else:
                valid_records.append(row)

    # Write clean, successfully geocoded data
    with open(VALID_CSV, mode='w', newline='', encoding='utf-8') as valid_out:
        writer = csv.DictWriter(valid_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(valid_records)

    # Write the 5 facilities requiring manual intervention
    with open(MANUAL_CSV, mode='w', newline='', encoding='utf-8') as manual_out:
        writer = csv.DictWriter(manual_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manual_records)

    print(f"Triage Complete:")
    print(f" - {junk_count} phantom records discarded.")
    print(f" - {len(valid_records)} verified targets saved to {VALID_CSV}")
    print(f" - {len(manual_records)} facilities isolated for manual CV intervention in {MANUAL_CSV}")

if __name__ == "__main__":
    triage_data()