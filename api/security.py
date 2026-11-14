"""POLARIS private workspace: fail-closed JWT/MFA identity and server-managed attribution.

Auth is not activated until a *dedicated* Supabase project is configured. No
client-submitted author/name/role is trusted for a signed engineering report.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from uuid import UUID
from urllib.parse import urlparse

import jwt
from jwt import InvalidTokenError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import requests

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class WorkspaceIdentity:
    user_id: str
    verified_name: str
    token: str
    role: str = 'engineer'


def _settings() -> tuple[str, str, str]:
    url = os.getenv('POLARIS_SUPABASE_URL', '').rstrip('/')
    public_key = os.getenv('POLARIS_SUPABASE_PUBLISHABLE_KEY', '')
    service_key = os.getenv('POLARIS_SUPABASE_SERVER_KEY', '')
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or not parsed.netloc or parsed.path or parsed.query
            or not url.endswith('.supabase.co') or not public_key):
        raise HTTPException(status_code=503, detail='Private workspace not configured')
    return url, public_key, service_key


@lru_cache(maxsize=4)
def _jwks_client(auth_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(auth_url + '/auth/v1/.well-known/jwks.json',
                           cache_jwk_set=True, lifespan=300, timeout=8)


def _verify_claims(token: str, url: str, *, require_mfa: bool = True) -> dict:
    try:
        key = _jwks_client(url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=['RS256', 'ES256'],
                            issuer=url + '/auth/v1', audience='authenticated',
                            options={'require': ['exp', 'iat', 'sub', 'iss', 'aud']},
                            leeway=15)
    except (InvalidTokenError, ValueError) as exc:
        raise HTTPException(status_code=401, detail='Invalid or expired session') from exc
    except Exception as exc:
        # JWKS fetch failures should not disclose signing infrastructure details.
        raise HTTPException(status_code=503, detail='Identity verification temporarily unavailable') from exc
    try:
        UUID(claims['sub'])
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=401, detail='Invalid account identity') from exc
    if claims.get('role') != 'authenticated' or claims.get('is_anonymous') is True:
        raise HTTPException(status_code=403, detail='Verified organization account required')
    if require_mfa and claims.get('aal') != 'aal2':
        raise HTTPException(status_code=403, detail='Multi-factor authentication required')
    return claims


def _verified_profile(url: str, key: str, token: str, user_id: str) -> dict:
    try:
        result = requests.get(
            url + '/rest/v1/operator_profiles',
            params={'user_id': 'eq.' + user_id, 'select': 'user_id,verified_name,active,role'},
            headers={'apikey': key, 'Authorization': 'Bearer ' + token}, timeout=(3, 8))
        result.raise_for_status()
        profiles = result.json()
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(status_code=503, detail='Account directory unavailable') from exc
    if not isinstance(profiles, list) or len(profiles) != 1:
        raise HTTPException(status_code=403, detail='Account not provisioned by workspace administrator')
    profile = profiles[0]
    if (profile.get('user_id') != user_id or profile.get('active') is not True
            or not isinstance(profile.get('verified_name'), str)
            or len(profile['verified_name'].strip()) < 3):
        raise HTTPException(status_code=403, detail='Account identity not verified')
    role = profile.get('role', 'engineer')
    if role not in ('engineer', 'reviewer', 'administrator'):
        raise HTTPException(status_code=403, detail='Unrecognized account role')
    return profile


def require_workspace_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> WorkspaceIdentity:
    url, public_key, _ = _settings()  # configuration is mandatory, even before auth
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Authentication required')
    token = credentials.credentials
    claims = _verify_claims(token, url)
    user_id = claims['sub']
    profile = _verified_profile(url, public_key, token, user_id)
    return WorkspaceIdentity(user_id, profile['verified_name'].strip(), token, profile.get('role', 'engineer'))


def record_report_export(identity: WorkspaceIdentity, report: dict, kind: str) -> str:
    """Server-only append audit. Never release private PDF if audit logging fails."""
    url, _, service_key = _settings()
    if not service_key:
        raise HTTPException(status_code=503, detail='Private report audit requires a configured server key')
    payload = {'actor_user_id': identity.user_id, 'event_type': 'report_export',
               'review_fingerprint': report['review_id'], 'report_kind': kind}
    try:
        response = requests.post(
            url + '/rest/v1/engineering_audit', json=payload,
            headers={'apikey': service_key, 'Authorization': 'Bearer ' + service_key,
                     'Prefer': 'return=representation', 'Content-Type': 'application/json'},
            timeout=(3, 10))
        response.raise_for_status()
        events = response.json()
        if not isinstance(events, list) or len(events) != 1 or not events[0].get('id'):
            raise ValueError('Missing persisted audit identifier')
        return str(events[0]['id'])
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(status_code=503, detail='Export audit unavailable; no private document released') from exc
