"""Self-service access-request status and minimal sign-in audit.

No account may choose its own role or approve its own profile. The database
signup trigger creates immutable self-registration records from Auth metadata.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import requests
from .security import _settings, _verify_claims

router = APIRouter(prefix='/api/registration', tags=['registration'])
_bearer=HTTPBearer(auto_error=False)


def _login_identity(credentials: HTTPAuthorizationCredentials|None=Depends(_bearer)):
    if not credentials or credentials.scheme.lower()!='bearer':
        raise HTTPException(status_code=401,detail='Sign in to view your request')
    url,key,_=_settings()
    claims=_verify_claims(credentials.credentials,url,require_mfa=False)
    return url,key,credentials.credentials,claims


def _send(url:str,key:str,token:str,method:str,path:str,*,params=None,data=None):
    h={'apikey':key,'Authorization':'Bearer '+token,'Accept':'application/json','Content-Type':'application/json'}
    try:
        response=requests.request(method,url+'/rest/v1/'+path,headers=h,params=params,json=data,timeout=(3,10))
    except requests.RequestException as exc:
        raise HTTPException(status_code=503,detail='Identity directory unavailable') from exc
    if response.status_code in (401,403):
        raise HTTPException(status_code=403,detail='Account status unavailable')
    if response.status_code>=400:
        raise HTTPException(status_code=503,detail='Unable to retrieve access status')
    try:return response.json() if response.content else None
    except ValueError as exc:raise HTTPException(status_code=503,detail='Unexpected account status') from exc


@router.get('/status')
def status(identity=Depends(_login_identity)):
    url,key,token,claims=identity
    rows=_send(url,key,token,'GET','access_requests',params={
        'select':'status,created_at,reviewed_at,first_name,last_name',
        'user_id':'eq.'+claims['sub'],'limit':'1'})
    if not isinstance(rows,list):
        raise HTTPException(status_code=503,detail='Account request unavailable')
    if not rows:
        return {'status':'pending','message':'Account awaiting provisioning. Contact the project owner if you registered before this system.'}
    row=rows[0]
    if row.get('status') not in ('pending','approved','rejected'):
        raise HTTPException(status_code=503,detail='Unexpected account state')
    return {'status':row['status'],'requested_at':row.get('created_at'),
            'reviewed_at':row.get('reviewed_at'),
            'name':' '.join((row.get('first_name',''),row.get('last_name',''))).strip()}


