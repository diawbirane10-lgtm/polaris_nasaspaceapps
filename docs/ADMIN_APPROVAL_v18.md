# POLARIS — Secure registration and administrator console (v1.8)

## URLs

- `/` — login / user registration (Sport Programme design system).
- `/admin` — administrator login and MFA; approvals, directory and connection history.
- `/workspace` — protected mission workspace, for **approved + MFA** identities only.
- `/demo` — public NASA challenge demonstration; no account required.
- `/terms` — account terms/privacy notice.

## User flow

1. The engineer enters first name, last name, staff ID, work email and password, and accepts `polaris-2026-11-14` terms.
2. Supabase Auth creates an identity. The database trigger `polaris_private.capture_signup_request` creates a **pending** accreditation record in the same transaction; profile and role are **not** user-supplied authorization inputs.
3. The engineer verifies email if required and signs in, then views `PENDING` (amber), `APPROVED` (green) or `REJECTED` (red) through `/api/access/status`. Pending status is refreshed automatically every 15 seconds; it grants **no access** to mission plans.
4. On approval, the engineer clicks **Continue to MFA**, enrolls or verifies a TOTP factor, and only then opens protected missions.

## Administrator flow

1. The administrator signs in at `/admin` with their own account and completes TOTP verification.
2. `GET /api/private/whoami` confirms the active, database-provisioned `administrator` role; all `/api/admin/*` endpoints additionally check the role, PostgreSQL RLS and MFA.
3. **Accreditation queue** shows pending requests; approval/rejection changes only the status. A trigger assigns the decision's admin and UTC time and provisions a verified engineer profile **atomically** upon approval.
4. **Directory** shows first name, last name, staff ID, request/review times and status; it does not show email, passwords or access tokens.
5. **Connection history** reads Supabase Auth `auth.sessions.created_at` via an admin-guarded database function and displays limited name/staff/status/time fields. This describes **issued authentication sessions**, not every browser page visit or continuous activity.

## First administrator: manual one-time bootstrap

**There is no preconfigured administrator password.** To avoid creating a universal backdoor, the project owner must:

1. Go to the dedicated Supabase dashboard → **Authentication** → **Users** → **Add user**. Create the first administrator's personal account securely, with an email only they control and a strong password. Do not create a public sign-up request for this administrator.
2. Copy that account's UUID, not the password. In the project's SQL Editor, provision that specific UUID as follows, replacing only the sample identifiers:

```sql
INSERT INTO public.operator_profiles
  (user_id, verified_name, first_name, last_name, staff_id, role, active, verified_at, verified_by)
VALUES
  ('<UUID_FROM_SUPABASE_AUTH>', '<VERIFIED_FIRST_LAST>', '<VERIFIED_FIRST>',
   '<VERIFIED_LAST>', '<STAFF_ID>', 'administrator', true, now(), '<UUID_FROM_SUPABASE_AUTH>');
```

3. Go to `/admin`, sign in with this account and enroll/verify the authenticator (TOTP). Only the admin's signed MFA session may approve new users.
4. Do not share passwords, OTP codes, service-role keys, or administrator sessions with ChatGPT or team members.

If the administrator account has already signed up using POLARIS, the first `operator_profiles` row can still be provisioned manually, but its separate applicant request may remain pending. Prefer creating the bootstrap admin via Authentication → Users to avoid this ambiguity.

## Database and security controls

- Supabase project: `jgfzkftwlqkmmddkjwrv` (dedicated to POLARIS).
- SQL migration: `supabase/sql/access_approval_and_admin_v18.sql`.
- `access_requests` RLS: read only own request or active MFA admin; update `status` only by admin, and only from `pending` to `approved` or `rejected`.
- `operator_profiles` is the authority for name and role. Never trust `raw_user_meta_data` for roles or access privileges; metadata is only applicant-submitted text pending administrator verification.
- `mission_plans` requires approved profile and AAL2 MFA; each user can access only their own records via RLS.
- All secrets and Supabase service-role keys remain server-only. This implementation needs only a publishable key to operate its registration/admin approval workflow.
- Enrollment, credential verification and password reset are handled by Supabase Auth. No password hashes are stored in the POLARIS `public` schema.
- MFA alone is not phishing-resistant. For institutional use, stronger SSO and risk-based session controls should be added after the hackathon.

## Status and verification

- Database schema migration applied to the dedicated Supabase project.
- Front-end registration and admin MFA / approvals exercised using **mock identities** in Chromium, both desktop and mobile.
- Python API and validation tests pass. No actual administrator account has been provisioned yet; **the real two-account approval flow is not fully tested** until that bootstrap is complete.
- The administrator's `auth.sessions` history cannot be verified with a real session until the first admin signs in.
- The existing private report export still requires `POLARIS_SUPABASE_SERVER_KEY` configured securely to persist protected audit events; do not claim it is fully operational until that key is in place and reports are tested with real identities.

## Deployment notes

The public NASA `/demo` route remains accessible without sign-in. A normal visitor to `/` sees account sign-in/registration first, as requested. `/admin` is a separately rendered login page; the **protected data** behind it cannot be fetched without a genuine administrator MFA JWT.
