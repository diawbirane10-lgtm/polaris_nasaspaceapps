"""Submission-ready public routing and disabled authentication endpoints."""
from pathlib import Path
import json
from fastapi.testclient import TestClient
from api.index import app

ROOT=Path(__file__).resolve().parents[1]
client=TestClient(app)

def test_public_scientific_demo():
    for path in ('/','/demo','/workspace','/admin'):
        response=client.get(path,follow_redirects=False)
        assert response.status_code==200
        assert 'data-nav="copilot"' in response.text
        assert 'data-nav="review"' in response.text
        assert 'id="loginForm"' not in response.text

def test_privileged_endpoints_unmounted():
    routes={r.path for r in app.routes}
    assert not any(p.startswith('/api/private/') or p.startswith('/api/admin/') or p.startswith('/api/registration/') for p in routes)
    for p in ('/api/private/whoami','/api/registration/status','/api/admin/requests','/api/workspace-config'):
        assert client.get(p).status_code==404

def test_vercel_home_and_demo_are_distinct_public_pages():
    routes=json.loads((ROOT/'vercel.json').read_text())['routes']
    root=next(r for r in routes if r['src']=='/' and 'dest' in r)
    assert root['dest']=='/public/project-home.html'
    assert next(r for r in routes if r['src']=='/demo')['dest']=='/public/index.html'
    assert next(r for r in routes if 'admin|workspace' in r['src'])['dest']=='/public/index.html'
    home=(ROOT/'public'/'project-home.html').read_text()
    assert 'href="/submission-slides.html"' in home
    assert 'href="/demo"' in home

def test_jury_slides_have_exactly_seven_slides():
    html=(ROOT/'public'/'submission-slides.html').read_text()
    assert html.count('data-slide="')==7
    assert '<script src="/assets/submission-slides.js" defer>' in html
