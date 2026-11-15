"""Privileged POLARIS operator access. No admin HTML or data is public.

A short-lived HTTP-only, Secure, SameSite=Strict cookie is issued only after
Supabase aal2 MFA and a currently active server-verified administrator profile.
Each admin request checks the live operator directory, so revocation takes effect
without waiting for cookie expiration. User passwords/tokens never appear in lists.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel
from uuid import UUID
from .security import WorkspaceIdentity, _settings, _verify_claims, _verified_profile, require_workspace_identity

router=APIRouter(tags=['privileged'])
BASE=Path(__file__).resolve().parents[1]
COOKIE='__Host-polaris-privileged'


def _deny():
    # Route existence and admin identity are deliberately indistinguishable.
    raise HTTPException(status_code=404,detail='Not found')


def _admin_identity(request:Request)->WorkspaceIdentity:
    token=request.cookies.get(COOKIE)
    if not token: _deny()
    try:
        url,key,_=_settings()
        claims=_verify_claims(token,url)
        profile=_verified_profile(url,key,token,claims['sub'])
        if profile.get('role')!='administrator':_deny()
        return WorkspaceIdentity(claims['sub'],profile['verified_name'],token,'administrator')
    except HTTPException:
        _deny()


def _same_origin(request:Request):
    origin=request.headers.get('origin','')
    parsed=urlparse(origin)
    host=request.headers.get('host','')
    if not origin or parsed.scheme not in ('https','http') or parsed.netloc!=host:
        _deny()
    # Production is HTTPS only; local test hosts may use HTTP.
    if parsed.scheme != 'https' and not host.startswith(('localhost','127.0.0.1','testserver')):
        _deny()
    if request.headers.get('sec-fetch-site','same-origin') not in ('same-origin','none'):
        _deny()


def _query(identity:WorkspaceIdentity, resource:str,*,params=None):
    url,key,_=_settings()
    try:
        r=requests.get(url+'/rest/v1/'+resource,params=params,headers={
            'apikey':key,'Authorization':'Bearer '+identity.token,'Accept':'application/json'},timeout=(3,10))
        r.raise_for_status();rows=r.json()
        if not isinstance(rows,list):raise ValueError('Unexpected response')
        return rows
    except (requests.RequestException,ValueError) as exc:
        raise HTTPException(status_code=503,detail='Privileged directory temporarily unavailable') from exc


@router.get('/admin',include_in_schema=False)
def admin_console(request:Request):
    # Admin URL can initiate normal login; privileged contents still require live MFA and role checks.
    if not request.cookies.get(COOKIE):
        return RedirectResponse('/', status_code=303, headers={
            'Cache-Control':'private, no-store',
            'X-Robots-Tag':'noindex, nofollow',
            'Referrer-Policy':'no-referrer',
        })
    _admin_identity(request)
    from .admin_template import OPERATOR_HTML
    return HTMLResponse(OPERATOR_HTML,headers={
        'Cache-Control':'private, no-store, max-age=0','X-Robots-Tag':'noindex, nofollow',
        'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'})


@router.post('/api/private/continue',include_in_schema=False)
def continue_to_workspace(request:Request, identity:WorkspaceIdentity=Depends(require_workspace_identity)):
    """Public JS receives a redirect only for an approved admin. No privileged path embedded in HTML/JS."""
    result=JSONResponse({'next':None})
    if identity.role!='administrator':return result
    url,_,_=_settings()
    claims=_verify_claims(identity.token,url)
    ttl=max(1,min(600,int(claims['exp']-datetime.now(timezone.utc).timestamp())))
    result=JSONResponse({'next':'/admin'})
    result.set_cookie(COOKIE,identity.token,httponly=True,secure=True,samesite='strict',max_age=ttl,path='/')
    result.headers['Cache-Control']='no-store'
    return result


@router.get('/api/admin/requests',include_in_schema=False)
def review_queue(request:Request):
    identity=_admin_identity(request)
    rows=_query(identity,'access_requests',params={'select':'user_id,first_name,last_name,staff_id,status,created_at,reviewed_at',
        'order':'created_at.desc','limit':'200'})
    return JSONResponse({'requests':[{'id':r.get('user_id'),'given_name':r.get('first_name'),'family_name':r.get('last_name'),'employee_id':r.get('staff_id'),'status':r.get('status'),'requested_at':r.get('created_at'),'reviewed_at':r.get('reviewed_at')} for r in rows]},
        headers={'Cache-Control':'private, no-store'})


@router.get('/api/admin/visits',include_in_schema=False)
def login_history(request:Request):
    identity=_admin_identity(request)
    url,key,_=_settings()
    try:
        r=requests.post(url+'/rest/v1/rpc/polaris_admin_recent_sessions',
            json={'max_rows':200},headers={'apikey':key,'Authorization':'Bearer '+identity.token,
            'Content-Type':'application/json'},timeout=(3,10))
        r.raise_for_status();entries=r.json()
        if not isinstance(entries,list):raise ValueError('Invalid session record format')
    except (requests.RequestException,ValueError) as exc:
        raise HTTPException(status_code=503,detail='Login activity temporarily unavailable') from exc
    output=[{'given_name':p.get('first_name'),'family_name':p.get('last_name'),
             'employee_id':p.get('staff_id'),'signed_in_at':p.get('session_created_at')}
            for p in entries]
    return JSONResponse({'visits':output},headers={'Cache-Control':'private, no-store'})


class Decision(BaseModel):
    request_id:UUID
    decision:str


@router.post('/api/admin/decision',include_in_schema=False)
def decision(payload:Decision,request:Request):
    _same_origin(request)
    identity=_admin_identity(request)
    if payload.decision not in ('approved','rejected'):
        raise HTTPException(status_code=422,detail='Invalid decision')
    url,key,_=_settings()
    try:
        r=requests.patch(url+'/rest/v1/access_requests',
            params={'user_id':'eq.'+str(payload.request_id),'status':'eq.pending'},
            headers={'apikey':key,'Authorization':'Bearer '+identity.token,'Content-Type':'application/json','Prefer':'return=representation'},
            json={'status':payload.decision},timeout=(3,10))
        if r.status_code in (401,403):_deny()
        if r.status_code not in (200,201,204):
            raise HTTPException(status_code=409,detail='Decision unavailable: check pending status and verified email')
        updated=r.json() if r.content else []
        if len(updated)!=1 or updated[0].get('status')!=payload.decision:
            raise HTTPException(status_code=409,detail='Request is no longer pending')
        return JSONResponse({'status':payload.decision},headers={'Cache-Control':'no-store'})
    except requests.RequestException as exc:
        raise HTTPException(status_code=503,detail='Approval service temporarily unavailable') from exc


@router.post('/api/admin/logout',include_in_schema=False)
def privileged_logout(request:Request):
    _same_origin(request)
    response=Response(status_code=204,headers={'Cache-Control':'no-store'})
    response.delete_cookie(COOKIE,path='/')
    return response
