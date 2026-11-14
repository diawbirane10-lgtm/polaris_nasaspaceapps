---
name: polaris-architecture
description: Before implementing or refactoring scientific web features.
---

# Architectural Design & Scope Control

## Role
Project-specific POLARIS 2026 agent workflow. Apply its checks to source code and evidence; instructions alone are not a pass.

## Steps
1. Map current modules: `api/core.py`, `api/horizon.py`, `api/index.py`, `tools/prepare_lola_horizon.py`, and `public/index.html`.
2. For any feature, write: purpose, user value, exact input/output, source provenance, explicit assumptions, failure modes, and acceptance criteria.
3. Mark every integration KNOWN (checked in source), ASSUMED (not yet verified), or UNKNOWN (must not be used in a claim).
4. Choose smallest implementation that meets the challenge; do not introduce cloud services, agents, databases, or Arduino without measured need.
5. Separate mission science from UI rendering, and separate NASA facts from synthetic fixtures.
6. Record new dependencies and performance tradeoffs in the README.

## Exit criteria
- Concrete file/test/evidence changes, or explicitly documented blocked step.
- Risks and unverified claims disclosed.
- No installation script, authentication change or remote action is implied by reading this file.
