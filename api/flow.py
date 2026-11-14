"""POLARIS intent and tool-planning rules, inspired by RampStack chatbot-flow-design.

No text here is a scientific observation. A parsed question becomes a constrained
calculation plan, then the engine recomputes NASA-backed scenarios. Unrecognized
requests are not secretly transformed into pre-recorded Q&A.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Any

# Explicit, auditable intent architecture: conversation support is not a FAQ.
_FIELDS = {
    'load_w': r'(?:electrical\s+)?(?:load|consumption|demand|power\s+draw|consommation|puissance|charge(?:\s+électrique)?)',
    'battery_kwh': r'(?:battery|storage|batterie|stockage|capacity|capacité)',
    'pv_area_m2': r'(?:pv\s+(?:array|area)|solar\s+(?:panels?|array|area)|photovoltaic\s+area|panneaux?\s+(?:solaires?|photovoltaïques?)|surface\s+(?:solaire|pv)|pv|panels?)',
}
_UNIT = {'load_w':r'(?:w|watts?)','battery_kwh':r'(?:kwh|kilowatt.hours?)','pv_area_m2':r'(?:m2|m²|sq\s*m|square\s*meters?)'}
_VERBS_UP = r'(?:increase|increases|increasing|raise|raised|boost|add|augmenter?|augmente|hausse|up|more|plus|\+)'
_VERBS_DOWN = r'(?:decrease|decreases|decreasing|reduce|reduced|lower|cut|baisser?|réduire|diminue|down|less|moins|\-)'
_PERCENT = r'(\d+(?:[.,]\d+)?)\s*(?:%|percent|pour\s*cent)'
_NUMBER = r'(\d+(?:[.,]\d+)?)'

@dataclass(frozen=True)
class FlowPlan:
    intent: str
    updates: dict[str, Any]
    interpretation: str
    confidence: str = 'high'
    ask_clarification: str | None = None
    handoff: bool = False


def _number(s: str) -> float:
    return float(s.replace(',', '.'))


def _matches(text: str, field: str) -> list[re.Match]:
    return list(re.finditer(_FIELDS[field], text, re.I))


def _extract_edit(text: str, field: str, current: float) -> float | None:
    """Parse local natural-language engineering edits; never infer an omitted unit."""
    # Keep independent instructions apart: "reduce load 10% and increase PV 30%".
    fragments=re.split(r"\s+(?:and|et|then|puis)\s+|[;,]\s*(?=[a-z])", text, flags=re.I)
    for fragment in fragments:
        for hit in _matches(fragment, field):
            left=fragment[:hit.start()];right=fragment[hit.end():]
            num=re.search(r"\b"+_NUMBER+r"\s*"+_UNIT[field]+r"\b",right,re.I)
            if num and not re.search(r"[%]|percent|pour\s*cent",right[:num.end()],re.I):
                return _number(num.group(1))
            pct=re.search(_PERCENT, fragment, re.I)
            if not pct:continue
            # A percentage must be within 32 chars of its referenced noun.
            if min(abs(pct.start()-hit.end()), abs(pct.end()-hit.start()))>32:continue
            percent=_number(pct.group(1))
            if not 0<=percent<=1000:raise ValueError('Percent outside supported range 0..1000')
            # Direction scoped to this independent clause; the bare '+' / '-' immediately
            # preceding the percent works even when there is no explicit verb.
            up=bool(re.search(_VERBS_UP, fragment,re.I));down=bool(re.search(_VERBS_DOWN,fragment,re.I))
            if not up and not down:
                pre=fragment[max(0,pct.start()-3):pct.start()]
                up='+' in pre;down='-' in pre
            if up and down:raise ValueError('Ambiguous direction for '+field)
            if not (up or down):continue
            return round(current*(1 + percent/100 if up else 1-percent/100),5)
    return None


def plan_question(question: str, current: dict[str,float], previous: dict[str, Any] | None = None) -> FlowPlan:
    q=' '.join(question.strip().split()).lower()
    if not q:
        return FlowPlan('clarify',{},'empty request','low','Ask about mission constraints, site comparison or an electrical change.')
    if re.search(r'\b(talk to (a|the) (engineer|human)|human review|human operator|contact engineer|validation humaine|parler à un ingénieur)\b',q):
        return FlowPlan('human_review',{},'Human engineering review requested',handoff=True)
    if re.search(r'\b(weather|restaurant|stock market|horoscope|flight ticket|actualité sportive)\b',q):
        return FlowPlan('out_of_scope',{},'outside lunar mission analysis', 'high', 'This mission copilot only analyzes lunar observation geometry, energy, constraint checks and scenario changes.')
    changes={}
    for f,val in current.items():
        new=_extract_edit(q,f,val)
        if new is not None:changes[f]=new
    # Resolve 'what about 20% more?' using previous successful parameter; no guess if not available.
    if not changes and previous and previous.get('field') in current:
        m=re.search(_PERCENT+r'\s*(more|less|plus|moins)\b',q,re.I)
        if m:
            change=_number(m.group(1))/100 * (1 if m.group(2) in ('more','plus') else -1)
            f=previous['field'];changes[f]=round(current[f]*(1+change),5)
    # A flight director can alter *mission* parameters, not just electrical sizing.
    # Only explicit operator directives are applied: observations like "a 24h delay"
    # are not silently interpreted as an instruction to modify the plan.
    move=re.search(r'\b(?:delay|postpone|push(?:\s+back)?|retarder|reporter|décaler)\s+(?:(?:the|la|le|our)\s+)?(?:(?:mission|landing|launch|schedule|atterrissage|départ)\s+)?(?:by\s+|de\s+|d[\'’]\s*)?(\d{1,3})\s*(?:hours?|hrs?|h|heures?)\b',q,re.I)
    if move:
        delay=int(move.group(1))
        if delay not in range(6,73,6):
            raise ValueError('Mission delay must be between 6 and 72 hours, in 6-hour increments')
        changes['delay_hours']=delay
    site_match=re.search(r'\b(?:switch|change|move|select|choose|try|use|passer|choisir|utiliser)\b[^.!?]{0,45}\b(shackleton(?:\s+rim)?|connecting\s+ridge|ridge)\b',q,re.I)
    if site_match:
        changes['site_key']='shackleton_rim' if 'shackleton' in site_match.group(1) else 'connecting_ridge'
    if changes:
        summary=', '.join(f'{field} = {value:g}' if isinstance(value,(int,float)) else f'{field} = {value}' for field,value in changes.items())
        return FlowPlan('simulate_change',changes,'Recompute with '+summary)
    if re.search(r'\b(source|evidence|provenance|nasa data|spice|validation|method|référence|preuve|fiabilit|how.*calculat)\b',q):
        return FlowPlan('sources',{},'Inspect NASA data provenance and SPICE audit')
    if re.search(r'\b(compare|comparison|versus|vs\.?|site|alternative|better|préférable|comparer|ridge|shackleton|différence)\b',q):
        return FlowPlan('compare_sites',{},'Compare matching mission scenarios')
    if re.search(r'\b(why|fail|constraint|risk|risk|bottleneck|recommend|solution|optimi[sz]|improve|mission|energy|battery|solar|earth|sun|power|communication|visibility|soc|pourquoi|contrainte|risque|énergie|batterie|soleil|terre|visibilité|échec)\b',q):
        return FlowPlan('evaluate_constraints',{},'Evaluate mission constraints and engineering tradeoffs')
    return FlowPlan('clarify',{},'Intent not sufficiently determined','low',
                    'I can compare sites, explain constraints, inspect NASA evidence, or calculate a change such as “increase load by 25%”. Which would help?')
