# POLARIS v0.6 — scientific and UI design audit

## What was verified

1. Scientific source: topocentric JPL Horizons apparent azimuth/elevation at two fixed lunar-south-pole observation coordinates. NASA LOLA 5m/pixel terrain tiles were used earlier to compute 72-direction local skyline profiles up to 6 km.
2. Cross-implementation ephemeris check: NAIF SpiceyPy `spkcpo` DE440s versus Horizons DE441 at 57 six-hour epochs for two sites and two bodies (228 comparisons). Residuals of order 10^-6 degrees verify the numerical implementations agree *at the sampled epochs*, not independently validated terrain or flight feasibility.
3. New independent source-resolution sensitivity check: JPL Horizons ephemerides fetched at **1h and 6h sampling** for 14–18 November 2026, with the *same* POLARIS local LOLA skyline. On Shackleton Rim for the 16–17 November 24h window, the local Earth-clear estimate was **18h at 6h sampling** versus **21h at 1h sampling**. Connecting Ridge remained 0h in that window. Recreate using `python tools/validate_sampling.py` (requires Internet).
4. Input validation fixes: NaN and infinity no longer enter energy or mission parameter calculations. Added tests verifying rejection and interval-boundary accounting.
5. Browser UI: full interactive state tested with the actual FastAPI response model injected in a headless Chromium page in a network-isolated test environment. Tested desktop 1500px and mobile 390px: no JavaScript exceptions, horizontal overflow 0px; site change, time scrubbing, and counterfactual 3-scenario rendering worked.

## Raw Horizons 1h response SHA-256 (audit reproducibility)

| Site | Sun 10 | Earth 399 |
|---|---|---|
| Connecting Ridge | `e8530d9a01505cf9cb72eb18ed223e40a4fb98af686a66fe3616902853edadd8` | `513700116240f178ca5f9b41bfe9a999e0b71ea7d108e2e269af2bd103befbee` |
| Shackleton Rim | `b329cf0afa4f9a2c8a7cece53cfd4350592f935a185c5aacd32190cecae6ed49` | `2683b801fe450d6b3c31a827fb6ed8fbfb16e09b471d853159d7db217ec4042d` |

Source query: JPL Horizons (`COMMAND='10'/'399'`, `CENTER='coord@301'`, `SITE_COORD` using DEM elevation+2m mast, `APPARENT='AIRLESS'`, `QUANTITIES='4'`, `STEP_SIZE='1 h'`), 2026-11-14 00:00–2026-11-18 00:00 UTC. Raw hashes help identify which calculations were compared; original full 1h responses are not bundled.

## Important unresolved scientific issues

- The integrated offline demo continues to use 6h observations. The 1h audit is reported separately; it does **not silently replace** the old figures with newer figures in displayed 6h scenario outputs.
- Only 6 km of nearby terrain is modeled, with 5° azimuth bins and 50m radial sampling. Distant terrain remains **unknown**, and the local Earth-clear duration is only a possible line-of-sight upper bound.
- A local threshold crossing needs adaptive event finding (not just a smaller fixed step) for accurate rise/set times.
- The 6km horizon is computed from NASA LOLA data but requires independent validation, e.g. against known illumination products and relief extending farther than the source tile.
- SPICE cross-check shares high-precision ephemeris heritage with Horizons and should not be described as a wholly independent physical validation.
- Radiometric model is deliberately simplified; no thermal, solar panel tilt constraints, charge/discharge losses, mass, dust, or DTE link budget. No recommendation of flight-suitable landing sites.

## Frontend design research and license approach

POLARIS v0.6 uses its **own HTML/CSS/SVG code**. Visual research sources (no third-party source code copied):

- Astro Sci-Fi UI (MIT), https://github.com/jonnysmillie/astro-sci-fi-ui — information hierarchy, disciplined HUD primitives
- NeonBlade UI (MIT), https://github.com/vprix21/neonblade-ui — restrained sci-fi component rhythm
- Velrino UI (MIT), https://github.com/velrino/velrino-ui — accessible control inspiration
- NEXUS UI (PolyForm Noncommercial), https://github.com/forcetrainer/nexus-ui — inspiration only; **no library installation**

The visualization includes a stylized lunar sphere for atmosphere/branding only. **The physically grounded data layers are the NASA LOLA-derived skyline, Horizons trajectories and annotated energy estimates.** NASA Moon Trek is used for real WMTS aggregate map context, not for a date-specific illumination simulation.

## Public deployment checklist

- Tests: `pytest -q` (58 or more expected with local paths)
- API: `/api/health`, `/api/nasa-sites`, `/api/nasa-reference/connecting_ridge`, `/api/skyline/shackleton_rim`, `/api/replan`, `/api/science-audit`, `/api/spice-validation`
- Browser: test 390px mobile and 1500px desktop, observation selection, timeline slider, power parameter change, counterfactual compare, exports, Moon Trek network fallback
- Confirm the production link opens without a Vercel auth gate in incognito mode
- Publish code in a **dedicated public GitHub repository**, with NASA source/provenance and AI-use disclosures; do not replace a separate project repository
- Submit via NASA Space Apps team > Project before the deadline; publishing on Vercel/GitHub does not submit the project to NASA
