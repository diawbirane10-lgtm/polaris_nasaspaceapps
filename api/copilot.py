"""POLARIS Mission Copilot.

Scientific computations stay in the deterministic mission engine.  The optional
language model receives *only* calculated metrics and may explain them; it never
becomes the numerical source.  The offline mode is always available.
"""
from __future__ import annotations

import math
import os
from typing import Any, Literal

import requests
from pydantic import BaseModel, Field

from .decision import counterfactual
from .flow import plan_question

Action = Literal['explain', 'load_plus_40', 'battery_plus_50', 'pv_minus_20', 'pv_plus_30']

class CopilotRequest(BaseModel):
    question: str = Field(min_length=3, max_length=360)
    site: Literal['connecting_ridge', 'shackleton_rim'] = 'connecting_ridge'
    start: str = '2026-11-14T00:00Z'
    duration_hours: Literal[24, 48] = 24
    delay_hours: int = Field(default=48, ge=6, le=72)
    pv_area_m2: float = Field(default=16.0, gt=0, le=200, allow_inf_nan=False)
    load_w: float = Field(default=400.0, ge=0, le=100000, allow_inf_nan=False)
    battery_kwh: float = Field(default=20.0, gt=0, le=10000, allow_inf_nan=False)
    panel_mode: Literal['horizontal', 'tracking'] = 'horizontal'
    action: Action = 'explain'
    previous_field: Literal['load_w','battery_kwh','pv_area_m2'] | None = None
    min_soc_pct: float = Field(default=20.0, ge=0, le=100, allow_inf_nan=False)
    min_local_earth_hours: float = Field(default=6.0, ge=0, le=48, allow_inf_nan=False)
    max_local_earth_gap_hours: float = Field(default=24.0, ge=0, le=48, allow_inf_nan=False)


def computed(req: CopilotRequest, **overrides: Any) -> dict[str, Any]:
    values = {'site_key': req.site, 'start_utc': req.start,
              'duration_hours': req.duration_hours, 'delay_hours': req.delay_hours,
              'pv_area_m2': req.pv_area_m2, 'load_w': req.load_w,
              'battery_kwh': req.battery_kwh, 'mode': req.panel_mode}
    values.update(overrides)
    return counterfactual(**values)


def constraints(req: CopilotRequest, metrics: dict[str, float]) -> dict[str, Any]:
    rules = [
        ('minimum_battery_soc', 'Battery reserve', metrics['min_soc_pct'], req.min_soc_pct, '>=', '%'),
        ('minimum_local_earth_hours', 'Local Earth visibility', metrics['earth_visible_hours'], req.min_local_earth_hours, '>=', 'h'),
        ('maximum_local_earth_gap', 'Longest local Earth gap', metrics['max_earth_gap_hours'], req.max_local_earth_gap_hours, '<=', 'h'),
        ('unserved_energy', 'Unserved electrical energy', metrics['unserved_energy_kwh'], 0.0, '<=', 'kWh'),
    ]
    details = []
    for rule, label, observed, target, op, unit in rules:
        ok = observed >= target if op == '>=' else observed <= target
        details.append({'id': rule, 'label': label, 'observed': observed,
                        'threshold': target, 'op': op, 'unit': unit,
                        'status': 'PASS' if ok else 'FAIL'})
    return {'status': 'PASS' if all(d['status']=='PASS' for d in details) else 'FAIL',
            'rules': details, 'origin': 'Mission thresholds chosen by the user; not external acceptance criteria'}


def _summary_lines(name: str, m: dict[str, Any], cons: dict[str, Any]) -> str:
    failing = [r['label'] for r in cons['rules'] if r['status']=='FAIL']
    label = '; '.join(failing) if failing else 'none of the selected thresholds'
    return (f"{name}: minimum battery SOC {m['min_soc_pct']:.2f}%; "
            f"local Earth visibility {m['earth_visible_hours']:.1f} h; "
            f"longest Earth gap {m['max_earth_gap_hours']:.1f} h; "
            f"unserved energy {m['unserved_energy_kwh']:.3f} kWh. "
            f"Constraints not met: {label}.")


