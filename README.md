# GSA Pipeline — Resource Security: Data Center Resource Extraction and Autonomy in the Global South

Pipeline code for satellite computer-vision facility detection, deduplication, and
resource-extraction (power/energy/carbon/water/heat) estimation, developed under
Subgrant Agreement No. 007 (Data Privacy Brasil / NED), Sinar Project PLT.

This repository contains code only. The underlying satellite imagery, facility
coordinate database, and policy/Hansard document corpus are maintained separately
and are not included here.

## Contents

- `src/satellite_cv_pipeline.py` — original satellite capture + CV pipeline entry point.
- `src/improved_cv.py` — redesigned building-detection logic: vegetation/water HSV
  masking, dual Otsu thresholding, contour filtering (area/compactness/aspect/border-touch),
  confidence scoring. Replaces the original largest-dark-contour detector, which was found
  to frequently capture non-building features.
- `src/validate_bboxes.py` — automated bounding-box validation (border-touch, full-frame,
  tiny-box, aspect-ratio, vegetation/water fraction, duplicate-area clustering flags).
- `src/dedup_buildings.py` — deduplicates co-located multi-tenant buildings by coordinate,
  reconciles against disclosed-capacity campuses.
- `src/resource_estimates_v3.py` — converts validated building footprints into power,
  energy, carbon, water, and waste-heat estimates; keeps disclosed-capacity facilities
  separate from modeled-coefficient facilities.
- `src/grid_search_ytl.py` — visual-signature grid search used to re-locate an
  undisclosed facility from a known campus's visual footprint.
- `src/extraction_filter.py`, `src/finalize_targets.py`, `src/isolate_unresolved.py`,
  `src/digital_infra.py` — supporting facility-list processing utilities.
- `src/qa_recheck.py` — independent verification re-check run against the full
  deduplicated building set: geometric re-check for unflagged border-hugging/full-frame
  boxes, and a coordinate-region plausibility check comparing each building's coordinate
  against its recorded City field. Reporting/discovery only; findings require manual
  visual confirmation before being applied.
- `src/apply_qa_corrections.py` — applies confirmed findings from `qa_recheck.py` (after
  manual review) to the deduplicated building dataset, so QA corrections are a scripted,
  reproducible pipeline step rather than a manual data edit. Run after `dedup_buildings.py`
  and before `resource_estimates_v3.py`.
- `logs/gsa_workflow.md` — running workflow/methodology log.

## Pipeline order

`satellite_cv_pipeline.py` / `improved_cv.py` → `validate_bboxes.py` → `dedup_buildings.py`
→ `qa_recheck.py` (review findings manually) → `apply_qa_corrections.py` →
`resource_estimates_v3.py`.

## Known limitations (documented for transparency)

- Geocoding fallback failure modes exist for facilities whose operators don't disclose
  physical addresses (parent-company registered office; town-level centroid). Three
  instances found a facility's coordinate resolving to a different country entirely:
  one to Metro Manila, Philippines, and two (a single corridor) to Marina Bay,
  Singapore, the latter discovered during a downstream land-cover change analysis
  rather than by `qa_recheck.py` itself; see the project's Verification and QA
  Report for both discovery routes.
- No single power-density coefficient is defensible across the full facility portfolio
  (observed range spans >100x between low-density colocation and high-density AI/liquid-
  cooled facilities); resource estimates therefore report disclosed-capacity facilities
  separately from modeled facilities rather than blending into one aggregate.
- An independent verification pass across the full 71-building dataset, run across
  three separate discovery routes (automated re-check, manual visual sample, and the
  land-cover change rollout), found 11 buildings (15.5%) with an issue not caught by
  the pipeline's own original automated flags (unflagged border-hugging boxes,
  City-field/coordinate mismatches, three out-of-country coordinates). The dataset
  should be described as reviewed and substantially reliable, not fully verified.
