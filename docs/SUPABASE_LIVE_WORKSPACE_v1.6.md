# POLARIS v1.6 — Secure Mission Workspace

**Live public demo:** https://polaris-spaceapps-2026.vercel.app/

**Private workspace:** https://polaris-spaceapps-2026.vercel.app/workspace

**Project:** Dedicated Supabase project `jgfzkftwlqkmmddkjwrv` (Europe West).

## Deployment state (14 November 2026)

- Database: `operator_profiles`, `mission_plans`, `simulation_runs`, `report_records`, `engineering_audit` with RLS enabled.
- Browser uses ONLY Supabase publishable key; private database queries carry the authenticated user's JWT.
- FastAPI validates issuer, audience, JWT signature via public ES256 JWKS, UUID subject and `aal2` MFA. It reads active profiles from a server-managed directory.
- Admin-provisioned profiles prevent spoofing a report author's name.
- A PostgreSQL audit trigger tracks creation and updates of mission plans; the audit table itself is not directly writable by public roles.
- Realtime Postgres changes are enabled only for the `mission_plans` table and filtered by `owner_id`. Connected browsers synchronize their own missions after they have authenticated.
- Public NASA demo remains accessible without any account, as required by the NASA submission guide.

## Activation gate

**The database has no users yet.** An authorized administrator must create/authenticate real users and provision each `operator_profiles` record with an approved legal/display name, `active=true`, role, and verification timestamp. Require TOTP MFA enrollment and completion (`aal2`) before admitting an engineer.

**Private PDF exports are intentionally disabled until `POLARIS_SUPABASE_SERVER_KEY` is set as a secret on the Vercel server.** The browser must never see that key. The `engineering_audit` insertion is verified before returning a private PDF; it fails closed if the key is missing.

Do not reuse profiles or data from another user's Supabase project. Do not use the public demo for sensitive mission plans.

## Manual acceptance tests, before confidential use

1. Create two independent approved test accounts with TOTP MFA.
2. Confirm a user without MFA is denied by all `/api/private` endpoints.
3. Confirm account A cannot list, read, edit or export account B's mission UUID.
4. Confirm an administrator-disabled account is denied.
5. Confirm mission create/update emits one auditable event in the same transaction.
6. Configure the server key securely, then confirm private report output has the verified account name and persisted audit ID.
7. Confirm realtime only exposes a user's own mission records and reconnects after a network interruption.
8. Run a security review, limit session lifetimes and establish a secrets rotation and incident-response procedure.

The tests in `tests/test_private_workspace_security.py` exercise a mocked identity boundary; they are not a substitute for cross-account integration tests on the real Supabase project.
