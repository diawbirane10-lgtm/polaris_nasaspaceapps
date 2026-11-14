"""Mission Copilot tests: evidence-grounding, action recalculation and resilience."""
from fastapi.testclient import TestClient
from api.index import app
from api.copilot import CopilotRequest,analyze
from unittest.mock import Mock
import math

client=TestClient(app)

def payload(**updates):
    p={"question":"What constraints are blocking our mission?", "site":"connecting_ridge",
       "start":"2026-11-14T00:00Z", "duration_hours":24,"delay_hours":48,
       "pv_area_m2":16, "load_w":400,"battery_kwh":20,"panel_mode":"horizontal",
       "min_soc_pct":20,"min_local_earth_hours":6,"max_local_earth_gap_hours":24,
       "action":"explain"}
    p.update(updates)
    return p

def test_copilot_explains_actual_computed_scenarios_without_key(monkeypatch):
    monkeypatch.delenv('POLARIS_LLM_API_KEY',raising=False)
    r=client.post('/api/copilot',json=payload())
    assert r.status_code==200, r.text
    body=r.json()
    assert body['mode']=='engineering'
    assert len(body['scenarios'])==3
    assert len(body['dataset_sha256'])==64
    assert 'NASA' in body['model']
    ridge=body['scenarios'][0]
    assert ridge['metrics']['earth_visible_hours']==0
    earth_rule=next(x for x in ridge['constraints']['rules'] if x['id']=='minimum_local_earth_hours')
    assert earth_rule['status']=='FAIL'
    assert earth_rule['observed']==0
    assert 'no external' not in body['answer'].lower()

def test_copilot_recomputes_actual_what_if():
    low=client.post('/api/copilot',json=payload(action='explain')).json()
    high=client.post('/api/copilot',json=payload(action='load_plus_40')).json()
    changed=high['what_if']
    assert changed['changed_inputs']['load_w']==560
    assert changed['new']['min_soc_pct'] <= changed['old']['min_soc_pct']
    assert changed['new']['unserved_energy_kwh'] >= changed['old']['unserved_energy_kwh']
    assert high['scenarios']==low['scenarios']  # baseline always stable

def test_power_experiment_does_not_change_visibility():
    r=client.post('/api/copilot',json=payload(action='battery_plus_50')).json()
    assert r['what_if']['changed_inputs']['battery_kwh']==30
    assert r['what_if']['new']['earth_visible_hours']==r['what_if']['old']['earth_visible_hours']

def test_thresholds_are_user_supplied_not_hidden_ranking():
    high=client.post('/api/copilot',json=payload(min_soc_pct=100)).json()
    low=client.post('/api/copilot',json=payload(min_soc_pct=0)).json()
    assert high['scenarios'][1]['metrics']==low['scenarios'][1]['metrics']
    assert 'user' in high['scenarios'][1]['constraints']['origin'].lower()
    assert high['scenarios'][1]['constraints']['status']=='FAIL'

def test_reject_bad_inputs_and_invalid_dates():
    for field,bad in [('pv_area_m2','NaN'),('load_w','Infinity'),('battery_kwh',0),('action','change-orbit'),('question','a')]:
        r=client.post('/api/copilot',json=payload(**{field:bad}))
        assert r.status_code==422,(field,r.text)
    assert client.post('/api/copilot',json=payload(start='2030-01-01T00:00Z')).status_code==422


def test_provider_outage_uses_computed_fallback(monkeypatch):
    import api.copilot as cp
    monkeypatch.setenv('POLARIS_LLM_PROVIDER','groq')
    monkeypatch.setenv('POLARIS_LLM_API_KEY','synthetic-test-key-not-real')
    def simulated_unavailable(*args,**kwargs):
        raise cp.requests.Timeout('mock provider outage')
    monkeypatch.setattr(cp.requests,'post',simulated_unavailable)
    r=client.post('/api/copilot',json=payload(action='pv_minus_20'))
    assert r.status_code==200
    j=r.json();assert j['mode']=='engineering_fallback'
    assert j['what_if']['changed_inputs']['pv_area_m2']==12.8
    assert j['scenarios'][0]['metrics']['earth_visible_hours']==0


def test_copilot_ui_has_controls_and_route():
    html=client.get('/').text
    assert 'data-nav="copilot"' in html
    assert 'data-page="copilot"' in html
    assert '/api/copilot' in html
    assert 'APPLY THESE PARAMETERS' in html
    assert 'aria-live="polite"' in html
    assert 'prefers-reduced-motion' in html