def _apply_action(req: CopilotRequest) -> tuple[dict[str, Any], str, dict[str,float]]:
    action = req.action
    options: dict[str,float] = {}
    desc = 'No change: assess three dated mission scenarios'
    if action=='load_plus_40':
        options={'load_w':round(req.load_w*1.4,4)}
        desc='Increase electrical demand by 40%'
    elif action=='battery_plus_50':
        options={'battery_kwh':round(req.battery_kwh*1.5,4)}
        desc='Increase battery capacity by 50%'
    elif action=='pv_minus_20':
        options={'pv_area_m2':round(req.pv_area_m2*.8,4)}
        desc='Reduce PV array area by 20%'
    elif action=='pv_plus_30':
        options={'pv_area_m2':round(req.pv_area_m2*1.3,4)}
        desc='Increase PV array area by 30%'
    if options.get('pv_area_m2',0)>200 or options.get('battery_kwh',0)>10000 or options.get('load_w',0)>100000:
        raise ValueError('What-if modification exceeds supported engineering input range')
    return computed(req, **options), desc, options


def _grounded_response(req:CopilotRequest, base:dict[str,Any], alt:dict[str,Any], action_label:str,
                       action_values:dict[str,Any], action_id: str | None = None) -> dict[str, Any]:
    analysis = []
    records=[]
    for key,scenario in base['scenarios'].items():
        m=scenario['summary']
        check=constraints(req,m)
        records.append({'id':key,'site':scenario['site_name'],'start_utc':scenario['start_utc'],
                        'metrics': {k:m[k] for k in ('min_soc_pct','earth_visible_hours','max_earth_gap_hours','sun_visible_hours','unserved_energy_kwh')},
                        'constraints':check})
        analysis.append(_summary_lines(key.replace('_',' ').capitalize(), m, check))
    changed=None
    if action_values:
        b=base['scenarios']['delayed']['summary'];a=alt['scenarios']['delayed']['summary']
        changed={'name':action_id or req.action,'label':action_label,'changed_inputs':action_values,
                 'old':{k:b[k] for k in ('min_soc_pct','unserved_energy_kwh','earth_visible_hours','max_earth_gap_hours')},
                 'new':{k:a[k] for k in ('min_soc_pct','unserved_energy_kwh','earth_visible_hours','max_earth_gap_hours')},
                 'proposed_scenarios':{k:{'site':v['site_name'],'start_utc':v['start_utc'],
                    'metrics':{field:v['summary'][field] for field in ('min_soc_pct','unserved_energy_kwh','earth_visible_hours','max_earth_gap_hours')},
                    'constraints':constraints(req,v['summary'])} for k,v in alt['scenarios'].items()},
                 'constraints':constraints(req,a)}
        analysis.append(f"What-if ({action_label}): SOC minimum {b['min_soc_pct']:.2f}% → {a['min_soc_pct']:.2f}%; "
                        f"unserved energy {b['unserved_energy_kwh']:.3f} → {a['unserved_energy_kwh']:.3f} kWh. "
                        'The new values were recomputed by the Python mission engine.')
    # Do not pretend geometric visibility is a viable RF downlink.
    analysis.append('Interpretation: Earth visibility is a local topographic bound, not a verified radio link. '
                    'The 6 km skyline, 6-hour epochs and assumed electrical design may change the result.')
    return {'mode':'engineering', 'answer':'\n\n'.join(analysis),
            'scenarios':records, 'what_if':changed,
            'inputs':base['inputs'], 'dataset_sha256':base['dataset_sha256'],
            'evidence':[{'label':'Source NASA observations','url':'/api/nasa-reference/'+req.site},
                        {'label':'JPL/SPICE cross-check','url':'/api/spice-validation'},
                        {'label':'Sampling sensitivity','url':'/api/science-audit'}],
            'model':'Python mission model with NASA JPL Horizons / LOLA reference data'}


def _llm_enrichment(req:CopilotRequest, response:dict[str,Any]) -> dict[str,Any]:
    provider=os.environ.get('POLARIS_LLM_PROVIDER','groq').lower()
    if provider not in ('groq','huggingface'):
        return response
    key=os.environ.get('POLARIS_LLM_API_KEY','').strip()
    if not key:
        return response
    endpoints={
        'groq':('https://api.groq.com/openai/v1/chat/completions','openai/gpt-oss-20b'),
        'huggingface':('https://router.huggingface.co/v1/chat/completions','openai/gpt-oss-120b'),
    }
    url,default_model=endpoints[provider]
    model=os.environ.get('POLARIS_LLM_MODEL',default_model)
    # Only metrics computed by POLARIS are given to the LLM. It cannot call tools or alter data.
    context={'question':req.question,'computed_evidence':response['answer'],
             'input_scenario':response['inputs'],'what_if':response['what_if']}
    try:
        request=requests.post(url,headers={'Authorization':'Bearer '+key},json={
            'model':model,'temperature':0.1,'max_tokens':450,
            'messages':[{'role':'system','content':(
                'You are the POLARIS mission analysis explainer. You MUST restrict all numeric claims to '
                'the computed evidence in the user message. Explain why constraints pass or fail and '
                'give concrete, reversible experiments. Never infer an RF link or mission safety from '
                'local Earth clearance. Never invent a threshold or physical quantity. '
                'If information is absent, say so. Respond succinctly in the language of the question.')},
                {'role':'user','content':__import__('json').dumps(context)}]
        },timeout=(4,14))
        request.raise_for_status()
        data=request.json()
        message=data['choices'][0]['message']['content']
        if isinstance(message,str) and 10 <= len(message) <= 6500:
            response['mode']='llm_explainer'
            response['language_model_commentary']=message
            response['provider']=provider
            response['provider_model']=model
    except (ValueError,LookupError,KeyError,IndexError,requests.RequestException):
        # The computed answer survives provider outage, tokens exhaustion and bad model output.
        response['mode']='engineering_fallback'
    return response


