"""POLARIS authenticated multi-user mission persistence.

Only verified MFA sessions can access these routes. Ownership is derived from
verified JWT, and Supabase Postgres RLS enforces it a second time.
Authenticated clients cannot write simulation results or authoritative profiles.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .security import WorkspaceIdentity, require_workspace_identity, _settings

router = APIRouter(prefix='/api/private', tags=['workspace'])


class MissionPlanInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=3, max_length=160)
    input_configuration: dict[str, Any] = Field(default_factory=dict)

    @field_validator('title')
    @classmethod
    def nonblank_title(cls, title: str) -> str:
        title = title.strip()
        if len(title) < 3:
            raise ValueError('Mission title must contain at least three characters')
        return title

    @field_validator('input_configuration')
    @classmethod
    def safe_configuration(cls, cfg: dict[str, Any]) -> dict[str, Any]:
        # A private plan can cover multiple kinds of missions; don't force one demo shape.
        try:
            raw = json.dumps(cfg, allow_nan=False, ensure_ascii=False)
        except (ValueError, TypeError) as exc:
            raise ValueError('Plan configuration must contain finite JSON values') from exc
        if len(raw.encode('utf-8')) > 16000:
            raise ValueError('Mission configuration exceeds 16 KB limit')
        return cfg


def _rest(identity: WorkspaceIdentity, method: str, resource: str, *, params=None, body=None):
    url, key, _ = _settings()
    headers = {'apikey':key,'Authorization':'Bearer '+identity.token,'Accept':'application/json',
               'Content-Type':'application/json','Prefer':'return=representation'}
    try:
        resp = requests.request(method, url+'/rest/v1/'+resource,params=params,json=body,
                                headers=headers,timeout=(4,12))
    except requests.RequestException as exc:
        raise HTTPException(status_code=503,detail='Mission database unavailable') from exc
    if resp.status_code in (401,403):
        raise HTTPException(status_code=403,detail='Database authorization rejected')
    if resp.status_code >= 400:
        # Do not leak Postgres SQL, keys or other-user row existence.
        raise HTTPException(status_code=503,detail='Mission database operation failed')
    try:
        result=resp.json()
    except ValueError as exc:
        raise HTTPException(status_code=503,detail='Unexpected database response') from exc
    if not isinstance(result,list):
        raise HTTPException(status_code=503,detail='Unexpected database result')
    return result


@router.get('/missions')
def list_missions(identity: WorkspaceIdentity=Depends(require_workspace_identity)):
    rows=_rest(identity,'GET','mission_plans',params={'select':'id,title,input_configuration,created_at,updated_at',
                 'owner_id':'eq.'+identity.user_id,'order':'updated_at.desc','limit':'100'})
    return {'missions':rows,'owner_id':identity.user_id}


@router.post('/missions',status_code=201)
def create_mission(plan:MissionPlanInput,identity:WorkspaceIdentity=Depends(require_workspace_identity)):
    body={'owner_id':identity.user_id,'title':plan.title,'input_configuration':plan.input_configuration}
    rows=_rest(identity,'POST','mission_plans',body=body)
    if len(rows)!=1 or rows[0].get('owner_id')!=identity.user_id:
        raise HTTPException(status_code=503, detail='Mission persistence could not be confirmed')
    return {'mission':rows[0]}


def _uuid(mission_id:str)->str:
    try:return str(UUID(mission_id))
    except (ValueError,TypeError) as exc:
        raise HTTPException(status_code=422,detail='Invalid mission identifier') from exc


@router.get('/missions/{mission_id}')
def read_mission(mission_id:str,identity:WorkspaceIdentity=Depends(require_workspace_identity)):
    rows=_rest(identity,'GET','mission_plans',params={'select':'id,title,input_configuration,created_at,updated_at',
                 'id':'eq.'+_uuid(mission_id),'owner_id':'eq.'+identity.user_id,'limit':'1'})
    if len(rows)!=1:raise HTTPException(status_code=404,detail='Mission not found')
    return {'mission':rows[0]}


@router.patch('/missions/{mission_id}')
def update_mission(mission_id:str,plan:MissionPlanInput,identity:WorkspaceIdentity=Depends(require_workspace_identity)):
    params={'id':'eq.'+_uuid(mission_id),'owner_id':'eq.'+identity.user_id}
    rows=_rest(identity,'PATCH','mission_plans',params=params,body={'title':plan.title,
               'input_configuration':plan.input_configuration})
    if len(rows)!=1:raise HTTPException(status_code=404,detail='Mission not found')
    return {'mission':rows[0]}
