# Mission Decision Review — POLARIS 1.4

## Purpose and end users

The engineering user configures a lunar south-pole study, validates quantitative scenario conditions, and exports a reproducible decision record. The short **Mission Decision Brief** supports technical reviews and stakeholder meetings. The **Engineering Simulation Dossier** holds the numerical constraints, time-series curves when requested, computed events, and NASA data provenance for an engineering team.

### User journey

1. **Mission / Scenarios / Power** — enter site, UTC mission start, delay, panel area, constant electric demand, battery capacity and panel mode. These settings are not screenshots or fixtures; the FastAPI engine recalculates on every call.
2. **AI Copilot** — ask free-form questions. The current Python flow recognizer parses the supported numerical changes (site, delay, load, PV area, battery capacity), executes the model, and shows source-linked metrics; a Groq/Hugging Face language model provides *additional* commentary only if a server-side key is configured. It is not connected by default. The chatbot-flow-design skill from rampstackco/claude-skills guided intent boundaries, grounding and fallback responses.
3. **Decision Review** — choose study focus (*integrated*, *electrical*, *geometry*), acceptance thresholds, a subset of up to three scenarios, and whether to include trace graphs and event detection.
4. **Evaluate** — inspect current computed metrics and *model-scope* PASS/FAIL statuses. Any input change invalidates the previous on-screen decision; the backend independently recalculates at export.
5. **Document** — download a Brief or Dossier in PDF, or the generated XeLaTeX source and the same JSON evidence.

## Dynamic rules and observables

| Focus | Actual constraint rules | Generated curves |
|---|---|---|
| Electrical | Battery SOC reserve; unserved energy | Battery SOC and PV output |
| Geometry | Minimum Earth above local skyline; longest local Earth gap | Local Sun/Earth elevation margins |
| Integrated | All four | Battery SOC and local Earth elevation margin |

The constraint thresholds come from the engineering user, not an invented system ranking. Each PASS or FAIL is accompanied by the observed numerical value, operator, required threshold, unit, and scenario identity.

**Events are detected from the actual timestamped series**, e.g. a battery reserve crossing or Earth crossing the modeled local horizon. If no tracked crossing occurs, no event is fabricated. The current 6-hour observational sampling cannot resolve the exact transition time; the report labels the sample epoch rather than pretending sub-hour precision.

## Report production and typefaces

- `POST /api/mission-review` — JSON decision payload and evidence.
- `POST /api/mission-decision/brief.pdf` — one-/two-page decision-oriented PDF.
- `POST /api/mission-decision/dossier.pdf` — variable-length technical report, with focus-matched curves and events.
- `POST /api/mission-decision/dossier.tex` — mission-specific XeLaTeX source with Libertinus Serif, monochrome body, colored POLARIS emblem and vector data plots.
- `POST /api/mission-decision/dossier.json` — exact supporting observations and check results.

The serverless PDF endpoint uses a portable ReportLab serif fallback when XeLaTeX is not installed, while the exported LaTeX source compiles with Libertinus Serif on a TeX-enabled machine. This is a **typographic portability difference only**; numeric inputs originate from the same calculation pipeline.

## Scientific limits

The stored LOLA model samples only the local 6 km surroundings. JPL geometry is based on six-hour samples in the main dataset. Direct-to-Earth radio communications, ground-station scheduling, thermal balance, battery aging, complete spacecraft load profiles, lander approach hazard clearance, and deep shadowing beyond 6 km are not modeled. Model PASS is deliberately labelled **MEETS MODELED LIMITS**, never universal mission safety.

## UI provenance

The design applies the user's Sport Programme UI design contract — restrained grid alignment, square edges, 1 px rules and data hierarchy — adapted to POLARIS dark mission-control context. The count-up effect is triggered only by real numerical results and is disabled under reduced-motion preferences. Navigation remains URL-addressable on eight views. Original markup and styling; locally bundled icons. The skill `nextlevelbuilder/ui-ux-pro-max-skill` informed keyboard, touch, responsive, chart and motion guidelines.

## Reproducibility

```bash
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn api.index:app --reload
```

Every decision carries its review ID (hash of current parameters, selection and dataset digest), dataset SHA-256, study focus, input requirements and scenario values. The browser cannot submit fabricated physics results as part of a report payload.
