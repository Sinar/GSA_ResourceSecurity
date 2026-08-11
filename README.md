<p align="center">
  <b>GSA Resource Security</b><br>
  <sub>Satellite-derived resource footprint auditing for Malaysia's data centre sector</sub>
</p>

<p align="center">
  <a href="https://sinar.github.io/GSA_ResourceSecurity/">Live visual library</a> ·
  <a href="#methodology-brief">Methodology</a> ·
  <a href="#references">References</a> ·
  <a href="#known-limitations">Known limitations</a> ·
  <a href="https://sinarproject.org">Sinar Project</a>
</p>

---

GSA Resource Security is an independent, satellite-derived audit of the physical resource footprint of data centre facilities in Malaysia: estimated power demand, energy consumption, water use, carbon emissions, and land-use/deforestation impact, cross-referenced against the regulatory and legislative record. It was built because operators routinely withhold facility-level resource figures under non-disclosure agreements and national-security framing, leaving no independent, verifiable account of what this sector actually costs the country.

Developed by [Sinar Project](https://sinarproject.org) under Subgrant Agreement No. 007 (Data Privacy Brasil / National Endowment for Democracy), as part of the *Resource Security: Data Center Resource Extraction and Autonomy in the Global South* project.

**Status:** research prototype produced for a fixed-term subgrant (March–September 2026). Not maintained as production software; see [Known Limitations](#known-limitations) before relying on any figure.

## Features

- **Satellite building detection**: computer-vision pipeline (OpenCV) that independently measures each facility's physical footprint from satellite imagery, rather than relying on operator-claimed capacity.
- **Confidence-scored, abstaining detector**: colour-space masking, dual-direction Otsu thresholding, and multi-factor contour filtering, with an explicit confidence score and no forced detection where nothing reliable is found.
- **Deduplication**: collapses co-located multi-tenant entries into physical-building records, with explicit handling for genuinely distinct multi-building campuses sharing one imprecise geocode.
- **Resource-extraction estimation**: converts footprint area into estimated power, annual energy, carbon emissions, and water use (optimised and regional water-usage-effectiveness scenarios), keeping operator-disclosed and modelled facilities strictly separate.
- **Independent QA re-check**: a second, separate verification pass (geometric re-check, coordinate-region plausibility check) run across the full dataset, not just the original validation sample; findings are applied as a scripted pipeline step, not a manual edit.
- **Regulatory and legislative corpus analysis**: environmental-review policy mapping across every Malaysian jurisdiction with a measured facility, plus a systematic keyword search and triage of the federal and Johor State Assembly Hansard record (2008–2026).
- **Land-cover change rollout**: facilities clustered into geographic corridors and checked against Hansen Global Forest Change data to quantify deforestation associated with development corridors.
- **Public visual library**: an interactive map, searchable/filterable gallery of every measured facility's satellite capture, and per-facility resource estimates, published as a static site (see [Live visual library](https://sinar.github.io/GSA_ResourceSecurity/)).

## Tech Stack

Python, OpenCV, NumPy · Google Places API / Google Static Maps API (imagery acquisition) · Global Forest Watch / Hansen Global Forest Change (land-cover data) · Leaflet.js (visual library map) · vanilla HTML/CSS/JS (static site, no build step)

## Repository Structure

```
src/      pipeline scripts (see Pipeline Order below)
docs/     public GitHub Pages site: interactive map, visual library, per-facility estimates
logs/     running workflow/methodology log
```

This repository contains the pipeline **code** and a **derived public dataset extract** (`docs/data/manifest.json` and the satellite captures under `docs/images` / `docs/thumbs`, covering the 71 measured buildings and their resource estimates). It does not contain the underlying raw facility coordinate database, the full satellite imagery archive, or the policy/Hansard document corpus, which are maintained separately by the project team; see [Documentation](#documentation) for the companion reports that describe them in full.

## Quick Start

Requires Python 3.10+, `opencv-python`, `numpy`, and a Google Maps Platform API key (Places API + Static Maps API enabled) for imagery acquisition steps.

```bash
git clone https://github.com/Sinar/GSA_ResourceSecurity.git
cd GSA_ResourceSecurity
pip install opencv-python numpy
```

### Pipeline order

```
satellite_cv_pipeline.py / improved_cv.py
        → validate_bboxes.py
        → dedup_buildings.py
        → qa_recheck.py            (review findings manually)
        → apply_qa_corrections.py
        → resource_estimates_v3.py
```

Each script's role is documented in its module comments. `qa_recheck.py` is reporting/discovery only, findings require manual visual confirmation before `apply_qa_corrections.py` applies them.

## Visual Library

The [live site](https://sinar.github.io/GSA_ResourceSecurity/) (source in `docs/`) provides:

- An interactive map of all 71 independently measured facilities, colour-coded by inclusion status.
- A searchable, filterable, sortable gallery of each facility's satellite capture with its detected bounding box.
- A detail view per facility: footprint area, estimated power/energy/carbon/water/waste heat, detection confidence, QA flags, and any independent-verification notes.

To run it locally: `cd docs && python3 -m http.server 8000`, then open `localhost:8000`.

## Methodology (Brief)

1. **Imagery acquisition**: candidate facility addresses/coordinates resolved via the Google Places API, satellite imagery pulled via the Google Static Maps API.
2. **Building detection**: a confidence-scored, abstaining OpenCV pipeline (colour-space masking, dual-direction Otsu thresholding, multi-factor contour filtering) measures each facility's physical footprint; it declines to output a box where nothing reliable is found rather than forcing a detection. 124 candidate facilities were processed.
3. **Validation and deduplication**: detected boxes are checked against source imagery, then co-located multi-tenant entries are collapsed into physical-building records (with an explicit, documented exception for genuinely distinct multi-building campuses sharing one imprecise geocode, e.g. AirTrunk JHB2/JHB3/JHB4). This reduced the candidate set to 71 physical buildings.
4. **Independent QA re-check**: a second, separate verification pass (geometric re-check, coordinate-region plausibility check) run across the full 71-building dataset, not just the original validation sample. Found 11 buildings (15.5%) with an issue not caught by the pipeline's original automated flags, including three facilities whose coordinates resolve outside Malaysia.
5. **Resource estimation**: footprint area converted to estimated power, annual energy, carbon emissions, and water use, with operator-disclosed and modelled facilities kept strictly separate rather than blended into one aggregate (see Valuation Benchmarking below for why).
6. **Regulatory and legislative corpus analysis**: environmental-review policy mapping across every Malaysian jurisdiction with a measured facility, plus a systematic keyword search of the federal and Johor State Assembly Hansard record (2008–2026), and a comparative desk review of Indonesia's environmental-review architecture.
7. **Land-cover change rollout**: facilities grouped by single-linkage geographic clustering (8 km threshold) into development corridors, each checked as a Hansen Global Forest Change area of interest via Global Forest Watch to quantify deforestation associated with the corridor.

Full formulas, coefficients, and caveats are in the companion reports listed under [Documentation](#documentation).

### Valuation benchmarking

The economic valuation paper benchmarks the pipeline's modelled power estimates against **operator-disclosed capacity** for the subset of facilities (7 of 71) where a specific MW figure is publicly disclosed, rather than against a single published industry coefficient treated as ground truth. The published reference coefficient used for the initial comparison is 1.5 kW/m² power density at PUE 1.4, a figure drawn from general industry guidance rather than a facility-specific measurement. Applying that coefficient to the disclosed-capacity facilities' CV-detected footprint area and comparing the implied density against each facility's actual disclosed density produced a spread of more than two orders of magnitude (approximately 0.36 kW/m² for a large colocation facility to approximately 40 kW/m² for a high-density liquid-cooled AI facility fragment). The paper argues this spread is not measurement noise but evidence of vintage capital heterogeneity (Solow's putty-clay framework) across a portfolio built over a decade or more, and situates the finding within the natural resource and industrial ecology aggregation-bias literature and the UN SEEA Central Framework for natural capital accounting (see [References](#references)).

Other figures benchmarked in the paper: Malaysia's pledged data centre investment (RM280 billion since 2021, RM131 billion/47% realised as of May 2026, cited from public investment-tracking reporting); Peninsular Malaysia's estimated annual grid generation, against which the portfolio's modelled ~31,023.5 GWh/yr (~20.0% of grid generation) is compared; and a 360 MW Nvidia-backed campus in Batam, Indonesia, used as a comparative single-facility benchmark against the entire 71-building Malaysian dataset.

## References

### Companion documents

These are the technical methodology, resource-estimation formulas, regulatory/legislative corpus analysis, land-cover change rollout, and full caveats, maintained alongside the underlying data corpus. They are grant deliverables under Subgrant Agreement No. 007 and are not currently published to this repository; available from the project team on request.

- Full Project Methodology - Satellite, Regulatory Corpus, and Land-Cover Change
- Economic Valuation Paper Draft - Vintage Capital Heterogeneity and Hidden Natural Capital Loss
- GSA Master Facility Database - Methodology Note and Data Dictionary
- QA Sample Report - Positional Accuracy and CV Extraction Spot-Check
- Policy Audit Report - Malaysia Data Centre Governance with Indonesia Comparison
- Comparative Regulatory Desk Review - Indonesia vs Malaysia Data Centre Governance
- Resource Security - Public Policy Report
- Policy Brief 1 - Closing the Cumulative-Impact Blind Spot (regulator-facing)
- Policy Brief 2 - Checking a Data Centre's Footprint (journalist-facing)
- Preliminary Results Report - Expanded Background and Assessment

### Policy, legal, and data-source references

- [Malaysia Environmental Quality Act 1974 and Environmental Quality (Prescribed Activities) (Environmental Impact Assessment) Order 2015](https://www.doe.gov.my) — Department of Environment Malaysia; full EIA Order 2015 text via [DOE eSWIS](https://eswis.doe.gov.my/helpDocs/No.4%20-%202015/Perintah-Kualiti-Alam-Sekeliling-Aktiviti-Yang-Ditetapkan-Eia-2015_EN.pdf)
- [Indonesia Government Regulation No. 22 of 2021 (AMDAL / UKL-UPL / SPPL environmental-approval framework)](https://www.menlhk.go.id) — Ministry of Environment and Forestry (KLHK)
- [UN System of Environmental-Economic Accounting (SEEA) Central Framework](https://seea.un.org/content/seea-central-framework) — UN Statistics Division
- [Hansen et al. Global Forest Change dataset](https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html) — University of Maryland / Google Earth Engine
- [Global Forest Watch](https://www.globalforestwatch.org) — World Resources Institute, area-of-interest analysis tool used for the land-cover change rollout
- [Subgrant Agreement No. 007](https://sinarproject.org) and Grant Agreement 2024-1046 (Data Privacy Brasil / National Endowment for Democracy) — governing agreement for this project; contact the project team for the signed document

## Documentation

The technical methodology, resource-estimation formulas, regulatory/legislative corpus analysis, land-cover change rollout, and full caveats are documented in the set of companion reports listed under [References](#references), maintained alongside the underlying data corpus and available from the project team on request.

## Known Limitations

- Geocoding fallback failure modes exist for facilities whose operators don't disclose physical addresses (parent-company registered office; town-level centroid). Three instances found a facility's coordinate resolving to a different country entirely: one to Metro Manila, Philippines, and two (a single corridor) to Marina Bay, Singapore, the latter discovered during a downstream land-cover change analysis rather than by `qa_recheck.py` itself.
- No single power-density coefficient is defensible across the full facility portfolio (observed range spans over 100x between low-density colocation and high-density AI/liquid-cooled facilities); resource estimates therefore report disclosed-capacity facilities separately from modelled facilities rather than blending into one aggregate.
- An independent verification pass across the full 71-building dataset, run across three separate discovery routes (automated re-check, manual visual sample, and the land-cover change rollout), found 11 buildings (15.5%) with an issue not caught by the pipeline's own original automated flags. The dataset should be described as reviewed and substantially reliable, not fully verified.
- This is a fixed-term research output, not a continuously maintained monitoring system; figures reflect the state of publicly available information as of mid-2026 and will drift out of date as facilities are built, disclosed, or decommissioned.

## Support

This is a research subgrant output, not a supported product. For questions about the methodology or data, contact the project team via [Sinar Project](https://sinarproject.org).

## Contributors

- **Adhura H. Farouk**, PhD Candidate in Economics, International Islamic University Malaysia (IIUM). Principal Investigator.
- **Hadirah Husna Huzaidi**, Final-year B.Econs, International Islamic University Malaysia (IIUM). Research Assistant.

## Funding and Acknowledgement

Produced under Subgrant Agreement No. 007 between Data Privacy Brasil and Sinar Project PLT, part of Grant Agreement 2024-1046 between the National Endowment for Democracy and Data Privacy Brasil.

## License

Not yet specified. Coordinate with Sinar Project before reuse or redistribution.
