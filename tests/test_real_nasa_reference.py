"""Regression tests for the genuine NASA data pack, distinct from synthetic unit tests."""
from fastapi.testclient import TestClient
from api.index import app
from api.nasa_reference import analyze_reference,load_dataset

client=TestClient(app)

def test_two_real_sites_available():
    r=client.get('/api/nasa-sites')
    assert r.status_code==200
    assert {x['key'] for x in r.json()['sites']}=={'connecting_ridge','shackleton_rim'}

def test_ephemerides_dates_and_horizon():
    data=load_dataset()
    for site in data['sites'].values():
        assert len(site['horizon_profile']['elevations_deg'])==72
        assert site['dem_sha256'] and len(site['dem_sha256'])==64
        assert site['ephemeris']['sun'][0]['utc']=='2026-11-14T00:00Z'
        assert site['ephemeris']['sun'][-1]['utc']=='2026-11-18T00:00Z'
        assert [x['utc'] for x in site['ephemeris']['sun']]==[x['utc'] for x in site['ephemeris']['earth']]

def test_real_terrain_affects_horizon():
    for site_id in ('connecting_ridge','shackleton_rim'):
        a=analyze_reference(site_id)
        assert a['summary']['horizon_model']=='DEM-profile'
        assert a['summary']['duration_hours']==96
        assert a['summary']['n_samples']==17
        assert a['source_type']=='nasa_real_reference'
        assert any(abs(x['sun_horizon_deg'])>0.2 for x in a['samples'])
        assert a['data_provenance']['dem_sha256']
        assert a['assumptions']['no_distant_terrain']

def test_cannot_claim_ground_truth_landing_site():
    r=client.get('/api/nasa-reference/shackleton_rim')
    assert r.status_code==200
    assert 'not certified' in ' '.join(r.json()['limitations']).lower()

def test_invalid_site_rejected():
    assert client.get('/api/nasa-reference/unknown').status_code==404

def test_pv_params_only_change_model_not_nasa_data():
    a=client.get('/api/nasa-reference/connecting_ridge?load=100').json()
    b=client.get('/api/nasa-reference/connecting_ridge?load=500').json()
    assert a['samples'][0]['sun_el']==b['samples'][0]['sun_el']
    assert a['samples'][0]['soc']>=b['samples'][0]['soc']
    assert a['summary']['min_soc_pct']>=b['summary']['min_soc_pct']
