"""Offline security regression suite. Does NOT substitute for live RLS penetration testing."""
import time
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from pypdf import PdfReader

from api.index import app
import api.security as security

client = TestClient(app)
BASE = {'question':'Study energy','site':'connecting_ridge','start':'2026-11-14T00:00Z',
        'duration_hours':24,'delay_hours':48,'pv_area_m2':16,'load_w':700,
        'battery_kwh':20,'panel_mode':'horizontal','min_soc_pct':35,
        'min_local_earth_hours':6,'max_local_earth_gap_hours':24,
        'focus':'electrical','selected_scenarios':['original']}
ID=str(uuid4())
private_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)

def token(aal='aal2',role='authenticated',sub=ID,expire=1800,issuer='https://polaris-test.supabase.co/auth/v1'):
    now=int(time.time())
    claims={'sub':sub,'role':role,'aud':'authenticated','iss':issuer,
            'aal':aal,'iat':now,'exp':now+expire,'is_anonymous':False}
    return jwt.encode(claims,private_key,algorithm='RS256',headers={'kid':'polaris-test-key'})

class FakeResponse:
    def __init__(self,body,code=200):self.body=body;self.code=code
    def raise_for_status(self):
        if self.code!=200:raise __import__('requests').HTTPError(str(self.code))
    def json(self):return self.body


def setup(monkeypatch,profile_user=ID,profile_name='Engineer Verified Example',profile_active=True,audit_ok=True):
    monkeypatch.setenv('POLARIS_SUPABASE_URL','https://polaris-test.supabase.co')
    monkeypatch.setenv('POLARIS_SUPABASE_PUBLISHABLE_KEY','test-publishable')
    monkeypatch.setenv('POLARIS_SUPABASE_SERVER_KEY','test-server-secret')
    monkeypatch.setattr(security,'_jwks_client',lambda url: SimpleNamespace(get_signing_key_from_jwt=lambda jwt_value:SimpleNamespace(key=private_key.public_key())))
    def get(url,**kwargs):
        assert kwargs['params']['user_id']=='eq.'+ID
        assert kwargs['headers']['Authorization'].startswith('Bearer ')
        return FakeResponse([{'user_id':profile_user,'verified_name':profile_name,'active':profile_active,'role':'engineer'}])
    def post(url,**kwargs):
        assert 'engineering_audit' in url
        assert kwargs['headers']['apikey']=='test-server-secret'
        assert kwargs['json']['actor_user_id']==ID
        return FakeResponse([{'id':str(uuid4())}] if audit_ok else [],200 if audit_ok else 500)
    monkeypatch.setattr(security.requests,'get',get)
    monkeypatch.setattr(security.requests,'post',post)

def test_private_endpoints_closed_without_configuration(monkeypatch):
    for key in ('POLARIS_SUPABASE_URL','POLARIS_SUPABASE_PUBLISHABLE_KEY','POLARIS_SUPABASE_SERVER_KEY'):
        monkeypatch.delenv(key,raising=False)
    r=client.get('/api/private/whoami')
    assert r.status_code==503
    assert client.get('/').status_code==200  # public NASA demo still works

def test_password_only_cannot_access_workspace(monkeypatch):
    setup(monkeypatch)
    r=client.get('/api/private/whoami',headers={'Authorization':'Bearer '+token(aal='aal1')})
    assert r.status_code==403
    assert 'Multi-factor' in r.text

def test_expired_wrong_issuer_and_anonymous_rejected(monkeypatch):
    setup(monkeypatch)
    for t in (token(expire=-90),token(issuer='https://other.supabase.co/auth/v1'), token(role='anon')):
        assert client.get('/api/private/whoami',headers={'Authorization':'Bearer '+t}).status_code in (401,403)

def test_profile_identity_mismatch_denies_access(monkeypatch):
    setup(monkeypatch,profile_user=str(uuid4()))
    r=client.get('/api/private/whoami',headers={'Authorization':'Bearer '+token()})
    assert r.status_code==403

def test_profile_inactive_denied(monkeypatch):
    setup(monkeypatch,profile_active=False)
    assert client.get('/api/private/whoami',headers={'Authorization':'Bearer '+token()}).status_code==403

def test_authoritative_legal_name_in_computed_review_and_pdf(monkeypatch):
    setup(monkeypatch)
    headers={'Authorization':'Bearer '+token()}
    r=client.get('/api/private/whoami',headers=headers)
    assert r.status_code==200,r.text
    assert r.json()['name']=='Engineer Verified Example'
    report=client.post('/api/private/mission-review',headers=headers,json={**BASE,'prepared_by':'Fake Director'})
    assert report.status_code==200,report.text
    assert report.json()['prepared_by']=='Engineer Verified Example'
    assert report.json()['prepared_by_id']==ID
    pdf=client.post('/api/private/mission-decision/brief.pdf',headers=headers,json={**BASE,'prepared_by':'Fake Director'})
    assert pdf.status_code==200,pdf.text[:250] if pdf.status_code!=200 else ''
    text='\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(pdf.content)).pages)
    assert 'Engineer Verified Example' in text
    assert 'Fake Director' not in text
    assert 'Audit:' in text
    latex=client.post('/api/private/mission-decision/brief.tex',headers=headers,json=BASE)
    assert latex.status_code==200 and 'Engineer Verified Example' in latex.text

def test_audit_failure_stops_private_export(monkeypatch):
    setup(monkeypatch,audit_ok=False)
    r=client.post('/api/private/mission-decision/brief.pdf',headers={'Authorization':'Bearer '+token()},json=BASE)
    assert r.status_code==503
    assert 'audit' in r.text.lower()

def test_no_authenticated_identity_in_public_demo_pdf():
    r=client.post('/api/mission-decision/brief.pdf',json=BASE)
    assert r.status_code==200
    text='\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(r.content)).pages)
    assert 'Public demonstration (no verified author)' in text

def test_db_schema_denies_unverified_users_and_cross_owner_links():
    from pathlib import Path
    schema=Path('supabase/sql/secure_workspace_schema.sql').read_text()
    for entity in ('operator_profiles','mission_plans','simulation_runs','report_records','engineering_audit'):
        assert f'ALTER TABLE public.{entity} ENABLE ROW LEVEL SECURITY' in schema
    assert 'FOREIGN KEY(mission_id,owner_id)' in schema
    assert 'FOREIGN KEY(run_id,owner_id)' in schema
    assert 'CREATE POLICY mission_insert_own' in schema
    assert "(auth.jwt()->>'aal')='aal2'" in schema
    assert 'CREATE POLICY report_read_own' in schema
    assert 'GRANT SELECT ON public.simulation_runs,public.report_records TO authenticated' in schema
    assert 'GRANT SELECT ON public.operator_profiles TO authenticated' in schema
    assert 'GRANT SELECT, INSERT, UPDATE ON public.mission_plans TO authenticated' in schema
    assert schema.count('op.active=true') >= 5