def analyze(req:CopilotRequest) -> dict[str,Any]:
    '''Interpret the actual question, execute whitelisted Python tools, return proof.''' 
    previous = {'field': req.previous_field} if req.previous_field else None
    planning=plan_question(req.question,{'load_w':req.load_w,
        'battery_kwh':req.battery_kwh,'pv_area_m2':req.pv_area_m2},previous)
    if planning.ask_clarification:
        return {'mode':'clarification', 'intent':planning.intent,
                'answer':planning.ask_clarification,'flow':{
                    'intent':planning.intent,'confidence':planning.confidence,
                    'reason':planning.interpretation,'updates':{},'tool_calls':[],
                    'human_review':False},'scenarios':[],'what_if':None,
                'evidence':[],'suggested_next':[]}
    if planning.handoff:
        return {'mode':'human_review','intent':planning.intent,
                'answer':('Human engineering review requested. Export the latest ' 
                          'mission report and send it to your mission engineering team. '
                          'POLARIS cannot contact a human reviewer automatically.'),
                'flow':{'intent':planning.intent,'confidence':'high',
                    'reason':planning.interpretation,'updates':{},'tool_calls':[],
                    'human_review':True},'scenarios':[],'what_if':None,
                'evidence':[{'label':'Simulation report endpoint','url':'/api/mission-report.pdf'}],
                'suggested_next':['Download the engineering report for review.']}
    base=computed(req)
    if planning.updates:
        updates=planning.updates
        if not set(updates) <= {'pv_area_m2','battery_kwh','load_w','delay_hours','site_key'}:
            raise ValueError('Unrecognized mission parameter requested')
        electrical=[updates.get(k, getattr(req,k)) for k in ('pv_area_m2','battery_kwh','load_w')]
        if (not all(isinstance(v,(int,float)) and math.isfinite(v) for v in electrical) or
            not 0<electrical[0]<=200 or not 0<electrical[1]<=10000 or not 0<=electrical[2]<=100000):
            raise ValueError('Requested electrical change exceeds valid simulation parameters')
        if updates.get('delay_hours',req.delay_hours) not in range(6,73,6):
            raise ValueError('Delay must be a 6-hour multiple between 6 and 72 hours')
        if updates.get('site_key',req.site) not in ('connecting_ridge','shackleton_rim'):
            raise ValueError('Unknown reference observation site')
        alternate=computed(req,**updates)
        label=planning.interpretation
        action_id='question_driven_calculation'
    elif req.action!='explain':
        alternate,label,updates=_apply_action(req)
        action_id=req.action
    else:
        alternate,label,updates=base,'No changes',{}
        action_id=None
    response=_grounded_response(req,base,alternate,label,updates,action_id)
    response['intent']=planning.intent
    response['flow']={'intent':planning.intent,'confidence':planning.confidence,
       'reason':planning.interpretation, 'updates':updates,
       'tool_calls':[{'name':'counterfactual','description':'Compute baseline + delayed + alternate observation point',
                      'dataset_sha256':base['dataset_sha256']}] +
                    ([{'name':'counterfactual','description':'Recompute edited mission parameters and verify constraints',
                        'input_overrides':updates,'dataset_sha256':base['dataset_sha256']}] if updates else []),
       'human_review':False}
    response['suggested_next']=[]
    for entry in response['scenarios']:
        failed=[r for r in entry['constraints']['rules'] if r['status']=='FAIL']
        if failed:
            response['suggested_next'].append({
                'scenario':entry['id'],'blocking_rules':[r['id'] for r in failed],
                'hint':'Change a time, site, requirement or electrical parameter and rerun to compare.',
                'source':'constraint checker, not AI-invented ranking'})
    return _llm_enrichment(req,response)
