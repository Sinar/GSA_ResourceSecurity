import os, csv, cv2, numpy as np, json

GSA_DIR = "/sessions/relaxed-sharp-turing/mnt/GSA"
CAPTURE_DIR = os.path.join(GSA_DIR, "data", "satellite_captures")
CARBON_CSV = os.path.join(GSA_DIR, "data", "processed", "gsa_carbon_estimates.csv")
IMG_DIM = 600

def find_green_box(bbox_path):
    img = cv2.imread(bbox_path)
    if img is None:
        return None
    # green box drawn as pure (0,255,0) BGR -> look for near-pure green pixels
    b, g, r = cv2.split(img)
    mask = (g > 200) & (b < 80) & (r < 80)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    return x0, y0, x1, y1

def texture_score(raw_path, box):
    # Edge density & color variance inside box vs whole image - buildings have
    # higher structural edge density / lower uniform-color fraction than bare land,
    # vegetation canopy, roads or water.
    img = cv2.imread(raw_path)
    if img is None or box is None:
        return None
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.shape[1]-1, x1), min(img.shape[0]-1, y1)
    if x1 <= x0 or y1 <= y0:
        return None
    crop = img[y0:y1, x0:x1]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = edges.mean() / 255.0
    # color variance (std) - low variance = uniform (water/roof/bare land), very high = noisy vegetation
    std = gray.std()
    # dominant hue check for vegetation (green) / water (blue) via HSV
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    green_frac = float(np.mean((h > 35) & (h < 85) & (s > 40)))
    blue_frac = float(np.mean((h > 90) & (h < 130) & (s > 40)))
    return {
        "edge_density": round(float(edge_density), 4),
        "std": round(float(std), 2),
        "green_frac": round(green_frac, 3),
        "blue_frac": round(blue_frac, 3),
    }

def main():
    rows = []
    with open(CARBON_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    results = []
    for row in rows:
        name = row["Data_Center_Name"]
        safe_name = "".join([c if c.isalnum() else "_" for c in name])
        raw_path = os.path.join(CAPTURE_DIR, f"{safe_name}_raw.png")
        bbox_path = os.path.join(CAPTURE_DIR, f"{safe_name}_bbox.png")
        area = float(row["Extracted_Area_m2"])

        box = find_green_box(bbox_path)
        flags = []

        if box is None:
            flags.append("NO_BOX_FOUND")
            w = h = None
        else:
            x0, y0, x1, y1 = box
            w, h = x1 - x0, y1 - y0
            # touches / near image border on 2+ sides -> thresholding grabbed whole frame
            border_touches = sum([
                x0 <= 2, y0 <= 2, x1 >= IMG_DIM - 3, y1 >= IMG_DIM - 3
            ])
            if border_touches >= 3:
                flags.append("FULL_FRAME_BOX")
            elif border_touches == 2:
                flags.append("BORDER_HUGGING_BOX")
            if w * h < 400:  # tiny box, unlikely a full building at zoom 18
                flags.append("TINY_BOX")
            aspect = max(w, h) / max(1, min(w, h))
            if aspect > 6:
                flags.append("EXTREME_ASPECT_RATIO")

        tex = texture_score(raw_path, box) if box else None
        if tex:
            if tex["green_frac"] > 0.55:
                flags.append("LIKELY_VEGETATION")
            if tex["blue_frac"] > 0.55:
                flags.append("LIKELY_WATER")
            if tex["edge_density"] < 0.03:
                flags.append("LOW_STRUCTURE_EDGE_DENSITY")

        results.append({
            "name": name,
            "city": row["City"],
            "area_m2": area,
            "box": box,
            "flags": flags,
            "texture": tex,
        })

    # duplicate-area clustering (independent facilities sharing identical extracted area
    # strongly suggests a degenerate/default box shape rather than a real per-site measurement)
    from collections import defaultdict
    by_area = defaultdict(list)
    for r in results:
        by_area[r["area_m2"]].append(r["name"])
    for r in results:
        if len(by_area[r["area_m2"]]) >= 4:
            r["flags"].append(f"DUPLICATE_AREA_CLUSTER(n={len(by_area[r['area_m2']])})")

    flagged = [r for r in results if r["flags"]]
    clean = [r for r in results if not r["flags"]]

    print(f"Total facilities: {len(results)}")
    print(f"Flagged: {len(flagged)}")
    print(f"Clean (passed automated check): {len(clean)}")
    print()
    from collections import Counter
    reason_counts = Counter(f for r in flagged for f in r["flags"])
    for reason, count in reason_counts.most_common():
        print(f"  {reason}: {count}")

    with open("/sessions/relaxed-sharp-turing/mnt/outputs/bbox_validation.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
