"""Admin approval, applicant status, and verified Supabase Auth session history.

Admin access is checked twice: here using a verified MFA-bound operator identity,
and again in PostgreSQL row security and narrowly scoped functions. No API ever
returns account passwords, Supabase tokens, or email login identifiers.
"""
from __future__ import annotations

from uuid import UUID

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict
from typing import Literal

from .security import (
    WorkspaceIdentity, _bearer, _settings, _verify_claims,
    require_workspace_identity,
)

router = APIRouter(tags=['registration-admin'])


def _user_session(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Sign in required')
    url, _, _ = _settings()
    claims = _verify_claims(credentials.credentials, url, require_mfa=False)
    return {'user_id': claims['sub'], 'token': credentials.credentials,
            'aal': claims.get('aal','aal1')}


def _admin(identity: WorkspaceIdentity = Depends(require_workspace_identity)) -> WorkspaceIdentity:
    if identity.role != 'administrator':
        raise HTTPException(status_code=403, detail='Administrator account required')
    return identity


def _db(method: str, resource: str, token: str, *, params=None, body=None) -> list:
    url, public_key, _ = _settings()
    headers = {'apikey': public_key, 'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json',
               'Prefer': 'return=representation'}
    try:
        r = requests.request(method, url + '/rest/v1/' + resource,
                             params=params, json=body, headers=headers,
                             timeout=(4, 14))
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail='Access directory temporarily unavailable') from exc
    if r.status_code in (401, 403):
        raise HTTPException(status_code=403, detail='Database authorization denied')
    if r.status_code >= 400:
        raise HTTPException(status_code=503, detail='Access directory operation unsuccessful')
    try:
        result = r.json()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail='Malformed directory response') from exc
    if not isinstance(result, list):
        raise HTTPException(status_code=503, detail='Malformed directory response')
    return result


@router.get('/api/access/status')
def own_registration_status(session: dict = Depends(_user_session)):
    """Allows a pending, signed-in applicant to see approval without MFA.

    This is not workspace authorization; mission APIs continue requiring MFA
    and an active, verified operator profile.
    """
    rows = _db('GET', 'access_requests', session['token'], params={
        'select': 'first_name,last_name,staff_id,status,created_at,reviewed_at',
        'user_id': 'eq.' + session['user_id'], 'limit': '1'})
    if not rows:
        return {'status':'not_registered','mfa_required_for_workspace':True}
    r=rows[0]
    return {'status':r['status'], 'first_name':r['first_name'], 'last_name':r['last_name'],
            'staff_id':r['staff_id'], 'submitted_at':r['created_at'],
            'reviewed_at':r.get('reviewed_at'), 'mfa_required_for_workspace':True}


@router.get('/api/admin/requests')
def admin_registration_queue(identity: WorkspaceIdentity = Depends(_admin)):
    rows = _db('GET', 'access_requests', identity.token, params={
        'select':'user_id,first_name,last_name,staff_id,status,created_at,reviewed_at,terms_version,terms_accepted_at',
        'order':'created_at.desc', 'limit':'200'})
    return {'requests':rows, 'administrator':identity.verified_name}


class ReviewDecision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    status: Literal['approved','rejected']


@router.post('/api/admin/requests/{user_id}/decision')
def admin_review_registration(user_id: str, decision: ReviewDecision,
                              identity: WorkspaceIdentity = Depends(_admin)):
    try:
        account_id = str(UUID(user_id))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail='Invalid request identifier') from exc
    rows = _db('PATCH', 'access_requests', identity.token, params={
        'user_id':'eq.'+account_id, 'status':'eq.pending',
        'select':'user_id,first_name,last_name,staff_id,status,reviewed_at'},
        body={'status':decision.status})
    if len(rows) != 1 or rows[0].get('status') != decision.status:
        raise HTTPException(status_code=409, detail='Request already reviewed or not available')
    return {'request':rows[0], 'reviewed_by':identity.verified_name}


@router.get('/api/admin/sessions')
def admin_auth_sessions(identity: WorkspaceIdentity = Depends(_admin)):
    rows = _db('POST', 'rpc/polaris_admin_recent_sessions', identity.token,
               body={'max_rows':150})
    # Only personal identifiers required for the operator overview, plus UTC time.
    allow={'first_name','last_name','staff_id','account_status','session_created_at'}
    return {'sessions':[{k:v for k,v in row.items() if k in allow} for row in rows],
            'source':'Supabase Auth session creation timestamps',
            'timezone':'UTC'}
