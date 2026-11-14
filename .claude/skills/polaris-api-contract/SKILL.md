---
name: polaris-api-contract
description: For changes to FastAPI endpoints, payloads or error handling.
---

# API Contract and Error Review

## Role
Project-specific POLARIS 2026 agent workflow. Apply its checks to source code and evidence; instructions alone are not a pass.

## Steps
1. Compare affected route paths, query parameter ranges, success fields, and status codes before editing.
2. Preserve `/api/health` and `/api/mission` until versioned explicitly.
3. Keep 422 for invalid site/dates and 503 for JPL unavailability; never transform JPL failures into valid-looking zero data.
4. Ensure assumptions, source, model limits and units remain in successful mission payloads.
5. Exercise API routes with TestClient + injected synthetic fixtures.
6. Document any breaking API change and update the web client together.

## Exit criteria
- Concrete file/test/evidence changes, or explicitly documented blocked step.
- Risks and unverified claims disclosed.
- No installation script, authentication change or remote action is implied by reading this file.
