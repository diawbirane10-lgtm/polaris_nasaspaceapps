"""Evidence-first mission decision review; the current simulation is always recalculated.

Model criterion status is not an assessment of spacecraft certification. Data provenance,
selected scope, and event detection are included with every decision record.
"""
from __future__ import annotations

from hashlib import sha256
import json
from math import isfinite
from typing import Any, Literal

from pydantic import Field, model_validator

from .copilot import CopilotRequest
from .report import build_report_data

SCENARIOS=('original','delayed','alternative_site_after_delay')
FOCI=('integrated','electrical','geometry')

class MissionReviewRequest(CopilotRequest):
    focus: Literal['integrated','electrical','geometry']='integrated'
    selected_scenarios: list[Literal['original','delayed','alternative_site_after_delay']] = Field(
        default_factory=lambda:list(SCENARIOS),min_length=1,max_length=3)
    include_trace: bool = True
    include_events: bool = True
    mission_label: str = Field('POLARIS lunar south-pole study',min_length=1,max_length=80)

    @model_validator(mode='after')
    def unique_scenarios(self):
        if len(self.selected_scenarios)!=len(set(self.selected_scenarios)):
            raise ValueError('Each selected scenario must be unique')
        return self


def active_rules(focus:str)->tuple[str,...]:
    if focus=='electrical':return ('minimum_battery_soc','unserved_energy')
    if focus=='geometry':return ('minimum_local_earth_hours','maximum_local_earth_gap')
    return ('minimum_battery_soc','unserved_energy','minimum_local_earth_hours','maximum_local_earth_gap')


def find_events(series:list[dict], req:MissionReviewRequest, focus:str, scenario_key:str)->list[dict[str,Any]]:
    """Detect actual state transitions, never a manufactured list of generic hazards."""
    ev=[]
    if focus in ('integrated','electrical'):
        # The first point is the initial battery state. Adjacent values belong to successive epochs.
        for a,b in zip(series,series[1:]):
            threshold=req.min_soc_pct
            if a['soc_pct']>=threshold>b['soc_pct']:
                ev.append({'type':'battery_reserve_breach','scenario':scenario_key,'hour':b['hours_from_start'],
                           'description':f"Battery SOC crossed below {threshold:g}% at the {b['hours_from_start']:g} h observation",
                           'value':b['soc_pct'],'unit':'%'})
            if a['soc_pct']<threshold<=b['soc_pct']:
                ev.append({'type':'battery_reserve_recovery','scenario':scenario_key,'hour':b['hours_from_start'],
                           'description':f"Battery SOC recovered above {threshold:g}% at the {b['hours_from_start']:g} h observation",
                           'value':b['soc_pct'],'unit':'%'})
    if focus in ('integrated','geometry'):
        for a,b in zip(series,series[1:]):
            if a['local_earth_clearance_deg']>0>=b['local_earth_clearance_deg']:
                ev.append({'type':'local_earth_occlusion','scenario':scenario_key,'hour':b['hours_from_start'],
                           'description':f"Earth passed below the modeled local skyline at sample {b['hours_from_start']:g} h",
                           'value':b['local_earth_clearance_deg'],'unit':'deg'})
            if a['local_earth_clearance_deg']<=0<b['local_earth_clearance_deg']:
                ev.append({'type':'local_earth_reappearance','scenario':scenario_key,'hour':b['hours_from_start'],
                           'description':f"Earth cleared the modeled local skyline at sample {b['hours_from_start']:g} h",
                           'value':b['local_earth_clearance_deg'],'unit':'deg'})
            if a['local_sun_clearance_deg']>0>=b['local_sun_clearance_deg']:
                ev.append({'type':'local_solar_occlusion','scenario':scenario_key,'hour':b['hours_from_start'],
                           'description':f"Sun moved below the modeled local skyline at sample {b['hours_from_start']:g} h",
                           'value':b['local_sun_clearance_deg'],'unit':'deg'})
    return sorted(ev,key=lambda x:x['hour'])


