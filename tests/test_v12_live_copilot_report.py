"""Regression tests for free-form question flow and generated engineering reports."""
from fastapi.testclient import TestClient
from api.index import app
from api.copilot import CopilotRequest, analyze
from api.flow import plan_question
from api.report import build_report_data, latex_source

client=TestClient(app)

PARAMS={'question':'Why does this plan fail?','site':'connecting_ridge',
        'start':'2026-11-14T00:00Z','duration_hours':24,'delay_hours':48,
        'pv_area_m2':16,'load_w':400,'battery_kwh':20,'panel_mode':'horizontal',
        'min_soc_pct':35,'min_local_earth_hours':6,'max_local_earth_gap_hours':24}


def test_free_text_recalculates_without_provider(monkeypatch):
    monkeypatch.delenv('POLARIS_LLM_API_KEY',raising=False)
    r=client.post('/api/copilot',json={**PARAMS,'question':'increase electrical load by 40%'})
    assert r.status_code==200
    data=r.json()
    assert data['intent']=='simulate_change'
    assert data['what_if']['changed_inputs']['load_w']==560
    assert data['flow']['tool_calls'][1]['name']=='counterfactual'
    assert data['what_if']['new']['min_soc_pct']<=data['what_if']['old']['min_soc_pct']


def test_multiple_free_text_changes():
    data=client.post('/api/copilot',json={**PARAMS,
      'question':'reduce load by 15% and increase PV area by 30%'}).json()
    assert data['what_if']['changed_inputs']=={'load_w':340,'pv_area_m2':20.8}


def test_ambiguous_question_does_not_crash_ui_contract():
    data=client.post('/api/copilot',json={**PARAMS,'question':'What about tomorrow?'}).json()
    assert data['mode']=='clarification'
    assert data['scenarios']==[]
    assert not data['flow']['tool_calls']


def test_multiturn_parameter_is_not_guessed_without_context():
    current={'load_w':400,'pv_area_m2':16,'battery_kwh':20}
    assert plan_question('20% more',current).updates=={}
    assert plan_question('20% more',current,{'field':'load_w'}).updates['load_w']==480


def test_pdf_tex_json_recomputed_from_same_evidence():
    outputs={fmt:client.post(f'/api/mission-report.{fmt}',json=PARAMS)
             for fmt in ('pdf','tex','json')}
    assert all(v.status_code==200 for v in outputs.values())
    assert outputs['pdf'].content.startswith(b'%PDF')
    assert len(outputs['pdf'].content)>10000
    assert 'Libertinus' in outputs['tex'].text
    assert r'\definecolor{polarisblue}' in outputs['tex'].text
    j=outputs['json'].json()
    assert len(j['scenarios'])==3
    assert len(j['dataset_sha256'])==64
    assert j['timeseries']['original'][0]['soc_pct']==80
    assert j['timeseries']['original'][-1]['hours_from_start']==24
    assert '>= 35' in outputs['tex'].text or '>= 35.00' in outputs['tex'].text


def test_report_respects_current_values():
    a=client.post('/api/mission-report.json',json=PARAMS).json()
    b=client.post('/api/mission-report.json',json={**PARAMS,'load_w':1500}).json()
    assert a['report_id'] != b['report_id']
    assert a['scenarios'][0]['metrics']['min_soc_pct'] > b['scenarios'][0]['metrics']['min_soc_pct']
    assert b['user_inputs']['load_w']==1500


def test_invalid_report_input_is_not_accepted():
    for field,bad in [('pv_area_m2',-1),('battery_kwh',0),('load_w','NaN'),('start','2028-01-01T00:00Z')]:
        resp=client.post('/api/mission-report.pdf',json={**PARAMS,field:bad})
        assert resp.status_code==422,(field,resp.text)


def test_web_exposes_report_buttons_and_copilot():
    html=client.get('/').text
    assert 'id="coReportPdf"' in html
    assert 'id="coReportTex"' in html
    assert 'downloadReport' in html
    assert 'previous_field:lastParameterField' in html
