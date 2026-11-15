from pathlib import Path
from fastapi.testclient import TestClient
from api.index import app
from api.nasa_reference import load_dataset

client=TestClient(app)
ROOT=Path(__file__).resolve().parents[1]

def test_nasa_source_catalog():
    data=client.get('/api/science-sources')
    assert data.status_code==200
    names=[a['name'] for a in data.json()['sources']]
    for required in ('NASA LROC QuickMap','NASA Moon Trek','JPL Horizons','NASA Goddard LOLA','NAIF SPICE'):
        assert required in names

def test_spice_report_is_not_mission_certification():
    r=client.get('/api/spice-validation')
    assert r.status_code==200
    j=r.json()
    assert j['number_comparisons']==228
    assert sum(a['n'] for a in j['comparisons'])==228
    assert max(x['max_abs_az_deg'] for x in j['comparisons'])<0.00001
    assert 'not' in j['interpretation'].lower()

def test_real_moon_trek_wmts_and_quickmap_are_linked():
    html=client.get('/demo').text
    assert 'trek.nasa.gov/tiles/Moon/SP/' in html
    assert 'quickmap.lroc.asu.edu' in html
    assert 'WAC_POLE_ILL_PCT_SOUTH_100M' in html
    assert 'AVGVISIB_85S_060M_201608_EARTH_SP' in html
    assert 'not date-specific' in html

def test_source_reference_is_reproducible():
    dataset=load_dataset()
    assert len(dataset['sites'])==2
    for site in dataset['sites'].values():
        assert 'dem_sha256' in site and len(site['dem_sha256'])==64
        assert len(site['horizon_profile']['elevations_deg'])==72

def test_naif_reproduction_script_is_present():
    script=(ROOT/'tools'/'validate_spice.py').read_text()
    assert 'spkcpo' in script and 'sha256' in script
    assert (ROOT/'requirements-science.txt').exists()
