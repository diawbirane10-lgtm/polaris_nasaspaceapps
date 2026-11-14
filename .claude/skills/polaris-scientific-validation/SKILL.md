---
name: polaris-scientific-validation
description: Before presenting lunar results as scientifically meaningful.
---

# Scientific Validation Gate

## Role
Project-specific POLARIS 2026 agent workflow. Apply its checks to source code and evidence; instructions alone are not a pass.

## Steps
1. Record input dataset identifier, projection, coordinate frame, data license, acquisition URL, and timestamp.
2. Cross-check JPL Horizons parsing and solar/Earth azimuth-elevation conventions against independently recorded reference rows.
3. Validate DEM projection, local north/east directions, height datum, nodata and ray coverage; abort on incomplete coverage.
4. Test horizon geometry on hand-computable synthetic terrains; do not call synthetic values observed NASA measurements.
5. Check energy balance conservation in kWh, battery clipping, power and SOC, time weighting, and sampling sensitivity.
6. Distinguish geometric Earth visibility from an operational radio link.
7. Report PASS / FAIL / NOT VERIFIED separately with source and observed evidence; never infer that a passing unit test validates mission physics.

## Exit criteria
- Concrete file/test/evidence changes, or explicitly documented blocked step.
- Risks and unverified claims disclosed.
- No installation script, authentication change or remote action is implied by reading this file.
