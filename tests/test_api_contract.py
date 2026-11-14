"""Contract tests using synthetic input; no live JPL validation claims."""
import pytest
from fastapi.testclient import TestClient
from requests.exceptions import ConnectionError as RequestsConnectionError

from api.index import app
from api import index
from api.core import parse_horizons

client = TestClient(app)

FIXTURE = '''SYNTHETIC JPL-style observer rows. NOT a NASA measurement.
$$SOE
 2026-Nov-14 00:00   350.0000   3.0000
 2026-Nov-14 06:00   359.0000  -2.0000
 2026-Nov-14 12:00    8.0000   1.0000
$$EOE
'''


def test_health_and_index_routes_are_live():
    h = client.get('/api/health')
    assert h.status_code == 200
    assert h.json()['status'] == 'ok'
    assert 'unvalidated' in h.json()['ephemerides']
    r = client.get('/')
    assert r.status_code == 200
    assert 'POLARIS' in r.text


def test_api_contract_with_synthetic_ephemerides(monkeypatch):
    def synthetic(body, site, start, days, step_hours):
        rows = parse_horizons(FIXTURE)
        return rows if body == '10' else [{**r, 'el_deg': 2.0} for r in rows]
    monkeypatch.setattr(index, 'get_ephemeris', synthetic)
    r = client.get('/api/mission?lat=-89.5&lon=203.8&start=2026-11-14&days=2&step=6')
    assert r.status_code == 200
    out = r.json()
    assert set(['summary', 'samples', 'site', 'assumptions', 'model', 'source']) <= set(out)
    assert out['summary']['duration_hours'] == 12
    assert out['summary']['horizon_model'] == 'geometric-zero-degree'
    assert out['assumptions']['no_terrain'] is True
    assert out['assumptions']['no_radio_link_budget'] is True


def test_upstream_failure_returns_503_not_made_up_results(monkeypatch):
    def offline(*args, **kwargs):
        raise RequestsConnectionError('Synthetic simulated outage')
    monkeypatch.setattr(index, 'get_ephemeris', offline)
    result = client.get('/api/mission?start=2026-11-14')
    assert result.status_code == 503
    assert 'unavailable' in result.json()['detail']


@pytest.mark.parametrize('query', [
    'lat=-75', 'lon=361', 'days=0', 'step=5', 'start=invalid',
    'area=0', 'battery=-1', 'mode=rocket',
])
def test_invalid_query_rejected_cleanly_without_jpl(monkeypatch, query):
    # Should not require a real upstream service to test validation.
    def synthetic(body, site, start, days, step_hours):
        return parse_horizons(FIXTURE)
    monkeypatch.setattr(index, 'get_ephemeris', synthetic)
    response = client.get('/api/mission?' + query)
    assert response.status_code == 422, (query, response.status_code, response.text)
