import os, cv2, numpy as np

IMG_DIM = 600
PIXEL_TO_M2 = 0.348

def detect_building_box(raw_path):
    """Improved building-footprint detector.
    Strategy: mask out vegetation/water, find both dark-roof and bright-roof
    candidate contours, then score candidates by area, compactness, and
    proximity to image center (facility coordinate is centered by construction
    of the Static Maps request) instead of just taking the single largest
    dark blob anywhere in frame.
    Returns (x, y, w, h, area_m2, confidence_flags) or None if nothing passes.
    """
    img = cv2.imread(raw_path)
    if img is None:
        return None
    h_img, w_img = img.shape[:2]
    cx_img, cy_img = w_img / 2, h_img / 2

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    veg_mask = (h > 35) & (h < 85) & (s > 40)
    water_mask = (h > 90) & (h < 130) & (s > 40)
    exclude_mask = veg_mask | water_mask

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_masked = gray.copy()
    gray_masked[exclude_mask] = 128  # neutralize excluded pixels so they don't threshold as structure

    blurred = cv2.bilateralFilter(gray_masked, 9, 75, 75)

    # candidates from both dark roofs (parking garages, dark membrane roofs)
    # and bright roofs (metal/white membrane roofs) - Otsu picks the right cut
    _, thresh_dark = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, thresh_bright = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = np.ones((5, 5), np.uint8)
    candidates = []
    for thresh in (thresh_dark, thresh_bright):
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area_px = cv2.contourArea(c)
            if area_px < 800:
                continue
            x, y, w, ww = cv2.boundingRect(c)
            bbox_area = w * ww
            if bbox_area == 0:
                continue
            # reject full-frame / border-hugging artifacts
            border_touches = sum([x <= 2, y <= 2, (x + w) >= w_img - 3, (y + ww) >= h_img - 3])
            if border_touches >= 3:
                continue
            if bbox_area > 0.55 * (w_img * h_img):
                continue
            aspect = max(w, ww) / max(1, min(w, ww))
            if aspect > 4.5:
                continue
            compactness = area_px / bbox_area  # how much of the bbox the contour actually fills
            if compactness < 0.35:
                continue
            # reject if candidate region is still mostly vegetation/water despite masking
            region_excl_frac = exclude_mask[y:y+ww, x:x+w].mean() if ww > 0 and w > 0 else 1.0
            if region_excl_frac > 0.5:
                continue
            bx_cx, bx_cy = x + w / 2, y + ww / 2
            dist_to_center = np.hypot(bx_cx - cx_img, bx_cy - cy_img) / np.hypot(cx_img, cy_img)
            score = (bbox_area / (w_img * h_img)) * compactness * (1 - 0.6 * dist_to_center)
            candidates.append((score, x, y, w, ww, region_excl_frac, compactness, dist_to_center, c))

    if not candidates:
        return None

    candidates.sort(key=lambda t: -t[0])
    score, x, y, w, hh, region_excl_frac, compactness, dist_to_center, contour = candidates[0]

    # Polygon footprint: simplify the actual contour (not its bounding box) so the
    # outline traces the building's real aerial outline rather than a rectangle
    # that overstates area on any non-rectangular footprint.
    perimeter = cv2.arcLength(contour, True)
    epsilon = max(1.5, 0.01 * perimeter)  # adaptive simplification, floor at 1.5px
    approx = cv2.approxPolyDP(contour, epsilon, True)
    polygon = [[int(pt[0][0]), int(pt[0][1])] for pt in approx]

    # Area from the actual contour/polygon, not the bounding box - this is the
    # correct footprint area for any building that isn't a perfect axis-aligned
    # rectangle (L-shapes, angled roofs, campus clusters), which the bbox area
    # systematically overstates.
    polygon_area_px = cv2.contourArea(contour)
    area_m2 = round(polygon_area_px * PIXEL_TO_M2, 2)
    bbox_area_m2 = round((w * hh) * PIXEL_TO_M2, 2)

    flags = []
    if dist_to_center > 0.5:
        flags.append("FAR_FROM_CENTER")
    if compactness < 0.5:
        flags.append("LOW_COMPACTNESS")
    return {
        "box": (x, y, x + w, y + hh),
        "polygon": polygon,
        "area_m2": area_m2,
        "bbox_area_m2": bbox_area_m2,
        "confidence": round(float(score), 4),
        "flags": flags,
        "edge_density": None,  # filled in by QC pass, see qc_verify.py
    }

def draw_and_save(raw_path, out_path, result):
    img = cv2.imread(raw_path)
    if result is None:
        cv2.putText(img, "NO_CONFIDENT_DETECTION", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.imwrite(out_path, img)
        return
    color = (0, 255, 0) if not result["flags"] else (0, 165, 255)
    polygon = result.get("polygon")
    if polygon and len(polygon) >= 3:
        pts = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(img, [pts], isClosed=True, color=color, thickness=2)
        label_x, label_y = polygon[0]
    else:
        x0, y0, x1, y1 = result["box"]
        cv2.rectangle(img, (x0, y0), (x1, y1), color, 2)
        label_x, label_y = result["box"][0], result["box"][1]
    cv2.putText(img, f"conf={result['confidence']}", (label_x, max(20, label_y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    cv2.imwrite(out_path, img)
