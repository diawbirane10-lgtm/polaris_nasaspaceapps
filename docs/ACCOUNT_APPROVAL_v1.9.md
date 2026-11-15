# POLARIS v1.9 — Account registration, approval, and audit

## Architecture

- Authentication: Supabase Auth, email verification and TOTP MFA (`aal2`).
- Registration: `auth.users` signup trigger `polaris_private.capture_signup_request` writes `public.access_requests` from explicit user consent and validated metadata.
- Identity for signed reports: server-verified `operator_profiles.verified_name`, not user metadata or a browser field.
- Request statuses: `pending` → `approved` or `rejected`; no reverse transition. Pending statuses are read at `aal1` only by their owners.
- Authorization: RLS, active operator profile and MFA checks at the API and database. Approval can change only `status`; the database writes `reviewed_by` and `reviewed_at` and provisions the profile.
- Login history: protected `polaris_admin_recent_sessions` RPC, querying Supabase Auth session timestamps and returning only name, professional ID, status, date and time. It is not a log of every page visit.
- Protected operator console HTML: `internal/operator_console.html`, **not** within the static `public/` tree. `/admin` checks a short-lived Secure, HttpOnly, SameSite=Strict cookie on every request. Unauthenticated and non-admin users receive 404. No route or link is embedded in public HTML/JavaScript.
- Admin decisions: server checks current role/MFA and same-origin request; PostgreSQL rechecks RLS and active admin in a trigger. Approval also requires the user's email to be confirmed.
- UX design: same flat white/black palette, blue `#145dff`, cyan `#009fbd`, green `#157b58`, yellow `#c28a00`, red `#cb3831` as `sportprogramme.vercel.app`; no gradients or glass effects.

## Existing Supabase structure

Dedicated project `jgfzkftwlqkmmddkjwrv` (EU West 1). Baseline migrations already existed: `polaris_secure_workspace_rls_v1`, `registration_admin_directory_visits_v18`, `polaris_registration_approval_admin_v18`. **Do not run the abandoned schema-creation proposal `20261115_approval_workflow.sql`**. The only additive v1.9 migration is `supabase/sql/20261115_existing_schema_hardening.sql`, which fixes UPDATE(status) permissions, strengthens email-verification requirements and blocks self-approval.

The project also has an older `registration_requests` table. The v1.9 workflow consistently uses **`access_requests`**, the table populated automatically by the existing `auth.users` signup trigger. Avoid conflating the two tables.

## Bootstrap the first administrator

1. Sign up using the actual operator's own email, first and last name and professional ID. Confirm the email link.
2. **Manually verify that identity outside the app**, then use the Supabase Dashboard SQL Editor as database owner to promote that exact account. Do not publish or paste user passwords or credentials into chat.
3. In SQL Editor, find the intended account by confirmed email, validate its identity and UUID. Then (with the verified UUID substituted by the owner) set its `access_requests.status` to `approved` and provision its `operator_profiles` as role `administrator`, `active=true`, `verified_at=now()`; use a privileged dashboard transaction only. Do not use public API to bootstrap an administrator.
4. Sign in at `/`, complete TOTP and allow the server to route the verified operator to the protected console automatically. Approve another test registration to verify the complete flow.
5. Run cross-account tests: applicant A must not read B's request or missions, an engineer must receive 404 from protected routes, a pending user must be unable to enter a mission, and a disabled administrator must lose access on the next request.

## Live release checks

- `python -m pytest -q` for backend regressions; no production identities used in tests.
- GET `/` must contain register/sign-in/pending forms and a terms link.
- GET `/demo` must remain public.
- Unauthenticated GET `/admin`, GET `/api/admin/requests`, GET `/api/admin/visits` must return 404.
- POST `/api/admin/decision` must return 404 without a verified admin session and reject cross-origin calls.
- Verify the RLS `authenticated` role can UPDATE only `access_requests.status` (not name or matricule).
- `public.polaris_admin_recent_sessions` is security-definer by design but enforces active admin + AAL2 internally; keep it under security review.
- No account is initially automatically designated as administrator.

## Privacy and limitations

Applicants supply their claimed name/matricule. Approval is the operator verification step. The admin dashboard exposes no email login identifiers or password material, and its session history is based on Supabase Auth session creation timestamps, not all navigation events. A strict institutional deployment additionally needs formal identity verification, periodic access reviews, logs, incident response and an appropriate privacy policy.
