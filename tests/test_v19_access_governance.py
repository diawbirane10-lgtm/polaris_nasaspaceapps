"""POLARIS account-approval regression checks; no production identities are used."""
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from api.index import app
from api import admin, registration
from api.security import WorkspaceIdentity
import pytest
from fastapi import HTTPException

client=TestClient(app,base_url='https://testserver')
ROOT=Path(__file__).resolve().parents[1]


def test_first_screen_contains_registration_and_legal_consent():
    r=client.get('/')
    assert r.status_code==200
    for entry in ('id="loginForm"','id="registerForm"','id="termsAccept"','id="pendingSection"',
                  'id="givenName"','id="familyName"','id="employeeId"'):
        assert entry in r.text
    assert '/admin' not in r.text.lower()
    assert client.get('/terms').status_code==200


def test_admin_documents_are_not_published_as_static_assets():
    for filename in ('/assets/operator_console.html','/operator_console.html','/admin_console.html'):
        assert client.get(filename).status_code in (404,405)
    assert '/admin' not in (ROOT/'public'/'workspace.js').read_text().lower()
    assert '/admin' not in (ROOT/'public'/'workspace.html').read_text().lower()


def test_admin_route_returns_not_found_without_cookie():
    assert client.get('/admin',follow_redirects=False).status_code==303
    for p in ('/api/admin/requests','/api/admin/visits'):
        assert client.get(p).status_code==404
    assert client.post('/api/admin/decision',headers={'origin':'https://testserver'},json={
        'request_id':str(uuid4()),'decision':'approved'}).status_code==404


def test_registration_status_requires_valid_session():
    assert client.get('/api/registration/status').status_code in (401,503)
    assert client.get('/api/registration/status').status_code in (401,503)


def test_admin_origin_check_rejects_cross_site():
    with pytest.raises(HTTPException) as exc:
        admin._same_origin(type('R',(),{'headers':{'origin':'https://attacker.example','host':'testserver','sec-fetch-site':'cross-site'}})())
    assert exc.value.status_code==404


def test_bearer_only_granted_after_verified_administrator(monkeypatch):
    user=WorkspaceIdentity(str(uuid4()),'Test Operator','test-token','engineer')
    # Depends injection inspects verified identity, and non-admin must not get any privileged redirect.
    app.dependency_overrides[admin.require_workspace_identity]=lambda:user
    try:
        r=client.post('/api/private/continue')
        assert r.status_code==200 and r.json()['next'] is None
        assert 'set-cookie' not in r.headers
    finally:
        app.dependency_overrides.clear()


def test_admin_backend_responses_never_include_auth_identifiers(monkeypatch):
    identity=WorkspaceIdentity(str(uuid4()),'Verified Test','admin-token','administrator')
    monkeypatch.setattr(admin,'_admin_identity',lambda req:identity)
    monkeypatch.setattr(admin,'_query',lambda ident,resource,**kw: ([
        {'id':str(uuid4()),'user_id':str(uuid4()),'first_name':'First','last_name':'Last',
         'staff_id':'MTR123','status':'pending','created_at':'2026-11-15T00:00:00Z',
         'email':'hidden@example.org','password_hash':'NEVER','refresh_token':'SECRET'}]
        if resource=='access_requests' else []))
    r=client.get('/api/admin/requests')
    assert r.status_code==200
    assert r.json()['requests'][0]['employee_id']=='MTR123'
    for forbidden in ('hidden@example.org','NEVER','SECRET','password_hash','refresh_token','user_id'):
        assert forbidden not in r.text


def test_admin_route_requires_current_role_each_request(monkeypatch):
    monkeypatch.setattr(admin,'_verify_claims',lambda token,url:{'sub':str(uuid4())})
    monkeypatch.setattr(admin,'_settings',lambda:('https://example.supabase.co','public',''))
    monkeypatch.setattr(admin,'_verified_profile',lambda url,key,token,user_id:{'role':'engineer','verified_name':'Example'})
    class R: cookies={admin.COOKIE:'dummy'}
    with pytest.raises(HTTPException) as exc:admin._admin_identity(R())
    assert exc.value.status_code==404


def test_sql_has_default_denial_and_server_approval():
    sql=(ROOT/'supabase/sql/20261115_existing_schema_hardening.sql').read_text()
    assert 'GRANT UPDATE(status) ON public.access_requests TO authenticated' in sql
    assert 'is_active_admin()' in sql
    assert 'email_confirmed_at' in sql
    assert 'OLD.status' in sql


def test_approved_administrator_receives_temporary_secure_cookie(monkeypatch):
    from datetime import datetime, timezone
    identity=WorkspaceIdentity(str(uuid4()),'Verified Reviewer','signed-token','administrator')
    app.dependency_overrides[admin.require_workspace_identity]=lambda:identity
    monkeypatch.setattr(admin,'_settings',lambda:('https://example.supabase.co','publishable',''))
    monkeypatch.setattr(admin,'_verify_claims',lambda token,url:{'sub':identity.user_id,
        'exp':datetime.now(timezone.utc).timestamp()+500})
    try:
        r=client.post('/api/private/continue')
        assert r.status_code==200 and r.json()['next']=='/admin'
        cookie=r.headers.get('set-cookie','').lower()
        assert 'httponly' in cookie and 'secure' in cookie and 'samesite=strict' in cookie
        assert 'max-age=' in cookie
    finally:app.dependency_overrides.clear()


def test_approved_administrator_can_load_nonpublic_console(monkeypatch):
    identity=WorkspaceIdentity(str(uuid4()),'Verified Reviewer','token','administrator')
    monkeypatch.setattr(admin,'_admin_identity',lambda request:identity)
    r=client.get('/admin')
    assert r.status_code==200
    assert 'Access & activity overview.' in r.text
    assert 'MATRICULE' in r.text
    assert r.headers.get('cache-control','').startswith('private, no-store')
    assert 'noindex' in r.headers.get('x-robots-tag','')


def test_approval_uses_restricted_status_update_and_uuid(monkeypatch):
    identity=WorkspaceIdentity(str(uuid4()),'Verified Reviewer','secret','administrator')
    reqid=str(uuid4())
    monkeypatch.setattr(admin,'_admin_identity',lambda request:identity)
    monkeypatch.setattr(admin,'_settings',lambda:('https://example.supabase.co','publishable',''))
    calls=[]
    class Resp:
        status_code=200
        content=b'[{}]'
        def json(self):return [{'status':'approved'}]
    def fake_patch(url,**kwargs):
        calls.append((url,kwargs));return Resp()
    monkeypatch.setattr(admin.requests,'patch',fake_patch)
    r=client.post('/api/admin/decision',headers={'origin':'https://testserver'},json={
        'request_id':reqid,'decision':'approved'})
    assert r.status_code==200 and r.json()['status']=='approved'
    assert len(calls)==1
    assert calls[0][0].endswith('/rest/v1/access_requests')
    assert calls[0][1]['params']=={'user_id':'eq.'+reqid,'status':'eq.pending'}
    assert calls[0][1]['json']=={'status':'approved'}


def test_csrf_blocks_an_outside_decision_even_with_mocked_admin(monkeypatch):
    identity=WorkspaceIdentity(str(uuid4()),'Verified Reviewer','token','administrator')
    monkeypatch.setattr(admin,'_admin_identity',lambda request:identity)
    r=client.post('/api/admin/decision',headers={'origin':'https://evil.example'},json={
        'request_id':str(uuid4()),'decision':'approved'})
    assert r.status_code==404
