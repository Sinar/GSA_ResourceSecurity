import os
import csv
import time
from playwright.sync_api import sync_playwright, TimeoutError

# 1. Enforce GSA Path Architecture
ROOT_DIR = "/Users/dhuralumin/Desktop/Development/"
GSA_DIR = os.path.join(ROOT_DIR, "04 side_projects", "GSA")
PROCESSED_DIR = os.path.join(GSA_DIR, "data", "processed")

os.makedirs(PROCESSED_DIR, exist_ok=True)
OUTPUT_CSV = os.path.join(PROCESSED_DIR, "gsa_datacenter_coordinates.csv")
BASE_URL = "https://www.datacentermap.com"

def execute_pipeline():
    print(f"Initializing Fault-Tolerant Headless Extraction Engine.\nTarget: {OUTPUT_CSV}")
    
    with open(OUTPUT_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Data_Center_Name", "Country", "City", "Address", "Source_URL"])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        country_url = f"{BASE_URL}/malaysia/"
        print(f"\nScanning Country Level: {country_url}")
        
        page.goto(country_url, wait_until="domcontentloaded")
        
        city_elements = page.query_selector_all("a[href^='/malaysia/']")
        city_links = set()
        for el in city_elements:
            href = el.get_attribute("href")
            if href and href != "/malaysia/":
                city_links.add(BASE_URL + href)
                
        print(f"Discovered {len(city_links)} potential city regions.")

        total_extracted = 0

        for city_url in city_links:
            print(f"--> Scanning City: {city_url}")
            try:
                page.goto(city_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(1)
            except TimeoutError:
                print(f"    [!] City page timeout, skipping: {city_url}")
                continue
            
            dc_elements = page.query_selector_all("a[href^='/malaysia/']")
            dc_links = set()
            for el in dc_elements:
                href = el.get_attribute("href")
                if href and href not in city_url and href != "/malaysia/":
                    dc_links.add(BASE_URL + href)

            for dc_url in dc_links:
                # Filter out generic 'quote' pages that aren't data centers
                if "quote" in dc_url.lower():
                    continue

                print(f"    [+] Extracting Profile: {dc_url}")
                
                try:
                    # Downgraded wait state and increased timeout buffer
                    page.goto(dc_url, wait_until="domcontentloaded", timeout=45000)
                    time.sleep(0.5)
                    
                    name_el = page.query_selector("h1")
                    name = name_el.inner_text().strip() if name_el else "Unknown DC"
                    
                    address = "Address not found"
                    address_el = page.query_selector("address") 
                    if not address_el:
                        address_el = page.query_selector("p.address, div.address")
                    
                    if address_el:
                        address = address_el.inner_text().replace('\n', ' ').strip()

                    with open(OUTPUT_CSV, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        city_name = city_url.split('/')[-2].title().replace('-', ' ')
                        writer.writerow([name, "Malaysia", city_name, address, dc_url])
                    
                    total_extracted += 1
                    print(f"        -> Success: Logged {name}")
                    
                except TimeoutError:
                    print(f"        [!] Timeout Error on Profile: {dc_url}. Skipping.")
                except Exception as e:
                    print(f"        [!] Unexpected Error on Profile: {dc_url}. {e}")

        print(f"\nExtraction complete. {total_extracted} records secured.")
        browser.close()

if __name__ == "__main__":
    execute_pipeline()