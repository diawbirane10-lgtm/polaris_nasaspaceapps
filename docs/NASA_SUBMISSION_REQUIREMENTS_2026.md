# NASA Space Apps 2026 — Official submission compliance / POLARIS

Verified against the current 2026 NASA Space Apps event page, official NASA Space Apps Connect conversations and legal terms on **14 November 2026**.

## Is there a required GitHub repository template?

**No required template was identified.** NASA Space Apps Connect organizers/Navigators explicitly confirm that you do not need to fork the `nasa/spaceapps` discussions repository, and GitHub hosting itself is optional. A public repository with a clear README, reproducible code and a suitable license is strongly useful for review.

Authoritative references:
- Event submission instructions: https://www.spaceappschallenge.org/2026/
- Submission guide: https://www.spaceappschallenge.org/resources/project-submission-guide
- Public source/license rules: https://www.spaceappschallenge.org/legal/
- Official Space Apps Connect: https://github.com/nasa/spaceapps/discussions/1979
- Alternative hosting clarification: https://github.com/nasa/spaceapps/discussions/1991
- Required submission fields clarified by NASA organizers: https://github.com/nasa/spaceapps/discussions/1858
- NASA dataset eligibility and credits clarification: https://github.com/nasa/spaceapps/discussions/1827

## Mandatory submission path (not GitHub)

Open the team's **Project** tab on the NASA Space Apps site. Include:

- [ ] Project title and high-level summary
- [ ] Link to the **publicly accessible** final project (POLARIS web app or public repo)
- [ ] Link to a **publicly accessible demonstration** (generally either a <30-second video or up to 7 slides; check the current guide's exact constraints)
- [ ] Detailed project description: problem, solution, scientific method, what is original, limitations
- [ ] All NASA/space agency data used and **how** it is used (QuickMap, Moon Trek, Horizons, LOLA, SPICE)
- [ ] Additional data, open-source code/frameworks, assets and citations
- [ ] AI tools used and their role (including ChatGPT and any coding assistants)
- [ ] Terms & conditions; confirm final submitted state

**Deadline:** Sunday **15 November 2026, 11:59 PM**, timezone assigned to the registered team's local event owner. Check the local event requirements if there are separate local judging rules.

## POLARIS repo presentation checklist

- [x] Public GitHub repo owned by project participant
- [x] Source license file (`LICENSE`, MIT)
- [x] Self-contained code, tests, NASA data records and scientific qualifications
- [x] Reproducible `python -m pytest -q` command
- [x] Documented links to NASA-provided challenge resources
- [x] Numerical validation and limits clearly distinguished
- [ ] Public demo video or 7-slide deck URL accessible without permissions
- [ ] NASA Project tab completed by the registered team

## Important truthfulness checks

- The source readme claims v0.6; do not show old v0.5 screenshots as current.
- NASA Moon Trek reference tiles are aggregated maps, **not** time-specific mission predictions.
- A local Earth-above-horizon interval is not a functioning RF communication window.
- SPICE-vs-Horizons numerical agreement is not a scientific certification.
- The 6 km skyline excludes distant terrain.

Sources: NASA Space Apps 2026 and the official NASA Space Apps Connect discussion answers linked above. This checklist is a team's best-effort summary, not an official NASA-issued template.
