"""Minimal pre-auth gateway; private workflow remains inside sign-in."""
from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)

def test_gateway_has_only_identity_actions():
    r=client.get('/workspace')
    assert r.status_code == 200
    html=r.text
    assert 'id="loginForm"' in html and 'id="registerForm"' in html
    assert 'id="showRegister"' in html and 'id="backToSignIn"' in html
    assert 'data-screen="loginSection"' in html
    for old in ('Explore public NASA demo', 'Every decision<br>has an author', 'Your engineering record', 'href="/demo"', 'class="panel scene"'):
        assert old not in html
    assert 'href="/assets/auth-gateway.css"' in html

def test_auth_gateway_css_and_javascript():
    css=client.get('/assets/auth-gateway.css')
    js=client.get('/assets/workspace.js')
    assert css.status_code==200 and js.status_code==200
    assert '--blue:#145dff' in css.text and 'display:none' in css.text
    assert 'document.body.dataset.screen=name' in js.text
    assert "view('loginSection');try{" in js.text

def test_public_demo_still_accessible_and_admin_not_linked():
    assert client.get('/demo').status_code==200
    assert 'href="/admin"' not in client.get('/workspace').text
    assert client.get('/admin',follow_redirects=False).status_code==303
