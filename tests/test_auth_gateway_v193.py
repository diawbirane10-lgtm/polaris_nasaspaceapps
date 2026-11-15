"""NASA public prototype: eight scientific views, no login or private API exposure."""
from pathlib import Path
from fastapi.testclient import TestClient
from api.index import app

client=TestClient(app)
ROOT=Path(__file__).resolve().parents[1]

def test_public_routes_open_same_mission_control():
    for path in ("/","/demo","/workspace","/admin"):
        response=client.get(path,follow_redirects=False)
        assert response.status_code==200
        assert 'data-nav="copilot"' in response.text
        assert 'data-nav="review"' in response.text
        assert 'id="loginForm"' not in response.text

def test_no_credentials_or_provisioning_endpoints():
    for path in ('/api/private/whoami','/api/registration/status','/api/admin/requests','/api/admin/visits','/api/workspace-config'):
        assert client.get(path).status_code==404
    for path in ('/api/private/continue','/api/admin/decision'):
        assert client.post(path,json={}).status_code==404

def test_private_routes_are_not_mounted():
    paths={r.path for r in app.routes}
    assert '/api/admin/decision' not in paths
    assert '/api/private/continue' not in paths
    assert '/api/registration/status' not in paths

def test_public_scripts_do_not_route_to_login():
    page=(ROOT/'public'/'index.html').read_text(encoding='utf-8')
    assert 'SECURE WORKSPACE ↗' not in page
    assert 'id="copilotForm"' in page
    assert 'id="loginForm"' not in page
    assert 'data-nav="mission"' in page

def test_vercel_routes_keep_admin_and_workspace_on_api():
    import json
    routes=json.loads((ROOT/'vercel.json').read_text())['routes']
    match=next(r for r in routes if r['src'].startswith('/(api/.*|admin'))
    assert 'workspace' in match['src']
    assert match['dest']=='/api/index.py'
