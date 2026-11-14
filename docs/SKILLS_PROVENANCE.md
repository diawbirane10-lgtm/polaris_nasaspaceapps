# POLARIS — reviewed coding skills (14 Nov 2026)

## Selection and provenance
These original, project-specific SKILL.md files adapt *workflows*, not scripts or copyrighted third-party code, after reviewing the cited external sources:

| Local project skill | Reviewed upstream sources | How applied |
| --- | --- | --- |
| `polaris-architecture` | [system-design-draft](https://github.com/proflead/codex-skills-library/blob/master/skills/backend/system-design-draft/SKILL.md), [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | architecture map, scoped interfaces, assumption tracking |
| `polaris-scientific-validation` | [zero-hallucination-coder](https://github.com/alirezarezvani/claude-skills/blob/main/engineering/zero-hallucination-coder/skills/zero-hallucination-coder/SKILL.md) | independent evidence gate on real vs synthetic data |
| `polaris-testing` | [unit-test-starter](https://github.com/proflead/codex-skills-library/blob/master/skills/testing/unit-test-starter/SKILL.md), [integration-test-planner](https://github.com/proflead/codex-skills-library/blob/master/skills/testing/integration-test-planner/SKILL.md) | deterministic boundary & API tests |
| `polaris-api-contract` | [api-contract-checker](https://github.com/proflead/codex-skills-library/blob/master/skills/api/api-contract-checker/SKILL.md), [api-design-reviewer](https://github.com/alirezarezvani/claude-skills/blob/main/engineering/skills/api-design-reviewer/SKILL.md) | error-code and JSON contract checks |
| `polaris-design-qa` | [accessibility-basic-check](https://github.com/proflead/codex-skills-library/blob/master/skills/frontend/accessibility-basic-check/SKILL.md), [design-qa](https://github.com/alirezarezvani/claude-skills/blob/main/product-team/skills/design-qa/SKILL.md) | keyboard/focus/live state and source audit |
| `polaris-pitch` | [readme-polish](https://github.com/proflead/codex-skills-library/blob/master/skills/docs/readme-polish/SKILL.md), Space Apps judging/submission guides | evidence-driven demo and handoff |

## Reviewed but deliberately not installed
- `sickn33/agentic-awesome-skills`: 2,957+ skills; large supply-chain/trust surface and mixed licenses, so no mass installation.
- `ComposioHQ/awesome-claude-skills`: curated directory/integrations; no reason to connect 1,000 external services for a self-contained scientific prototype.
- `raccrompton/claude-codex-skills`: depends on local logged-in Codex CLI, gh CLI, Claude Code; not available from this coding environment.
- `openai/skills`: upstream README says deprecated, points to current OpenAI plugins repository; no bulk install.
- `Appllama/appllama-skills`: React Native/Expo-specific, not needed for our web demo.
- `Vincentwei1021/anything2explainer`: heavy video rendering dependencies and PolyForm Noncommercial; pitch copy/slide guide is enough for now.
- `htdt/godogen`: Godot game generation does not match the numerical mission tool.

## Security boundary
A SKILL.md is an **instruction file**, not a trusted executable. We reviewed sources and authored a minimal set for this project. No external install script, post-install hook, credential request, PR merge gate, network proxy, or account changes were imported. Original repos retain their own licenses; links are for attribution. The local adaptations are independent project documents.

## Work completed using these skills
- `polaris-testing` → added deterministic API validation and failure-path tests.
- `polaris-api-contract` → checked preservation of /api/health and /api/mission schema/status behavior.
- `polaris-design-qa` → added live status and accessible alert/focus semantics to HTML.
- `polaris-architecture` → documented no additional cloud service or dependency.
- `polaris-scientific-validation` → kept terrain/JPL verification explicitly NOT VERIFIED until data are obtained.
- `polaris-pitch` → retained concise challenge/value and explicit physics caveats.
