---
name: polaris-design-qa
description: When changing the mission-control page or before a demo.
---

# Interface Accessibility and Credibility QA

## Role
Project-specific POLARIS 2026 agent workflow. Apply its checks to source code and evidence; instructions alone are not a pass.

## Steps
1. Verify keyboard navigation and visible focus for all links, presets, buttons, and form fields.
2. Verify each numeric field has a descriptive label, error text uses role=alert, and loading is announced in an aria-live region.
3. Inspect 320px mobile and desktop layouts, empty/loading/error/success states and no horizontal overflow.
4. Check every chart has a text equivalent, units, timeline and a source/assumption label.
5. Flag inert links and placeholders; do not render synthetic values as live NASA data.
6. Do not claim WCAG compliance unless manual keyboard and automated contrast checks have actually run.

## Exit criteria
- Concrete file/test/evidence changes, or explicitly documented blocked step.
- Risks and unverified claims disclosed.
- No installation script, authentication change or remote action is implied by reading this file.
