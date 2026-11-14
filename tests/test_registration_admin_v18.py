"""Admission and administration tests — never require real passwords or users."""
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from api.index import app
from api import access_admin
from api.security import WorkspaceIdentity, require_workspace_identity

ROOT=Path(__file__).resolve().parent.parent
cli=TestClient(app)


def test_auth_and_admin_pages_are_real_pages():
    for page,text in [('/admin','Accreditation queue'),('/terms','Terms'),('/','Create account'),('/workspace','Create account'),('/demo','POLARIS')]:
        r=cli.get(page)
        assert r.status_code==200,(page,r.text[:160])
        assert text in r.text


def test_signup_contains_consented_terms_and_name_id():
    content=(ROOT/'public/workspace.html').read_text()
    for item in ['id="signupForm"','id="firstName"','id="lastName"','id="staffId"',
                 'id="acceptTerms"','id="pendingSection"','id="approvalBadge"']:
        assert item in content


def test_registration_signup_is_safely_restricted_to_auth():
    assert cli.get('/api/access/status').status_code in (401,503)
    assert cli.get('/api/admin/requests').status_code in (401,503)
    assert cli.get('/api/admin/sessions').status_code in (401,503)


def test_admin_requires_provisioned_role_and_verified_mfa():
    engineer=WorkspaceIdentity(str(uuid4()),'Engineer Test','signed.jwt','engineer')
    app.dependency_overrides[require_workspace_identity]=lambda:engineer
    try:
        assert cli.get('/api/admin/requests').status_code==403
        assert cli.get('/api/admin/sessions').status_code==403
        assert cli.post('/api/admin/requests/'+str(uuid4())+'/decision',json={'status':'approved'}).status_code==403
    finally:app.dependency_overrides.clear()


def test_admin_queue_exposes_name_staff_and_time_not_login_credentials(monkeypatch):
    adm=WorkspaceIdentity(str(uuid4()),'Admin Verified','signed.jwt','administrator')
    app.dependency_overrides[require_workspace_identity]=lambda:adm
    uid=str(uuid4())
    monkeypatch.setattr(access_admin,'_db',lambda *args,**kwargs: [{
        'user_id':uid,'first_name':'Maria','last_name':'Engineer','staff_id':'ENG-211',
        'status':'pending','created_at':'2026-11-14T16:00:00Z','reviewed_at':None}])
    try:
        r=cli.get('/api/admin/requests');assert r.status_code==200
        assert r.json()['requests'][0]['staff_id']=='ENG-211'
        assert 'password' not in r.text and 'access_token' not in r.text
    finally:app.dependency_overrides.clear()


def test_status_only_reads_active_signed_in_user(monkeypatch):
    uid=str(uuid4())
    app.dependency_overrides[access_admin._user_session]=lambda:{'user_id':uid,'token':'valid.token','aal':'aal1'}
    def fake(method,resource,token,**k):
        assert method=='GET' and resource=='access_requests' and k['params']['user_id']=='eq.'+uid
        return [{'first_name':'Sofia','last_name':'Robot','staff_id':'ROB-44','status':'pending','created_at':'2026-11-14T15:00:00Z'}]
    monkeypatch.setattr(access_admin,'_db',fake)
    try:
        r=cli.get('/api/access/status');assert r.status_code==200
        assert r.json()['status']=='pending' and r.json()['mfa_required_for_workspace'] is True
    finally:app.dependency_overrides.clear()


@pytest.mark.parametrize('status,code',[('admin',422),('pending',422),('approved',200),('rejected',200)])
def test_admin_decision_is_constrained(monkeypatch,status,code):
    adm=WorkspaceIdentity(str(uuid4()),'Verified Admin','valid.token','administrator')
    app.dependency_overrides[require_workspace_identity]=lambda:adm
    def fake(method,resource,token,**opts):
        assert method=='PATCH' and resource=='access_requests'
        assert opts['params']['status']=='eq.pending' and opts['body']['status'] in ('approved','rejected')
        return [{'status':opts['body']['status']}]
    monkeypatch.setattr(access_admin,'_db',fake)
    try:
        r=cli.post('/api/admin/requests/'+str(uuid4())+'/decision',json={'status':status})
        assert r.status_code==code
    finally:app.dependency_overrides.clear()


def test_invalid_admin_target_rejected(monkeypatch):
    adm=WorkspaceIdentity(str(uuid4()),'Verified Admin','valid.token','administrator')
    app.dependency_overrides[require_workspace_identity]=lambda:adm
    try:
        assert cli.post('/api/admin/requests/not-uuid/decision',json={'status':'approved'}).status_code==422
    finally:app.dependency_overrides.clear()


def test_authenticated_session_history_redacts_sensitive_fields(monkeypatch):
    adm=WorkspaceIdentity(str(uuid4()),'Verified Admin','valid.token','administrator')
    app.dependency_overrides[require_workspace_identity]=lambda:adm
    monkeypatch.setattr(access_admin,'_db',lambda *args,**kwargs:[{
        'first_name':'John','last_name':'Engineer','staff_id':'EE-101','account_status':'approved',
        'session_created_at':'2026-11-14T17:00:00Z','password':'DO-NOT-RETURN','email':'hidden@example.org',
        'refresh_token':'SECRET-DO-NOT-RETURN'}])
    try:
        r=cli.get('/api/admin/sessions');assert r.status_code==200
        assert len(r.json()['sessions'])==1
        for secret in ('password','hidden@example.org','refresh_token','SECRET-DO-NOT-RETURN'):
            assert secret not in r.text
    finally:app.dependency_overrides.clear()


def test_sql_security_contract():
    sql=(ROOT/'supabase/sql/access_approval_and_admin_v18.sql').read_text()
    for must in ('ENABLE ROW LEVEL SECURITY','auth.sessions','is_active_admin','BEFORE UPDATE',
                 'provision_approved_account','accepted_terms','terms_version',
                 'REVOKE ALL ON public.access_requests','GRANT UPDATE(status)'):
        assert must in sql
    assert "GRANT INSERT ON public.access_requests TO authenticated" not in sql


def test_browser_code_supports_pending_polling_and_admin_refusal():
    js=(ROOT/'public/workspace.js').read_text()
    adminjs=(ROOT/'public/admin.js').read_text()
    assert 'signupForm' in js and 'accessStatus()' in js and 'approvalTimer' in js
    assert 'person.role!==\'administrator\'' in adminjs
    assert 'sessionStorage' not in adminjs and 'localStorage' not in adminjs