def build_review(req:MissionReviewRequest)->dict[str,Any]:
    source=build_report_data(req)
    considered=set(active_rules(req.focus))
    scenarios=[]
    for s in source['scenarios']:
        if s['key'] not in req.selected_scenarios:continue
        checks=[]
        for rule in s['constraint_evaluation']['rules']:
            if rule['id'] not in considered:continue
            if not all(isfinite(float(rule[x])) for x in ('observed','threshold')):
                raise ValueError('Nonfinite constraint result')
            checks.append({**rule,'evidence_metric':rule['id'],'basis':'engineer-defined threshold, current simulation',
                          'scope':'local-model evaluation'})
        failures=[x for x in checks if x['status']=='FAIL']
        series=source['timeseries'][s['key']]
        events=find_events(series,req,req.focus,s['key']) if req.include_events else []
        scenarios.append({**s,'checks':checks,'blocking_criteria':[x['id'] for x in failures],
            'decision': 'REVISE PLAN' if failures else 'MEETS MODELED LIMITS',
            'event_count':len(events),'events':events,
            'trace':series if req.include_trace else [],
        })
    if not scenarios:raise ValueError('No selected mission scenario found')
    all_blockers=sorted(set(k for s in scenarios for k in s['blocking_criteria']))
    accepted=[s['key'] for s in scenarios if not s['blocking_criteria']]
    diff=[]
    if len(scenarios)>=2:
        baseline=scenarios[0]
        fields={'integrated':('earth_visible_hours','min_soc_pct','unserved_energy_kwh'),
                'electrical':('min_soc_pct','unserved_energy_kwh'),
                'geometry':('earth_visible_hours','max_earth_gap_hours')}
        for item in scenarios[1:]:
            changes={field:round(item['metrics'][field]-baseline['metrics'][field],3) for field in fields[req.focus]}
            diff.append({'from':baseline['key'],'to':item['key'],'metric_deltas':changes})
    # Versioned digest includes selection and all thresholds, so two distinct decisions are not conflated.
    settings=req.model_dump(mode='json')
    fingerprint=sha256(json.dumps({'inputs':settings,'dataset_sha256':source['dataset_sha256']},sort_keys=True).encode()).hexdigest()
    event_count=sum(s['event_count'] for s in scenarios)
    return {'review_id':'PDR-'+fingerprint[:12].upper(),'simulation_id':source['report_id'],
            'version':'1.4.0','generated_utc':source['generated_utc'],
            'mission_label':req.mission_label,'focus':req.focus,'selected_scenarios':list(req.selected_scenarios),
            'dataset_sha256':source['dataset_sha256'],'inputs':settings,'scenarios':scenarios,
            'comparison':diff,'blocking_criteria':all_blockers,'modeled_limits_met_by':accepted,
            'total_detected_events':event_count,'model_settings':source['model_settings'],
            'data_sources':source['data_sources'],'analysis_notes':source['analysis_notes'],
            'analysis_scope':{
              'electrical':'Solar production and battery energy balance with mission reserve constraints',
              'geometry':'Sun/Earth observer geometry and local skyline, with visibility time requirements',
              'integrated':'Electrical energy, local Sun/Earth geometry and mission timing constraints'}[req.focus],
            'interpretation':'No single universal score: each option is classified against engineer-selected numerical limits. '
             'An absence of local blockers cannot prove global visibility, RF connectivity, or landing suitability.',
            'status':'REVISIONS REQUIRED' if all_blockers else 'MODELED LIMITS SATISFIED',
            'report_variants':['brief','dossier'],
            'chart_fields':(['soc_pct','pv_w'] if req.focus=='electrical' else
                            ['local_sun_clearance_deg','local_earth_clearance_deg'] if req.focus=='geometry' else
                            ['soc_pct','local_earth_clearance_deg']),
            'traceability':{'recomputed':True,'ephemeris_utc_step_hours':6,'local_terrain_radius_km':6,
                'report_fingerprint':fingerprint,'rule_ids':list(considered)}}
