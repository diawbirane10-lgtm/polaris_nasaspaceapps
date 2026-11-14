"""Multi-view accessibility, routing affordances and electrical integration checks."""
from pathlib import Path
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
from api.index import app

ROOT = Path(__file__).resolve().parent.parent
CLIENT = TestClient(app)


def test_eight_explorable_views_and_keyboard_ready_navigation():
    r = CLIENT.get('/')
    assert r.status_code == 200
    dom = BeautifulSoup(r.text, 'html.parser')
    routes = ['mission', 'sky', 'scenarios', 'power', 'atlas', 'evidence', 'copilot', 'review']
    assert [a.get('data-nav') for a in dom.select('[data-nav]')] == routes
    assert all(dom.select_one('[data-page="'+p+'"]') is not None for p in routes)
    assert dom.select_one('a.skip-link')['href'] == '#contentStart'
    assert dom.select_one('#nextPage') is not None
    assert 'prefers-reduced-motion' in r.text


def test_power_controls_are_labeled_and_model_backed():
    dom = BeautifulSoup(CLIENT.get('/').text,'html.parser')
    for cid in ['powerArea','powerLoad','powerBattery','powerMode']:
        assert dom.select_one(f'label[for="{cid}"]') is not None
        assert dom.select_one('#'+cid) is not None
    response1=CLIENT.get('/api/nasa-reference/connecting_ridge',params={'area':16,'load':400,'battery':20,'mode':'horizontal'})
    response2=CLIENT.get('/api/nasa-reference/connecting_ridge',params={'area':16,'load':1500,'battery':20,'mode':'horizontal'})
    assert response1.status_code == response2.status_code == 200
    assert response2.json()['summary']['unserved_energy_kwh'] > response1.json()['summary']['unserved_energy_kwh']
    assert response1.json()['summary']['duration_hours'] == 96


def test_local_open_source_ui_assets_and_attribution():
    icons = ROOT / 'public' / 'icons'
    assert len(list(icons.glob('*.svg'))) >= 6
    assert 'Lucide' in (icons/'LICENSE').read_text()
    assert 'ISC' in (icons/'LICENSE').read_text()
    assert (ROOT/'docs'/'DEMO_30_SECONDS.md').exists()


def test_invalid_scenario_rejected_not_autocorrected():
    r=CLIENT.get('/api/replan',params={'site':'connecting_ridge','start':'2026-11-14T00:00Z','hours':24,'delay':0})
    assert r.status_code == 422


def test_static_icon_routes_use_correct_vercel_rewrite():
    from json import loads
    v=loads((ROOT/'vercel.json').read_text())
    assert {'src':'/assets/(.*)','dest':'/public/$1'} in v['routes']
    for key in ['rocket','orbit','map','battery-charging','shield-check','git-compare']:
        assert (ROOT/'public'/'icons'/(key+'.svg')).is_file()
