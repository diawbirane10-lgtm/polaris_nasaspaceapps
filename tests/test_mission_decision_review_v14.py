"""Adaptive report and decision review tests across three independent study scopes."""
from fastapi.testclient import TestClient
from pypdf import PdfReader
from io import BytesIO
from api.index import app
from api.review import MissionReviewRequest, build_review, find_events
from api.review_pdf import latex_decision_report

c=TestClient(app)
BASE={"question":"Evaluate mission options", "site":"connecting_ridge",
      "start":"2026-11-14T00:00Z", "duration_hours":24,"delay_hours":48,
      "pv_area_m2":16,"load_w":700,"battery_kwh":20,"panel_mode":"horizontal",
      "min_soc_pct":35,"min_local_earth_hours":6,"max_local_earth_gap_hours":24}


def test_electrical_focus_filters_geometry_and_curves():
    d=c.post('/api/mission-review',json={**BASE,'focus':'electrical',
        'selected_scenarios':['original','delayed']}).json()
    assert d['chart_fields']==['soc_pct','pv_w']
    assert len(d['scenarios'])==2
    assert all(set(rule['id'] for rule in s['checks'])=={'minimum_battery_soc','unserved_energy'} for s in d['scenarios'])
    latex=c.post('/api/mission-decision/dossier.tex',json={**BASE,'focus':'electrical','selected_scenarios':['original']}).text
    assert 'Photovoltaic output' in latex and 'Battery state of charge' in latex
    assert 'Earth over local horizon' not in latex
    assert 'Earth visibility' not in latex


def test_geometry_focus_filters_power_and_uses_earth_trace():
    r=c.post('/api/mission-review',json={**BASE,'focus':'geometry',
        'selected_scenarios':['alternative_site_after_delay']})
    assert r.status_code==200,r.text
    d=r.json()
    assert d['chart_fields']==['local_sun_clearance_deg','local_earth_clearance_deg']
    assert len(d['scenarios'])==1
    assert not any('battery' in x['id'] for x in d['scenarios'][0]['checks'])
    assert d['scenarios'][0]['trace']
    tex=c.post('/api/mission-decision/dossier.tex',json={**BASE,'focus':'geometry',
        'selected_scenarios':['alternative_site_after_delay']}).text
    assert 'Earth over local horizon' in tex
    assert 'Photovoltaic output (W)' not in tex


def test_dossier_and_brief_are_different_recomputed_documents():
    body={**BASE,'focus':'integrated','selected_scenarios':['original','delayed']}
    brief=c.post('/api/mission-decision/brief.pdf',json=body)
    full=c.post('/api/mission-decision/dossier.pdf',json=body)
    assert brief.status_code==full.status_code==200
    assert brief.content[:4]==full.content[:4]==b'%PDF'
    assert brief.headers['X-POLARIS-REVIEW-ID']==full.headers['X-POLARIS-REVIEW-ID']
    btxt='\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(brief.content)).pages)
    dtxt='\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(full.content)).pages)
    assert 'Mission Decision Brief' in btxt and 'Engineering Simulation Dossier' in dtxt
    assert 'Simulation traces' in dtxt and 'Simulation traces' not in btxt


def test_empty_event_list_does_not_invent_problems():
    d=build_review(MissionReviewRequest(**BASE,focus='electrical',selected_scenarios=['original']))
    assert len(d['scenarios'])==1
    assert d['total_detected_events']>=0
    assert all(e['type'] in ('battery_reserve_breach','battery_reserve_recovery') for e in d['scenarios'][0]['events'])


def test_detects_crossing_from_computed_samples():
    req=MissionReviewRequest(**BASE,focus='electrical')
    series=[{'hours_from_start':0,'soc_pct':70,'local_earth_clearance_deg':-1,'local_sun_clearance_deg':-3},
            {'hours_from_start':6,'soc_pct':32,'local_earth_clearance_deg':2,'local_sun_clearance_deg':-2},
            {'hours_from_start':12,'soc_pct':47,'local_earth_clearance_deg':-2,'local_sun_clearance_deg':2}]
    e=find_events(series,req,'integrated','original')
    assert [x['type'] for x in e]==['local_earth_reappearance','battery_reserve_breach','battery_reserve_recovery','local_earth_occlusion'] or {x['type'] for x in e}=={'battery_reserve_breach','battery_reserve_recovery','local_earth_occlusion','local_earth_reappearance'}
    assert {x['hour'] for x in e}=={6,12}


def test_report_fingerprint_changes_with_requirements_and_scope():
    a=c.post('/api/mission-review',json=BASE).json()
    b=c.post('/api/mission-review',json={**BASE,'min_soc_pct':50}).json()
    g=c.post('/api/mission-review',json={**BASE,'focus':'geometry'}).json()
    assert len({a['review_id'],b['review_id'],g['review_id']})==3
    assert a['dataset_sha256']==b['dataset_sha256']==g['dataset_sha256']


def test_selection_validation_and_out_of_window_dates():
    for changes in ({'selected_scenarios':[]},{'selected_scenarios':['original','original']},
                    {'selected_scenarios':['unknown']},{'start':'2028-01-01T00:00Z'}):
        r=c.post('/api/mission-review',json={**BASE,**changes})
        assert r.status_code==422,r.text


def test_charts_are_skipped_if_not_requested():
    p={**BASE,'focus':'geometry','include_trace':False}
    data=c.post('/api/mission-review',json=p).json()
    assert all(s['trace']==[] for s in data['scenarios'])
    text=c.post('/api/mission-decision/dossier.tex',json=p).text
    assert 'Time-series inclusion disabled' in text


def test_routes_and_ui_connected_to_active_settings():
    html=c.get('/demo').text
    for term in ('data-nav="review"','id="reviewForm"','id="reviewStatus"',
                 'function reviewPayload()','/api/mission-review','/api/mission-decision/',
                 'id="coJumpReview"','id="reviewLabel"'):
        assert term in html
    assert c.post('/api/mission-decision/dossier.json',json=BASE).status_code==200
    assert c.post('/api/mission-decision/missing.pdf',json=BASE).status_code==404
