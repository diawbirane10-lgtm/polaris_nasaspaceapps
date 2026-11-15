"""Retired authenticated API remains unreachable in public NASA prototype mode.

The underlying Supabase database retains its original RLS and is not exposed by these routes.
"""
from io import BytesIO
from fastapi.testclient import TestClient
from pypdf import PdfReader
from api.index import app

client=TestClient(app)

INPUT={'question':'Study energy','site':'connecting_ridge','start':'2026-11-14T00:00Z',
       'duration_hours':24,'delay_hours':48,'pv_area_m2':16,'load_w':700,
       'battery_kwh':20,'panel_mode':'horizontal','min_soc_pct':35,
       'min_local_earth_hours':6,'max_local_earth_gap_hours':24,
       'focus':'electrical','selected_scenarios':['original']}

def test_private_auth_routes_unmounted():
    for path in ('/api/private/whoami','/api/private/missions',
                 '/api/admin/requests','/api/registration/status',
                 '/api/workspace-config'):
        assert client.get(path).status_code==404
    for path in ('/api/private/mission-review','/api/private/mission-decision/brief.pdf',
                 '/api/admin/decision','/api/private/continue'):
        assert client.post(path,json=INPUT).status_code==404

def test_public_demo_and_reports_still_work_without_user():
    for path in ('/','/demo','/workspace','/admin'):
        r=client.get(path)
        assert r.status_code==200
        assert 'data-nav="copilot"' in r.text
    r=client.post('/api/mission-decision/brief.pdf',json=INPUT)
    assert r.status_code==200
    document='\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(r.content)).pages)
    assert 'Public demonstration (no verified author)' in document

def test_rls_source_retained_not_exposed_in_api():
    from pathlib import Path
    schema=Path('supabase/sql/secure_workspace_schema.sql').read_text()
    assert 'ALTER TABLE public.mission_plans ENABLE ROW LEVEL SECURITY' in schema
    routes={route.path for route in app.routes}
    assert '/api/private/whoami' not in routes
    assert '/api/admin/requests' not in routes
