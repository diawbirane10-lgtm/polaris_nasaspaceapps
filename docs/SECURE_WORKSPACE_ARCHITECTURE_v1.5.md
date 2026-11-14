# POLARIS — Secure Mission Workspace architecture v1.5

## Status and activation

This is an **isolated, fail-closed implementation skeleton**, not a claim that the public deployment is an authenticated production system. The separate Supabase project has **not been created or configured**, the SQL has **not been applied**, and no named private mission has been stored in it.

Current public NASA hackathon demonstration remains accessible without login, per the official 2026 submission guide. Its unsigned reports state `Public demonstration (no verified author)`. **Private reports** must come only from `/api/private/mission-decision/...`, after verified identity and admin-provisioned profile. Never accept `name`, `owner_id`, `role` or numeric simulation results from client input as authoritative report metadata.

## Threat model and controls

| Threat | Control |
|---|---|
| Stolen password | Mandatory MFA (`aal2`), TOTP or stronger phishing-resistant passkey; no password-only private exports |
| Forged JWT or expired session | Verify asymmetric Supabase JWT signature via JWKS, issuer, audience, expiry, user id; reject anonymous and missing MFA |
| User edits PDF author | Server reads an administrator-managed `operator_profiles.verified_name`, not user metadata or request body |
| Another engineer views a mission | Postgres RLS `owner_id = auth.uid()` and verified MFA; API bearer identity |
| Altered simulation outputs | Server recomputes from NASA references; no direct authenticated DB writes to computed result table |
| Export without a trace | Backend writes `engineering_audit` as server service; failure blocks private file download |
| Credentials exposed in source | Publishable key permitted in frontend; service key backend only, environment secret manager; no .env in git |
| API/DDoS/abuse | Provider rate limits, WAF, timeouts and request caps; configure before sensitive use |
| Session theft | Short-lived tokens and rotation/revocation; additional check with Supabase Auth service for sensitive operations if immediate revocation required |
| LLM instruction injection | Copilot only invokes approved backend methods; LLM cannot grant permissions or mint an approval |

**Not yet delivered:** production MFA onboarding UI, session-revocation hardening, organization SSO, team RBAC/sharing, immutable audit retention, private object storage, database penetration tests, account recovery, security monitoring and backups. Those must be verified in the dedicated live environment before sensitive data is uploaded.

## Data model

- Auth provider: Supabase Auth (dedicated project) with MFA and verified identity.
- `operator_profiles`: server-provisioned name, role and active flag. Authenticated client has only `SELECT` self; cannot change verified name.
- `mission_plans`: created and updated by owner under RLS, `aal2` required.
- `simulation_runs`: server-computed payload plus NASA dataset fingerprint and engine version; direct writes disabled.
- `report_records`: server-owned links to files stored in private bucket, cryptographic hash and author/owner.
- `engineering_audit`: server-only inserts containing actor, report kind, simulation fingerprint and UTC time; backed by database logs. For stronger tamper resistance use externally managed immutable event sink.

## User flow

1. Judge uses `/` or the public demo with open NASA datasets, no account.
2. Engineering user selects **Secure Workspace**, signs in using a supported IdP + MFA and receives a time-bounded session.
3. API `/api/private/whoami` verifies signature+MFA and retrieves verified profile through row-level restricted database query.
4. Engineer creates mission plan; server associates its owner from the token only.
5. Approved compute tool evaluates mission parameters and saves a result under the verified owner.
6. Engineer requests report; server *recomputes*, fetches profile, writes audit event and generates English Brief/Dossier with `Prepared by: <verified_name>`, UTC and audit ref.
7. Download/read is permitted only for the resource owner or future explicit team permissions. Sharing is never inferred from a guessed UUID.

## Required configuration procedure

1. Select the organization for a new **POLARIS only** Supabase project, and verify it is on an appropriate plan and region.
2. Enable asymmetric JWT signing, confirmed-email accounts, MFA enrollment/challenge and enforce required MFA for private endpoints.
3. In the newly created POLARIS database only, review then apply `supabase/sql/secure_workspace_schema.sql`. Enable RLS everywhere.
4. Provision test operators with names validated by the workspace administrator. Do not rely on self-declared names for report authorship.
5. Set `POLARIS_SUPABASE_URL`, `POLARIS_SUPABASE_PUBLISHABLE_KEY`, `POLARIS_SUPABASE_SERVER_KEY` in *Vercel backend environment secrets*. Never commit real values.
6. Implement and audit login UI and private object storage with strict owner checks; test two distinct real user accounts and cross-account forbidden operations.
7. Run penetration/security test suite including failed JWT verification, MFA, IDOR, isolation, report name spoofing, stolen/revoked session handling and audit immutability, then promote behind feature flag.

## Public demo constraints

NASA Space Apps requires public access to the final project and the 30-second video or seven-slide deck without password or registration. Protect private business/mission plans but retain public sample datasets as a separate isolated non-account route.

## Sources

- OWASP ASVS 5.0 V6/V7: https://github.com/OWASP/ASVS
- Supabase JWT asymmetric validation: https://supabase.com/docs/guides/auth/jwts
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase MFA: https://supabase.com/docs/guides/auth/auth-mfa
- NASA Space Apps project submission: https://www.spaceappschallenge.org/resources/project-submission-guide/
