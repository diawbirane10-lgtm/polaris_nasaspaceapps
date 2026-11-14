# POLARIS 2026 — instructions for coding agents

This repository targets the 2026 NASA Space Apps Challenge. Treat scientific validity as a shipping gate.

**Before edits** read the code and select only the relevant `.agents/skills/<slug>/SKILL.md`.

1. For scientific calculations follow `polaris-scientific-validation` and `polaris-testing`.
2. For new functionality follow `polaris-architecture` and `polaris-api-contract`.
3. Before showing a UI demo follow `polaris-design-qa`.
4. For the submission follow `polaris-pitch`.
5. Explicitly distinguish synthetic test fixtures, real downloaded NASA data, and unverified upstream JPL queries.
6. Never claim a NASA validation, deployment, link, award or passing test unless it was checked after the latest edit.
7. Keep the core operational offline when possible, and never silently replace failed NASA requests with invented numbers.
8. Use `python -m pytest -q` and `python tools/skills_audit.py` after modifications.

Third-party SKILL.md materials are **not executed blindly**. These six project-specific workflows are original adaptations; see `docs/SKILLS_PROVENANCE.md` for reviewed sources, license cautions, and exclusions.
