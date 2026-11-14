import pytest
from api.core import Site, horizons_params, mission_metrics, parse_horizons

SAMPLE = '''JPL Horizons synthetic test fixture — NOT real NASA data
$$SOE
 2026-Nov-14 00:00   135.0000   2.5000
 2026-Nov-14 06:00   180.0000  -0.5000
 2026-Nov-14 12:00   230.0000   1.0000
$$EOE
'''

def test_parse_horizons_fixture():
    records = parse_horizons(SAMPLE)
    assert len(records) == 3
    assert records[1]['el_deg'] == -0.5
    assert records[0]['utc'] == '2026-11-14T00:00:00Z'

def test_missing_ephemeris_fails_loudly():
    with pytest.raises(ValueError): parse_horizons('service unavailable')

def test_site_validation():
    with pytest.raises(ValueError): Site('bad', 91, 0)
    assert 'coord@301' in horizons_params('10', Site('pole', -89.5, 0), '2026-11-14', 3, 6)['CENTER']

def test_battery_energy_conservation():
    sun = [{'utc':f'2026-11-14T0{i}:00:00Z', 'az_deg':0, 'el_deg':-5} for i in range(4)]
    earth = [{'utc':r['utc'], 'az_deg':0, 'el_deg':4} for r in sun]
    out = mission_metrics(sun, earth, step_hours=1, load_w=1000, battery_kwh=2,
                          initial_soc=1, pv_area_m2=1, array_mode='horizontal')
    assert out['summary']['unserved_energy_kwh'] == 1
    assert out['summary']['min_soc_pct'] == 0
    assert out['summary']['sun_visible_pct'] == 0
    assert out['summary']['earth_visible_pct'] == 100

def test_tracking_panel_no_negative_generation():
    sun = parse_horizons(SAMPLE)
    earth = [{**r, 'el_deg':10} for r in sun]
    out = mission_metrics(sun, earth, 6, array_mode='tracking')
    assert all(r['pv_w'] >= 0 for r in out['samples'])
    assert out['samples'][1]['pv_w'] == 0


def test_fastapi_end_to_end_without_network(monkeypatch):
    from fastapi.testclient import TestClient
    from api.index import app
    from api import index
    def mock_ephem(body, site, start, days, step_hours):
        rows = parse_horizons(SAMPLE)
        return rows if body == '10' else [{**r, 'el_deg': 15.0} for r in rows]
    monkeypatch.setattr(index, 'get_ephemeris', mock_ephem)
    r = TestClient(app).get('/api/mission?lat=-89.5&lon=0&start=2026-11-14&days=3&step=6')
    assert r.status_code == 200
    payload = r.json()
    assert payload['summary']['n_samples'] == 3
    assert payload['model'].startswith('geometric horizon only')
    assert payload['source'].startswith('JPL Horizons API')
