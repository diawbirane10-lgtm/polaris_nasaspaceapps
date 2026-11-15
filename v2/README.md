# POLARIS / MISSION CONTROL V2 — isolated Japanese-inspired UI experiment

This is a **separate Next.js 15 / React 19 UI** in `v2/`, developed on branch `experiment/mission-control-v2`. The production Python FastAPI demo and main branch are unchanged.

## Concept / source references

- Japan Digital Agency Design System β — https://design.digital.go.jp/dads/ — component anatomy, form affordances, typography, contrast, semantic colors and interaction consistency.
- Japan Digital Agency Dashboard Practical Guidebook — https://www.digital.go.jp/en/resources/user-centered-approach-guidebook/practices — clearly grouped indicators and honest visualization.
- Japan Web Design Gallery (grid category) — https://japan.2-wg.com/category/special/grids-system/ — structured grids, whitespace, Japanese restraint.
- Japan Web Design Gallery — https://japan.2-wg.com/ — visual hierarchy and editorial precision.

**No logos or illustrations are copied from reference websites.** The visual system is original and intentionally uses English for NASA audience.

## Implementation

- 8 navigation views share one premium industrial console shell.
- Connecting Ridge / Shackleton Rim reference data is fetched **read-only** through a Next.js server route from the original POLARIS NASA-backed reference endpoint. No invented numerical readings.
- Scrubber selects among real six-hour sampled timestamps, updates readouts, visibility and energy timeline.
- The topographic drawing is a **schematic illustration**, not a georegistered DEM terrain reconstruction. Real site positions are displayed from the reference dataset.
- AI Copilot passes requests to the original POLARIS Python engineering backend via a server-side proxy; provider keys are not present in this codebase.
- Decision Review and Evidence panels in V2 are **exploratory visual prototypes** and deep-link to the full original app for complete workflows. The tested production app remains the canonical submission.
- Uses no React Three Fiber or WebGL initially: evaluate data integrity, layout and user experience first. A real calibrated LOLA mesh should be added after validating coordinate systems, terrain tile data, scale, and occlusion.

## Test manually

```bash
cd v2
npm install
npm run build
npm run dev
```

Compare 1440 desktop, 1024 tablet and 390 mobile. Verify keyboard nav, light/dark contrast, site switching, timeline interaction, remote service outage states, and live Copilot responses. Do not promote to production without functional parity and an accessibility audit.