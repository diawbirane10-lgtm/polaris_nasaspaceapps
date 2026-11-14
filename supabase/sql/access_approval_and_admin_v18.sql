-- POLARIS v1.8 — registration approval and private administration.
-- Run on the dedicated POLARIS Supabase project ONLY, after secure_workspace_schema.sql.
-- Security model: no self-assigned role, database-transactional approval,
-- MFA for administrators and approved engineering workspace access.

BEGIN;

ALTER TABLE public.operator_profiles
  ADD COLUMN IF NOT EXISTS first_name text,
  ADD COLUMN IF NOT EXISTS last_name text,
  ADD COLUMN IF NOT EXISTS staff_id text;

CREATE TABLE IF NOT EXISTS public.access_requests (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  first_name text NOT NULL CHECK (char_length(btrim(first_name)) BETWEEN 2 AND 80),
  last_name text NOT NULL CHECK (char_length(btrim(last_name)) BETWEEN 2 AND 80),
  staff_id text NOT NULL CHECK (staff_id ~ '^[a-zA-Z0-9][a-zA-Z0-9._-]{2,31}$'),
  terms_version text NOT NULL,
  terms_accepted_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
  reviewed_at timestamptz,
  reviewed_by uuid REFERENCES auth.users(id),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS polaris_registration_status_idx
  ON public.access_requests(status, created_at DESC);
ALTER TABLE public.access_requests ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.access_requests FROM PUBLIC, anon, authenticated;
GRANT SELECT, UPDATE(status) ON public.access_requests TO authenticated;

-- An applicant may check their own approval status with a standard authenticated
-- session. Access to missions still requires administrator approval AND MFA.
CREATE POLICY polaris_request_self_read ON public.access_requests
  FOR SELECT TO authenticated
  USING (user_id = (select auth.uid()) AND coalesce(auth.jwt()->>'is_anonymous','false') <> 'true');

-- A private (non-exposed) function validates the admin role against
-- administrator-provisioned profiles, never self-editable JWT user_metadata.
CREATE OR REPLACE FUNCTION polaris_private.is_active_admin()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $fn$
 SELECT COALESCE(
  (SELECT p.active AND p.role='administrator' AND p.verified_at IS NOT NULL
   FROM public.operator_profiles p WHERE p.user_id = auth.uid()), false)
 AND (auth.jwt()->>'aal')='aal2'
 AND coalesce(auth.jwt()->>'is_anonymous','false') <> 'true';
$fn$;
REVOKE ALL ON FUNCTION polaris_private.is_active_admin() FROM PUBLIC, anon;
GRANT USAGE ON SCHEMA polaris_private TO authenticated;
GRANT EXECUTE ON FUNCTION polaris_private.is_active_admin() TO authenticated;

CREATE POLICY polaris_admin_requests_read ON public.access_requests
  FOR SELECT TO authenticated USING ((select polaris_private.is_active_admin()));
CREATE POLICY polaris_admin_request_decision ON public.access_requests
  FOR UPDATE TO authenticated
  USING ((select polaris_private.is_active_admin()) AND status='pending')
  WITH CHECK ((select polaris_private.is_active_admin()) AND status IN ('approved','rejected'));

-- Collect self-declared identifiers at signup. They are NOT authorization claims.
-- User account and request are created in the same Auth transaction.
CREATE OR REPLACE FUNCTION polaris_private.capture_signup_request()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $fn$
DECLARE m jsonb; given text; family text; employee text;
BEGIN
 m := COALESCE(NEW.raw_user_meta_data, '{}'::jsonb);
 IF m->>'polaris_signup' IS DISTINCT FROM 'true' THEN RETURN NEW; END IF;
 given := btrim(COALESCE(m->>'first_name',''));
 family := btrim(COALESCE(m->>'last_name',''));
 employee := btrim(COALESCE(m->>'staff_id',''));
 IF char_length(given) NOT BETWEEN 2 AND 80 OR char_length(family) NOT BETWEEN 2 AND 80
    OR employee !~ '^[a-zA-Z0-9][a-zA-Z0-9._-]{2,31}$'
    OR m->>'accepted_terms' IS DISTINCT FROM 'true'
    OR m->>'terms_version' IS DISTINCT FROM 'polaris-2026-11-14' THEN
    RAISE EXCEPTION 'Invalid POLARIS registration metadata';
 END IF;
 INSERT INTO public.access_requests (
  user_id,first_name,last_name,staff_id,terms_version,terms_accepted_at)
 VALUES (NEW.id,given,family,employee,'polaris-2026-11-14',now());
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION polaris_private.capture_signup_request() FROM PUBLIC, anon, authenticated;
DROP TRIGGER IF EXISTS polaris_capture_registration ON auth.users;
CREATE TRIGGER polaris_capture_registration AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION polaris_private.capture_signup_request();

-- Before an admin changes a request's status, the DB itself confirms approval
-- authority. Client can only update status (GRANT UPDATE(status) above).
CREATE OR REPLACE FUNCTION polaris_private.validate_access_decision()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $fn$
BEGIN
 IF NOT polaris_private.is_active_admin() THEN RAISE EXCEPTION 'Administrator MFA required'; END IF;
 IF OLD.status <> 'pending' OR NEW.status NOT IN ('approved','rejected') THEN
  RAISE EXCEPTION 'Request transition not permitted'; END IF;
 IF NEW.user_id IS DISTINCT FROM OLD.user_id
    OR NEW.first_name IS DISTINCT FROM OLD.first_name
    OR NEW.last_name IS DISTINCT FROM OLD.last_name
    OR NEW.staff_id IS DISTINCT FROM OLD.staff_id
    OR NEW.terms_version IS DISTINCT FROM OLD.terms_version
    OR NEW.terms_accepted_at IS DISTINCT FROM OLD.terms_accepted_at
    OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
  RAISE EXCEPTION 'Applicant fields are immutable'; END IF;
 NEW.reviewed_by := auth.uid();
 NEW.reviewed_at := now();
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION polaris_private.validate_access_decision() FROM PUBLIC, anon, authenticated;
DROP TRIGGER IF EXISTS polaris_validate_request_decision ON public.access_requests;
CREATE TRIGGER polaris_validate_request_decision BEFORE UPDATE ON public.access_requests
  FOR EACH ROW EXECUTE FUNCTION polaris_private.validate_access_decision();

-- Transactional approval: a successful status change also provisions the
-- authoritative identity. No route accepts client-provided name or user role.
CREATE OR REPLACE FUNCTION polaris_private.provision_approved_account()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $fn$
BEGIN
 IF NEW.status='approved' THEN
   IF EXISTS (SELECT 1 FROM public.operator_profiles p
              WHERE p.user_id=NEW.user_id AND p.role<>'engineer') THEN
      RAISE EXCEPTION 'Cannot overwrite a privileged operator profile';
   END IF;
   INSERT INTO public.operator_profiles (
     user_id,verified_name,first_name,last_name,staff_id,role,active,verified_at,verified_by)
   VALUES (NEW.user_id, NEW.first_name||' '||NEW.last_name,
           NEW.first_name,NEW.last_name,NEW.staff_id,'engineer',true,now(),auth.uid())
   ON CONFLICT (user_id) DO UPDATE SET
     verified_name=EXCLUDED.verified_name,
     first_name=EXCLUDED.first_name,last_name=EXCLUDED.last_name,
     staff_id=EXCLUDED.staff_id,active=true,
     verified_at=EXCLUDED.verified_at,verified_by=EXCLUDED.verified_by;
 END IF;
 RETURN NEW;
END $fn$;
REVOKE ALL ON FUNCTION polaris_private.provision_approved_account() FROM PUBLIC, anon, authenticated;
DROP TRIGGER IF EXISTS polaris_approve_provision ON public.access_requests;
CREATE TRIGGER polaris_approve_provision AFTER UPDATE OF status ON public.access_requests
 FOR EACH ROW EXECUTE FUNCTION polaris_private.provision_approved_account();

-- Admin dashboard: aggregate sessions from the authoritative Supabase Auth
-- session table, not client-fabricated login events. Do NOT return passwords,
-- credentials, token material, email addresses or network identifiers.
CREATE OR REPLACE FUNCTION public.polaris_admin_recent_sessions(max_rows integer DEFAULT 100)
RETURNS TABLE(first_name text,last_name text,staff_id text,
              account_status text,session_created_at timestamptz)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $fn$
BEGIN
 IF NOT polaris_private.is_active_admin() THEN
   RAISE EXCEPTION 'Administrator authorization required';
 END IF;
 RETURN QUERY SELECT
   COALESCE(r.first_name,p.first_name,'Unregistered')::text,
   COALESCE(r.last_name,p.last_name,'')::text,
   COALESCE(r.staff_id,p.staff_id,'—')::text,
   COALESCE(r.status,CASE WHEN p.active THEN 'approved' ELSE 'unregistered' END)::text,
   s.created_at
 FROM auth.sessions s
 LEFT JOIN public.access_requests r ON r.user_id=s.user_id
 LEFT JOIN public.operator_profiles p ON p.user_id=s.user_id
 ORDER BY s.created_at DESC
 LIMIT LEAST(GREATEST(COALESCE(max_rows,100),1),200);
END $fn$;
REVOKE ALL ON FUNCTION public.polaris_admin_recent_sessions(integer) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.polaris_admin_recent_sessions(integer) TO authenticated;

COMMIT;
