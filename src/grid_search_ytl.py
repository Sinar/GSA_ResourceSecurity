import os, requests, math, sys, json
sys.path.insert(0, "/sessions/relaxed-sharp-turing/mnt/outputs")
from improved_cv import detect_building_box, draw_and_save

API_KEY = "AIzaSyDqgaMR2t5LNXfajyb33DXbFRYzfR1PTrQ"
OUT_DIR = "/sessions/relaxed-sharp-turing/mnt/outputs/ytl_grid"
os.makedirs(OUT_DIR, exist_ok=True)

# Midpoint of the two YTL fallback coordinates we have
lat0 = (1.6195328 + 1.6196508) / 2
lon0 = (103.521885 + 103.5197902) / 2

STEP_M = 300
N = 5  # 5x5 grid -> ~1.5km x 1.5km
dlat = STEP_M / 111320
dlon = STEP_M / (111320 * math.cos(math.radians(lat0)))

def fetch(lat, lng, path):
    url = (f"https://maps.googleapis.com/maps/api/staticmap?"
           f"center={lat},{lng}&zoom=18&size=600x600&maptype=satellite&key={API_KEY}")
    r = requests.get(url, timeout=15)
    if r.status_code == 200 and len(r.content) > 2000:
        open(path, "wb").write(r.content)
        return True
    return False

results = []
for i in range(-(N//2), N//2+1):
    for j in range(-(N//2), N//2+1):
        lat = lat0 + i*dlat
        lon = lon0 + j*dlon
        tag = f"r{i+2}c{j+2}"
        raw_path = os.path.join(OUT_DIR, f"{tag}_raw.png")
        ok = fetch(lat, lon, raw_path)
        if not ok:
            continue
        res = detect_building_box(raw_path)
        bbox_path = os.path.join(OUT_DIR, f"{tag}_bbox.png")
        draw_and_save(raw_path, bbox_path, res)
        if res:
            results.append({"tag": tag, "lat": lat, "lon": lon, **res})

results.sort(key=lambda r: -r["area_m2"])
json.dump(results, open(os.path.join(OUT_DIR, "results.json"), "w"), indent=2)
print(f"Tiles fetched: {N*N}, candidates found: {len(results)}")
for r in results[:10]:
    print(r["tag"], r["lat"], r["lon"], "area_m2=", r["area_m2"], "conf=", r["confidence"], "flags=", r["flags"])
