from fastapi.testclient import TestClient
from api.index import app
c=TestClient(app)

def test_skyline_endpoint():
 r=c.get('/api/skyline/shackleton_rim')
 assert r.status_code==200
 d=r.json()
 assert len(d['profile']['elevations_deg'])==72
 assert d['radius_km']==6
 assert d['source']['dem_url'].startswith('https://')

def test_skyline_missing():
 assert c.get('/api/skyline/not_an_observation').status_code==404

def test_science_audit():
 r=c.get('/api/science-audit')
 assert r.status_code==200
 assert r.json()['results'][1]['one_hour_local_earth_clear_h']==21
