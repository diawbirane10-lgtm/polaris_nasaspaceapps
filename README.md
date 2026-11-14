# POLARIS — Lunar Mission Decision Intelligence

**NASA Space Apps Challenge 2026 · Lunar Landing Site Navigator (10 — CLPS)**

[**Live Mission Control**](https://polaris-spaceapps-2026.vercel.app/) · [Official challenge](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/) · [Submission instructions](https://www.spaceappschallenge.org/resources/project-submission-guide)

> **A launch delay changes the Moon you land on.** POLARIS lets anyone explore how a mission's location and timing affect local solar illumination, potential direct-to-Earth visibility and a simplified energy budget — using documented NASA datasets, rather than invented scientific outputs.

**Status: v0.8, engineering demonstrator (multi-view interface).** Deployed on Vercel and tested locally on 14 November 2026. **Not a flight-qualified tool, a certified landing-site selector, or a radio-link predictor.**

## What judges can try

1. Open the [live app](https://polaris-spaceapps-2026.vercel.app/). Compare the two south-pole reference observer coordinates, **Connecting Ridge** and **Shackleton Rim**. These are sample points, not approved landing sites.
2. Examine real JPL Horizons Sun/Earth azimuth-elevation against a 6 km skyline derived from NASA LOLA elevation data. Inspect the plot and provenance labels.
3. Use **Mission Reschedule Lab** to compare an initial mission, its delayed schedule and an alternative site under the same assumptions.
4. Explore NASA Moon Trek WMTS cartographic layers for *aggregated* polar illumination and Earth visibility. These are **not** date-specific mission predictions.
5. Inspect the [SPICE/Horizons cross-check](https://polaris-spaceapps-2026.vercel.app/api/spice-validation), [source register](https://polaris-spaceapps-2026.vercel.app/api/science-sources), and [temporal-sampling audit](https://polaris-spaceapps-2026.vercel.app/api/science-audit).

**Important example:** A 24-hour Shackleton Rim scenario showed 18 estimated hours of local Earth visibility at 6-hour sampling versus 21 hours when repeated with 1-hour JPL data. Sampling resolution matters; neither is a verified operational RF communication window.

## NASA data and reproducibility

| Resource | How used | Access |
|---|---|---|
| **LROC QuickMap** | Interactive visual reconnaissance of lunar terrain | https://quickmap.lroc.asu.edu/ |
| **Moon Trek** | Genuine WMTS reference tiles for *aggregate* south polar illumination / Earth visibility | https://trek.nasa.gov/moon/ |
| **JPL Horizons** | Sampled, site-specific Sun/Earth apparent azimuth and elevation (`coord@301`, `QUANTITIES=4`, airless) | https://ssd.jpl.nasa.gov/horizons/ |
| **NASA GSFC LOLA** | Two 5 m/pixel DEMs used to derive the **local** 6 km terrain skyline | https://pgda.gsfc.nasa.gov/products/78 |
| **NASA NAIF SPICE** | Independent software method used for cross-checking Horizons angular geometry | https://naif.jpl.nasa.gov/ |

Original ~40 MB DEM tiles are deliberately not committed; original NASA URLs and SHA-256 hashes are documented in `data/nasa/reference_sites_2026-11-14_18.json`. SPICE kernel hashes and verification summaries appear in `data/analysis/spice_crosscheck_2026-11-14.json`. Raw kernels and TIFF files can be re-downloaded using source addresses and checked by the available scripts.

At 57 epochs per body and site (2 sites, 2 bodies), 228 Sun/Earth angular comparisons between SPICE and Horizons were made. Sub-microdegree agreement is **algorithmic consistency**, not independent proof of terrain accuracy. The datasets and model limitations are disclosed in `docs/SCIENTIFIC_AUDIT_AND_UI_v0.6.md`.

## Engineering limitations — do not remove these warnings

- Local terrain skyline extends only **6 km** radially; distant peaks may obscure the Sun or Earth.
- Reference predictions are based on **6-hour** epochs. A separate 1-hour audit demonstrates sensitivity to the sampling cadence.
- No radio link budget, antenna pointing, Earth ground-station schedule, lunar relay, or communications availability assessment.
- The solar and battery model is deliberately simple: it omits thermal conditions, dust, solar disk extent, complex panel pointing, battery degradation and certified safety margins.
- Custom-coordinate live JPL requests currently use a **geometric 0° horizon**, not a site-specific LOLA skyline.
- A local site appears visible only under **the modeled horizon and temporal assumptions**; it is not declared safe or optimal for landing.

## Install & run

```bash
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn api.index:app --reload
# http://127.0.0.1:8000
```

Local offline NASA reference data are bundled. Custom-location / live ephemeris requests require HTTPS access to JPL Horizons. If unavailable, errors are surfaced rather than fabricated readings.

### API routes

```text
GET /api/health
GET /api/nasa-sites
GET /api/nasa-reference/connecting_ridge
GET /api/nasa-reference/shackleton_rim
GET /api/skyline/connecting_ridge
GET /api/replan?site=connecting_ridge&start=2026-11-14T00:00Z&hours=24&delay=48
GET /api/mission?lat=-89.5&lon=220&start=2026-11-14&days=5&step=6
GET /api/spice-validation
GET /api/science-audit
GET /api/science-sources
```

The GitHub Actions workflow in `.github/workflows/ci.yml` runs `pytest` on pushes and pull requests; local test verification on Nov 14 resulted in **58 passing tests**. CI status after publication must be checked separately.

## Repository map

```text
api/             FastAPI and scientific/decision routines
public/          Mission Control web interface (responsive)
data/nasa/       NASA source-derived demo records and provenance
data/analysis/   SPICE checks, sampling sensitivity, scenario evidence
tools/           Reproducibility, validation and source-checking scripts
tests/           Python regression, API, physical-input and data checks
docs/            NASA project summary, science limits, submission checklist
.github/         GitHub Actions continuous integration
.agents/skills/  Six project-specific coding-agent workflows
```

## How to submit to NASA Space Apps

The GitHub repository is **not** itself a NASA submission. The team must complete the **Project** tab on the [official NASA event platform](https://www.spaceappschallenge.org/2026/), including title, brief and detailed descriptions, demo link, final project link, NASA/partner data, other references, tools/AI disclosures and terms. The hackathon submission deadline is **15 November 2026 at 23:59 in the team's registered local-event timezone**. See [`docs/NASA_SUBMISSION_REQUIREMENTS_2026.md`](docs/NASA_SUBMISSION_REQUIREMENTS_2026.md) and [`docs/NASA_PROJECT_SUBMISSION_DRAFT.md`](docs/NASA_PROJECT_SUBMISSION_DRAFT.md).

The NASA organizers do **not** require a particular GitHub repository template or a fork of `nasa/spaceapps` (which is for community discussions). All cited assets must have appropriate permission; comply with applicable NASA Space Apps terms and attribute third-party code. 

## AI disclosure & license

ChatGPT assisted with architecture, code, verification workflows, user interface, tests and documentation. No scientific observation was invented by AI. Reproducing numerical outputs still requires checking NASA files and algorithm assumptions. Six locally authored workflow skills (for Codex/Claude Code) are included under `.agents/skills/`; no bulk third-party skill scripts were imported. See `docs/SKILLS_PROVENANCE.md`.

**Project source license: MIT** — see [`LICENSE`](LICENSE). NASA data, third-party assets and libraries retain their respective source terms; the project MIT license does not override them.

*POLARIS is a NASA Space Apps participant project, not a NASA/JPL-approved or endorsed product.*

## Mission UI v0.8 — 6 views

Use the permanent sidebar or browser URL fragments `#/mission`, `#/sky`, `#/scenarios`, `#/power`, `#/atlas`, `#/evidence`. Native JavaScript retains the same proven FastAPI endpoints. The Power Systems page directly models the degree-appropriate electrical subsystem (PV, electric load, batteries, state of charge). See `docs/INTERFACE_ARCHITECTURE_v0.8.md`.
