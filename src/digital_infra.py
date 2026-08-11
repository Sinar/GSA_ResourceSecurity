import os
import csv
import time
import googlemaps

# 1. Enforce GSA Path Architecture
ROOT_DIR = "/Users/dhuralumin/Desktop/Development/"
GSA_DIR = os.path.join(ROOT_DIR, "04 side_projects", "GSA")
PROCESSED_DIR = os.path.join(GSA_DIR, "data", "processed")

INPUT_CSV = os.path.join(PROCESSED_DIR, "gsa_datacenter_coordinates.csv")
OUTPUT_CSV = os.path.join(PROCESSED_DIR, "gsa_spatial_targets.csv")

# 2. API Configuration
API_KEY = "AIzaSyDqgaMR2t5LNXfajyb33DXbFRYzfR1PTrQ"

def get_coordinates(facility_name, city, gmaps_client):
    # Query the Places API for precise facility coordinates.
    if "Right Place" in facility_name or "Request Quote" in facility_name:
        return None, None, "Invalid Facility Name"

    search_query = f"{facility_name} Data Center, {city}, Malaysia"
    
    try:
        places_result = gmaps_client.places(query=search_query)
        
        if places_result['status'] == 'OK' and len(places_result['results']) > 0:
            location = places_result['results'][0]['geometry']['location']
            return location['lat'], location['lng'], places_result['results'][0].get('formatted_address', 'Address Resolved via API')
        else:
            return None, None, "API Match Failed"
            
    except Exception as e:
        print(f"        [!] API Error: {e}")
        return None, None, str(e)

def execute_pipeline():
    print(f"Initializing Google Maps API Geocoder.\nIngesting: {INPUT_CSV}\nTargeting: {OUTPUT_CSV}")
    
    # Corrected conditional
    if API_KEY == "YOUR_GOOGLE_MAPS_API_KEY_HERE" or API_KEY == "":
        print("\n[!] FATAL ERROR: You must insert your Google Maps API Key into src/digital_infra.py before execution.")
        return

    gmaps = googlemaps.Client(key=API_KEY)
    
    processed_count = 0
    resolved_count = 0
    
    with open(INPUT_CSV, mode='r', encoding='utf-8') as infile, \
         open(OUTPUT_CSV, mode='w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.DictReader(infile)
        
        fieldnames = ["Data_Center_Name", "City", "Resolved_Address", "Latitude", "Longitude", "Source_URL"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            name = row["Data_Center_Name"]
            city = row["City"]
            
            print(f"--> Translating: {name} ({city})")
            
            lat, lng, address_status = get_coordinates(name, city, gmaps)
            
            if lat and lng:
                print(f"    [+] Resolved: {lat}, {lng}")
                resolved_count += 1
            else:
                print(f"    [-] Unresolved: {address_status}. Requires manual CV intervention.")
                
            writer.writerow({
                "Data_Center_Name": name,
                "City": city,
                "Resolved_Address": address_status,
                "Latitude": lat if lat else "NaN",
                "Longitude": lng if lng else "NaN",
                "Source_URL": row["Source_URL"]
            })
            
            processed_count += 1
            time.sleep(0.5) 

    print(f"\nAPI Geocoding complete. {resolved_count}/{processed_count} spatial targets resolved.")

if __name__ == "__main__":
    if not os.path.exists(INPUT_CSV):
        print(f"Error: Input file missing at {INPUT_CSV}")
    else:
        execute_pipeline()