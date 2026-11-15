"""v1.9 regression: retired public-admin links stay inaccessible.

These tests intentionally replace pre-v1.9 tests that expected a public
administration page, which is now a prohibited security regression.
"""
from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)


def test_public_auth_entry_and_public_demo_exist():
    login = client.get("/workspace")
    assert login.status_code == 200
    assert 'id="loginForm"' in login.text
    assert 'id="registerForm"' in login.text
    assert "/admin" not in login.text
    assert client.get("/demo").status_code == 200
    assert client.get("/terms").status_code == 200


def test_administration_undiscoverable_without_verified_session():
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/workspace"
    for route in ("/api/admin/requests", "/api/admin/visits"):
        response = client.get(route)
        assert response.status_code == 404, (route, response.status_code)
    assert client.post(
        "/api/admin/decision",
        json={"request_id": "00000000-0000-0000-0000-000000000001",
              "decision": "approved"},
    ).status_code == 404


def test_request_status_rejects_unauthenticated_users():
    assert client.get("/api/registration/status").status_code == 401


def test_supabase_registration_is_not_recreated_by_an_untrusted_api():
    for route in ("/api/access/status", "/api/admin/sessions"):
        assert client.get(route).status_code == 404


def test_public_homepage_is_scientific_demo_without_credentials():
    landing = client.get("/")
    assert landing.status_code == 200
    assert 'id="loginForm"' not in landing.text
    assert 'id="registerForm"' not in landing.text
    assert 'data-nav="mission"' in landing.text
