# POLARIS v0.8 — Navigation & UX

- **Architecture:** native HTML / CSS / JavaScript, Python FastAPI backend; no React dependency. Six client-side URL-addressable views with explicit navigation, history and back support.
- **Mission:** configure observing point and see the dome.
- **Sky:** see Sun/Earth against sampled local terrain skyline.
- **Scenarios:** choose site, date, delay; run three NASA-backed counterfactuals.
- **Power:** vary electrical load (W), PV area (m²), battery capacity (kWh), tracking vs horizontal; plot NASA-backed SOC timeline and unmet energy.
- **Atlas:** browse Moon Trek aggregated WMTS and link NASA data.
- **Evidence:** mission processing mesh, JPL/SPICE provenance and temporal audit.
- **Accessibility:** text navigation, keyboard focus and browser history, no animation dependency, respect reduced motion, descriptions and warnings.
- **UI assets:** locally vendored Lucide icons (ISC license), see public/icons/LICENSE; animation and controls coded in project. No external UI CDN required.
- **Provenance warning:** Moon Trek tiles are aggregated, solar/battery results simplified, terrain skyline 6 km and Earth visibility is not a radio link.
- **Why native JS:** deadline and existing tested Python-backed code; lower runtime/dependency risk than a wholesale React or Angular rewrite. A TypeScript migration may be considered after submission.
