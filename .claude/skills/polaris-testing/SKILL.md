---
name: polaris-testing
description: Whenever a change touches the Python engine or NASA data adapter.
---

# Test-driven Python Development

## Role
Project-specific POLARIS 2026 agent workflow. Apply its checks to source code and evidence; instructions alone are not a pass.

## Steps
1. Read the target function and its callers.
2. Add deterministic `pytest` tests before or alongside the smallest code modification: nominal, boundary, invalid input, and upstream outage.
3. Mock network only at the JPL boundary; do not mock mission physics under test.
4. Add contract tests for API JSON keys, 422 validation, 503 upstream outage.
5. Run `python -m pytest -q` and `python tools/skills_audit.py` after changes.
6. Record test counts and explicit unverified integration tests; never claim online JPL validation without a live query.

## Exit criteria
- Concrete file/test/evidence changes, or explicitly documented blocked step.
- Risks and unverified claims disclosed.
- No installation script, authentication change or remote action is implied by reading this file.
