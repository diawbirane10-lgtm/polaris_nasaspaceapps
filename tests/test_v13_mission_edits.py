"""Mission director natural language edits and evidence tracking."""
from fastapi.testclient import TestClient
from api.index import app
from api.flow import plan_question

client=TestClient(app)
BASE={'question':'Please delay the landing by 24 hours',
      'site':'connecting_ridge','start':'2026-11-14T00:00Z',
      'delay_hours':48, 'duration_hours':24,'pv_area_m2':16,
      'battery_kwh':20,'load_w':400,'panel_mode':'horizontal'}


def test_parse_flight_delay():
    p=plan_question('Please delay the landing by 24 hours',{})
    assert p.updates=={'delay_hours':24}
    assert p.intent=='simulate_change'


def test_parse_site_change():
    p=plan_question('Switch the mission site to Shackleton Rim',{})
    assert p.updates=={'site_key':'shackleton_rim'}


def test_compare_is_not_arbitrarily_applied():
    p=plan_question('Compare Shackleton Rim with Connecting Ridge',{})
    assert p.intent=='compare_sites'
    assert not p.updates


def test_api_recomputes_delay_and_provides_proof():
    response=client.post('/api/copilot',json=BASE)
    assert response.status_code==200,response.text
    d=response.json()
    assert d['flow']['updates']=={'delay_hours':24}
    assert d['flow']['tool_calls'][1]['name']=='counterfactual'
    assert d['what_if']['proposed_scenarios']['delayed']['start_utc']=='2026-11-15T00:00Z'
    assert d['what_if']['proposed_scenarios']['delayed']['constraints']['rules']


def test_api_recomputes_site():
    d=client.post('/api/copilot',json={**BASE,'question':'Change mission site to Shackleton Rim'}).json()
    assert d['what_if']['changed_inputs']['site_key']=='shackleton_rim'
    assert 'Shackleton' in d['what_if']['proposed_scenarios']['delayed']['site']


def test_invalid_delay_is_rejected():
    r=client.post('/api/copilot',json={**BASE,'question':'Delay landing by 25 hours'})
    assert r.status_code==422


def test_ui_supports_applying_mission_updates():
    html=client.get('/demo').text + client.get('/assets/polaris-app.js').text
    assert "if(k==='site_key')" in html
    assert "if(k==='delay_hours')" in html
    assert 'APPLY & SIMULATE MISSION' in html
