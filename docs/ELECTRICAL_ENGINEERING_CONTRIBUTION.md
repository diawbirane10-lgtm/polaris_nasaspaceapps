# POLARIS — Electrical engineering contribution (NASA Space Apps 2026)

## Scope and engineering question
Can a preliminary photovoltaic-and-battery electrical power subsystem support a selected lunar south-pole landing/operations window when the site-specific solar horizon and landing delay are included?

This is a **reproducible energy-feasibility prototype, not an electrical circuit implementation or a flight-qualified power system**. The system helps identify *power and energy deficits* and tests design tradeoffs for an illustrative rover/lander load.

## Architecture — conceptual DC power system
PV array → power-conditioning DC/DC converter (conceptual only) → DC bus ↔ battery energy storage; DC bus → electrical loads.

The current implementation **numerically simulates** solar generation, constant electrical load, battery charge balance, clipping and unmet energy. It does **not** design the converter, select bus voltage, simulate switching transients, calculate wiring or protections, verify the BMS, or validate thermal/radiation/aging performance. Those elements are future engineering work.

## Implemented physical calculations
1. **PV generation at each epoch:** `P_PV = 1361 W/m² × A [m²] × 0.28 × 0.78 × orientation_factor × solar_disk_visible_fraction`. A horizontal panel uses `max(0,sin(solar_elevation))`; ideal 2-axis tracking uses a factor of 1, when the Sun is visible. All efficiencies are modeling assumptions.
2. **Load energy:** `E_load,k = P_load × Δt_k` and nominal 24-hour demand `P_load × 24 h`.
3. **Battery energy balance:** `E_batt,k+1 = clamp(E_batt,k + (P_PV,k - P_load)Δt_k, 0, C_batt)`. Initial state of charge is 80%; the engine accumulates unserved energy in kWh when the energy balance goes negative.
4. **Engineering outputs:** minimum and terminal SOC, PV energy and load energy over the sampled reference window, maximum sun-darkness interval, unmet energy, and user-defined pass/fail thresholds.
5. **Sensitivity studies:** site change (Connecting Ridge vs Shackleton Rim), date/delay, load increase/decrease, PV area, tracking assumption and battery capacity.

## NASA-data provenance and limitations
Site horizon comes from a NASA/GSFC LOLA-derived local profile (6 km radius); Sun/Earth apparent geometry is based on JPL Horizons and SPICE comparison artifacts. Samples are every 6 hours. The observed Earth elevation above a local skyline is **not** a verified RF communication link. Remote hills, thermal management, radiation, converter/BMS losses, component degradation and transient power behavior are not modeled. Conclusions cannot certify a landing site or flight hardware.

## Where to see it
- **Power systems** (section 4) — parameters, battery SOC graph and **From lunar sunlight to a resilient DC bus** with a quantitative energy ledger.
- **Scenarios** (section 3) — compare date/terrain/electrical scenarios.
- **AI Copilot** (section 7) — natural-language intent translated into whitelisted parameter edits, deterministic Python recalculation, source-tracked explanation, optional connected LLM.
- **Decision Review** (section 8) — computed constraints and engineering dossier exports.

## Copilot architecture: scoped, not trained
The COPILOT is not a newly trained model. It follows the [RampStack chatbot-flow-design](https://github.com/rampstackco/claude-skills/blob/main/skills/chatbot-flow-design/SKILL.md) method: intent recognition → validated engineering edit → physics calculation → grounded explanation → explicit fallback. In the deployed environment, the optional external LLM may be disconnected; the deterministic engineering fallback remains usable. Never call this a trained domain-specific neural model without actual fine-tuning and evaluation evidence.

## Example of a defensible portfolio description (English)
**POLARIS — Lunar Mission Electrical Power Feasibility & Decision Support** (NASA Space Apps Challenge 2026).
Developed a physics-based PV/battery energy-feasibility module integrated with NASA JPL Horizons and LOLA-derived local terrain data, enabling comparison of south-pole reference sites and delayed-landing scenarios. Implemented parameterized load, solar-array area, battery storage and tracking assumptions, time-stepped battery SOC, unmet-energy calculation, and explainable engineering what-if analyses via a constrained mission Copilot. Documented limits: local 6 km horizon, 6-hour samples, no converter/thermal/RF-link validation. **Research/demo prototype — not flight qualified.**

## Next logical technical upgrade
Create an electrical system simulation with explicit DC-bus nominal voltage, buck/boost converter and MPPT, battery voltage/current and BMS states, load profiles, efficiency maps and protections; validate transients and energy estimates independently (e.g. MATLAB/Simulink), then compare the design against the present system-level Python model. Do not present these extensions as completed.
