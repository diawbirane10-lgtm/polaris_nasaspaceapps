"""ECC-inspired operational UI regression checks for NASA prototype.

Static invariants complement (but never replace) real browser tests.
"""
from pathlib import Path
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
from api.index import app

ROOT=Path(__file__).resolve().parents[1]
client=TestClient(app)

def test_public_mission_control_does_not_offer_retired_login():
    html=client.get('/').text
    assert 'SECURE SIGN IN' not in html
    assert 'SECURE WORKSPACE' not in html
    assert 'id="copilotForm"' in html
    assert 'id="reviewForm"' in html
    for route in ('mission','sky','scenarios','power','atlas','evidence','copilot','review'):
        assert f'data-nav="{route}"' in html

def test_all_nav_destinations_have_content_sections():
    soup=BeautifulSoup(client.get('/').text,'html.parser')
    for anchor in soup.select('.railnav [data-nav]'):
        route=anchor['data-nav']
        assert anchor.get('href')=='#/'+route
        assert soup.select_one('[data-page="'+route+'"]') is not None

def test_feedback_is_visible_and_accessible_to_screen_readers():
    soup=BeautifulSoup(client.get('/').text,'html.parser')
    assert soup.select_one('#copilotFeedback[role="status"][aria-live="polite"]') is not None
    assert soup.select_one('#reviewStatus[role="status"][aria-live="polite"]') is not None
    assert soup.select_one('#coReportStatus[role="status"][aria-live="polite"]') is not None
    for name in ('copilotSubmit','qRun','powerRun','reviewCompute'):
        assert soup.select_one('#'+name) is not None
    page=(ROOT/'public'/'polaris-app.js').read_text(encoding='utf-8')
    for phrase in ('Calculating NASA-grounded mission response','Response complete','Review failed:',
                   'COMPUTING SCENARIOS','RECOMPUTING POWER','Power calculation unavailable'):
        assert phrase in page

def test_mobile_navigation_shows_all_eight_sections():
    css=(ROOT/'public'/'sport-mission.css').read_text(encoding='utf-8')
    assert 'grid-template-columns:repeat(4,minmax(0,1fr))' in css
    assert 'grid-template-rows:repeat(2,50px)' in css
    assert 'prefers-reduced-motion' in css

def test_demo_engine_remains_public():
    assert client.get('/api/health').status_code==200
    assert client.get('/api/copilot/status').status_code==200
    for old in ('/api/registration/status','/api/admin/requests','/api/private/whoami'):
        assert client.get(old).status_code==404
