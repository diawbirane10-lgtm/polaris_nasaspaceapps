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


## Mission Decision Review — v1.4

Select **Decision Review** (8th page) after running a mission. Choose an electrical, geometric, or integrated study, engineer-defined acceptance limits, selected scenarios, and whether to include actual event detection and time-series data. The application recomputes the model and shows observable constraints and reasoned scenario comparisons before enabling export.

Two output variants are now generated from the current inputs: **Mission Decision Brief** (stakeholder decision summary) and **Engineering Simulation Dossier** (focus-adaptive charts, actual events, model methods and NASA dataset fingerprints). Both have PDF and English XeLaTeX sources / JSON evidence. LaTeX compiles with Libertinus Serif, while Vercel uses a portable serif PDF renderer without a TeX installation. See [Mission Decision Review documentation](docs/MISSION_DECISION_REVIEW_v1.4.md).

The flight director Copilot is a bounded **question-to-calculation interface**, not a hardcoded FAQ. It re-evaluates the live mission parameters using the Python engine; an optional server-side LLM can explain results but cannot change the numbers. An external LLM is not active unless a key is installed in Vercel environment variables; the deterministic calculation and constraint checker work without a key.

### Mission-review routes

```text
POST /api/mission-review
POST /api/mission-decision/brief.pdf
POST /api/mission-decision/dossier.pdf
POST /api/mission-decision/dossier.tex
POST /api/mission-decision/dossier.json
```

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

## Mission AI Copilot & generated simulation report (v1.2)

On the **Copilot** screen, type an actual engineering question, including numeric edits like
`increase electrical load by 40%`, `reduce PV area by 20%`, or
`reduce load by 15% and increase PV area by 30%`. POLARIS interprets those edits
and reruns the NASA-backed mission calculation; it shows the three observation
scenarios and exactly which user-defined requirements pass or fail.

- **Trust model:** numerical metrics are computed exclusively by Python;
  an optional server-configured Groq/Hugging Face language model may add commentary
  but cannot change computed values. In the default mode no remote LLM is running,
  and the UI labels it "Engineering analysis" rather than pretending an LLM is active.
- **Outputs:** the current mission settings generate on-demand
  `POST /api/mission-report.pdf` (serverless PDF),
  `POST /api/mission-report.tex` (reproducible XeLaTeX/Libertinus Serif source),
  `POST /api/mission-report.json` (full numerical evidence).
- **Report:** English; monochrome text, colored logo and charts;
  three scenarios, electrical-system settings, constraint table, dataset digest,
  methods and data provenance. The source XeLaTeX file uses Libertinus Serif;
  the serverless PDF uses an available serif fallback when LaTeX isn't installed.
- **Reproducibility:** the code includes `tests/test_v12_live_copilot_report.py`.

See [`docs/POLARIS_COPILOT_REPORT_V1.2.md`](docs/POLARIS_COPILOT_REPORT_V1.2.md)
for the implemented flow, original design inspiration and installation settings.

## How to submit to NASA Space Apps

The GitHub repository is **not** itself a NASA submission. The team must complete the **Project** tab on the [official NASA event platform](https://www.spaceappschallenge.org/2026/), including title, brief and detailed descriptions, demo link, final project link, NASA/partner data, other references, tools/AI disclosures and terms. The hackathon submission deadline is **15 November 2026 at 23:59 in the team's registered local-event timezone**. See [`docs/NASA_SUBMISSION_REQUIREMENTS_2026.md`](docs/NASA_SUBMISSION_REQUIREMENTS_2026.md) and [`docs/NASA_PROJECT_SUBMISSION_DRAFT.md`](docs/NASA_PROJECT_SUBMISSION_DRAFT.md).

The NASA organizers do **not** require a particular GitHub repository template or a fork of `nasa/spaceapps` (which is for community discussions). All cited assets must have appropriate permission; comply with applicable NASA Space Apps terms and attribute third-party code. 

## AI disclosure & license

ChatGPT assisted with architecture, code, verification workflows, user interface, tests and documentation. No scientific observation was invented by AI. Reproducing numerical outputs still requires checking NASA files and algorithm assumptions. Six locally authored workflow skills (for Codex/Claude Code) are included under `.agents/skills/`; no bulk third-party skill scripts were imported. See `docs/SKILLS_PROVENANCE.md`.

**Project source license: MIT** — see [`LICENSE`](LICENSE). NASA data, third-party assets and libraries retain their respective source terms; the project MIT license does not override them.

*POLARIS is a NASA Space Apps participant project, not a NASA/JPL-approved or endorsed product.*

## Mission UI v0.8 — 6 views

Use the permanent sidebar or browser URL fragments `#/mission`, `#/sky`, `#/scenarios`, `#/power`, `#/atlas`, `#/evidence`. Native JavaScript retains the same proven FastAPI endpoints. The Power Systems page directly models the degree-appropriate electrical subsystem (PV, electric load, batteries, state of charge). See `docs/INTERFACE_ARCHITECTURE_v0.8.md`.


*Release update (14 November 2026): seven-page mission UI with dynamic copilot and technical report export.*

## v1.5 security branch: private workspace groundwork (not activated on production)

The public NASA Space Apps demonstration remains accessible without a login. The dedicated **private** API endpoints under `/api/private/` enforce validated asymmetric Supabase JWT, MFA (`aal2`), a server-provisioned active operator profile and an export audit event. The private report author is taken from the protected profile, **never** from editable browser input. A missing auth provider configuration fails closed with HTTP 503.

This code is an **integration candidate**: a new dedicated POLARIS Supabase project, MFA sign-in UX, applied/tested RLS policies, session-lifecycle controls and audit/storage verification are still necessary before private mission data is accepted. Do not point POLARIS to Supabase databases belonging to unrelated applications. See [secure workspace design](docs/SECURE_WORKSPACE_ARCHITECTURE_v1.5.md) and the [unapplied SQL reference](supabase/sql/secure_workspace_schema.sql). Validate security using at least two distinct real accounts, not only mocked tests.


## Secure workspace v1.6 (14 November 2026)

- [Private Mission Workspace](https://polaris-spaceapps-2026.vercel.app/workspace) (Supabase Auth + MFA + Postgres RLS + realtime mission sync).
- [Deployment, security boundaries, and activation checklist](docs/SUPABASE_LIVE_WORKSPACE_v1.6.md).
- The publicly accessible demo remains separate from private mission records. Approved operator profiles are provisioned by an administrator; private exports remain fail-closed until the server-side audit key is configured.
