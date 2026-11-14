"""Counterfactual tests use checked-in NASA data; no synthetic arrays or network."""
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from api.decision import counterfactual
from api.index import app

client = TestClient(app)

def test_replanning_preserves_utc_and_durations():
    r = counterfactual(site_key='connecting_ridge', start_utc='2026-11-14T00:00Z',
                       duration_hours=24, delay_hours=48)
    assert r['analysis_type']=='counterfactual_v0.4'
    assert r['scenarios']['original']['start_utc']=='2026-11-14T00:00Z'
    assert r['scenarios']['delayed']['start_utc']=='2026-11-16T00:00Z'
    assert r['scenarios']['delayed']['summary']['duration_hours']==24
    assert r['scenarios']['alternative_site_after_delay']['start_utc']==r['scenarios']['delayed']['start_utc']

def test_replanning_sun_and_earth_use_distinct_geometry():
    r = counterfactual()
    a, b = r['scenarios']['delayed'], r['scenarios']['alternative_site_after_delay']
    assert a['summary']['earth_visible_hours']==0.0
    assert b['summary']['earth_visible_hours']>a['summary']['earth_visible_hours']
    assert r['recommendation'] is None
    assert '6km' in r['confidence']

def test_energy_stress_monotonic_load_and_pv_area():
    r = counterfactual()
    vals={v['id']:v for v in r['delayed_site_energy_sensitivity']}
    assert vals['load_plus_20pct']['min_soc_pct'] <= vals['nominal']['min_soc_pct']
    assert vals['pv_area_minus_20pct']['min_soc_pct'] <= vals['nominal']['min_soc_pct']
    assert vals['combined_stress']['min_soc_pct'] <= vals['load_plus_20pct']['min_soc_pct']
    assert vals['combined_stress']['min_soc_pct'] <= vals['pv_area_minus_20pct']['min_soc_pct']

def test_replanning_reproducible():
    assert counterfactual() == counterfactual()

def test_start_window_outside_data_fails_without_fabrication():
    for start in ['2026-11-12T00:00Z','2026-11-17T00:00Z','2026-11-14T02:00Z']:
        with pytest.raises(ValueError): counterfactual(start_utc=start)

def test_incomplete_window_fails():
    with pytest.raises(ValueError, match='exceeds stored'):
        counterfactual(start_utc='2026-11-15T00:00Z',duration_hours=48,delay_hours=48)

def test_invalid_site_and_mode():
    with pytest.raises(ValueError):counterfactual(site_key='not_on_moon')
    with pytest.raises(ValueError):counterfactual(mode='magic-panel')

def test_api_contract_and_rejections():
    r=client.get('/api/replan')
    assert r.status_code==200
    assert r.json()['dataset_sha256']
    assert r.json()['scenarios']['delayed']['summary']['duration_hours']==24
    assert client.get('/api/replan?hours=72').status_code==422
    assert client.get('/api/replan?start=2026-11-01T00:00Z').status_code==422
    assert client.get('/api/replan?mode=impossible').status_code==422

def test_no_operational_radio_link_claim():
    r=client.get('/api/replan').json()
    assert 'not confirmed direct-to-Earth communication' in ' '.join(r['scientific_limits'])
    assert r['recommendation'] is None
    assert r['scenarios']['alternative_site_after_delay']['earth_clear_upper_bound_hours'] <= 24
