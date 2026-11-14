# POLARIS v1.2 | Decision Copilot & Report Generator

Implemented with the RampStack `chatbot-flow-design` intent architecture (MIT, not verbatim code reuse):
https://github.com/rampstackco/claude-skills/blob/main/skills/chatbot-flow-design/SKILL.md

- Mission question text is parsed into whitelisted scientific tool calls. The authoritative numerical engine is `counterfactual()` with NASA observations. Unclear/out-of-domain requests clarify or return a review handoff.
- Optional LLM via backend environment variables `POLARIS_LLM_PROVIDER` (`groq` or `huggingface`), `POLARIS_LLM_API_KEY`, `POLARIS_LLM_MODEL`. The key must remain on server; model never writes output metrics.
- Without a configured LLM, all numerical decisions, natural-language parameter parsing and report generation still work; the UI labels that mode **Engineering analysis**.
- Free-text experiment examples: `increase load by 40%`, `reduce PV area by 20%`, `battery to 30 kWh`, `reduce load by 15% and increase PV area by 30%`.
- POST `/api/mission-report.pdf`, `/api/mission-report.tex`, `/api/mission-report.json` accept the same mission input schema as `/api/copilot`. They recompute NASA-backed scenario results each time.
- PDF serverless output uses ReportLab and locally available serif font; XeLaTeX source compiles with embedded Libertinus Serif on a LaTeX installation and contains colored charts/logo with monochrome main text.
- Reports include the model equations, the engineer's thresholds, all three scenarios and dataset digest; do not confuse a sampled geometric Earth-clear duration with an RF link.

This mode is a dynamic constrained assistant, **not** a remotely hosted LLM by default. An LLM requires a configured external API key and is optional.
