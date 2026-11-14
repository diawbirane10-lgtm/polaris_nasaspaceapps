# POLARIS v0.4 — mission replan evidence brief

**Challenge:** 2026 NASA Space Apps / Lunar Landing Site Navigator (10 — CLPS)

**Claim:** POLARIS compares lunar south-pole reference sites and UTC mission schedules with genuine NASA/JPL azimuth/elevation and DEM-derived local horizons, then explains how simplified energy margins respond to scenario changes.

## Demonstration (data-backed, reproducible)

1. In the dashboard, scroll to **04 / Mission Reschedule Lab**.
2. Choose **Connecting Ridge**, baseline `2026-11-14T00:00Z`, **24-hour** analysis, **+48-hour** delay.
3. Click **SIMULATE +48H DELAY**.
4. Observe three scenarios, evaluated on equal-length windows and with the same PV/battery/load assumptions:

| Derived indicator | 14 Nov / Connecting Ridge | 16 Nov / Connecting Ridge | 16 Nov / Shackleton Rim |
|---|---:|---:|---:|
| Potential Earth line-of-sight against *6-km local* skyline (hours out of 24) | 0 | 0 | 18 |
| Potential local Sun exposure (hours out of 24) | 24 | 24 | 24 |
| Longest sampled local Earth obstruction (hours) | 24 | 24 | 6 |
| Illustrative minimum battery SOC, horizontal PV (%) | 46.53 | 44.43 | 46.88 |

This is **not** an operational communications claim. Distant mountains and the radio link budget are unknown, and 6-hour samples can miss events. Here, **18 hours means the Earth's center is above the computed local skyline in three left-endpoint 6-hour time intervals**, not that a lander could reliably contact Earth for 18 uninterrupted hours. Nor are these points certified landing sites.

The test is deterministic, auditable and exportable. No scalar "best site" score is claimed.

## Energy stress test

For the delayed Connecting Ridge scenario, keeping the model's explicitly idealized assumptions:

| Perturbation | Load (W) | Panel area (m²) | Min. SOC (%) |
|---|---:|---:|---:|
| Nominal | 400 | 16.0 | 44.43 |
| Load +20% | 480 | 16.0 | 34.83 |
| Panel area -20% | 400 | 12.8 | 41.95 |
| Both changes | 480 | 12.8 | 32.35 |

The model treats a fixed 1361 W/m² solar constant, efficiency 28%, derating 78%, a hypothetical 20 kWh battery initially at 80%, and a constant load. Solar array geometry is simplified; no thermal, dust, degradation, power electronics, tracking actuator or battery efficiency is included.

## Source provenance and reproducibility

- NASA GSFC LOLA DEMs at 5m/pixel: `https://pgda.gsfc.nasa.gov/products/78`. Source GeoTIFF URLs and SHA256 digests are in `data/nasa/reference_sites_2026-11-14_18.json`.
- NASA/JPL Horizons apparent azimuth/elevation: `https://ssd.jpl.nasa.gov/api/horizons.api`. Sun (10), Earth (399), coordinate observer on Moon (`coord@301`), `QUANTITIES=4`, `APPARENT=AIRLESS`.
- 2m observer height, local ray radius <=6km, 5-degree skyline azimuth resolution, 50m radial stepping. The DEM MOON_ME/DE421 frame versus JPL MEAN_ME has not been calibrated to a known relative angular error.
- The compact source file stores **4 days** of NASA samples (14–18 Nov 2026, 6-hour interval). Outputs are non-flight-qualified and reference data cannot support an arbitrary mission month.

Run: `python -m pytest -q` followed by `python tools/export_counterfactual.py`. The latter produces 8 counterfactual experiments and 24 scenario rows in `data/analysis/`.

## Important verification gates still open

- Independent numerical check against SPICE or an independently generated JPL Horizons export;
- Longer-range terrain beyond the local 6km tiles (this could **reverse** apparent visibility findings);
- Higher temporal cadence (ideally <=1h for the selected dates);
- Accounting for the Earth's apparent angular radius / partial visibility and full radio-link budget;
- More credible power subsystem model, and broader site/date coverage;
- Operational usability test with independent reviewers and deployment on a publicly accessible URL.

**Competition statement:** POLARIS is an independently developed student hackathon prototype and is not affiliated with or endorsed by NASA. We have not verified mission safety or flight readiness.
