# NASA resources and jury evidence — POLARIS v0.5

## NASA challenge resource integration — precise status

1. **LROC QuickMap**: linked per selected site as a human visual inspection tool. We do not claim QuickMap pixels are ingested into the numerical horizon model.
2. **Moon Trek**: actual NASA Moon Trek South Pole WMTS tiles are displayed as a cartographic context atlas. Two products are offered: WAC long-term illumination percentage and Earth visibility (aggregate); these images **do not correspond to selected UTC dates**, so never treat them as SPICE/Horizons values.
3. **JPL Horizons**: true observer azimuth/elevation data at sample lunar coordinates, time stamped and included in the reference pack; 4-day offline 6-hour sample.
4. **NASA GSFC LOLA 5m**: directly downloaded DEMs used for 6 km local horizon profiles. Distant terrain is unknown.
5. **NAIF SPICE**: independent geometric crosscheck, with detailed report, source kernels and SHA256 manifest, and locally re-runnable script.

## Critique and mitigation

- **Scientific validity**: yes for astronomy point samples, not certified landing feasibility. Sun/Earth compared at 57 epochs each, 2 locations; Max angular difference approx 1e-6 deg across data; 4-day bundled reference is independently re-checkable via script.
- **Far terrain**: 6 km LOLA horizon is an optimistic visibility bound. Moon Trek aggregate visibility map may flag broader effects but is not a ground truth comparison at chosen time.
- **6-hour time grid**: missed transitions can bias contiguous dark or Earth-window duration; increase to 1h before claiming precision.
- **Energy model**: illustrative flat or tracking PV, approximate battery state, NOT flight power prediction.
- **Navigation**: two sites only in the offline demo; custom user coordinates rely on live Horizons with **geometric** horizon (no local LOLA).
- **UI/UX**: two levels — quick geometry/decision controls and scientific source atlas, explicit loading/error handling and export; minimize jargon in public-facing copy; accessible links and labels.

## Judging criteria grounded in official NASA local pages

2026 criteria: Impact, Creativity, Validity, Relevance, Presentation. UX is not separately weighted globally; it materially affects usability/relevance and clarity/presentation.

Sources: https://www.spaceappschallenge.org/2026/local-events/ajmer/ and https://www.spaceappschallenge.org/2025/local-events/isa-town/ (latter spells out usability under relevance).

## Reproducibility

- NASA data catalog `/api/science-sources`
- Independent validation report `/api/spice-validation` and data/analysis/spice_crosscheck_2026-11-14.json
- Re-run geometry check: `pip install -r requirements-science.txt && python tools/validate_spice.py --download` (downloads kernels).
- Test: `python -m pytest -q`.
- Sources remain property of their providers. Do not claim NASA endorses POLARIS.
