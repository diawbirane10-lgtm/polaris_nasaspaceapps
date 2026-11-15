-- POLARIS v1.9 targeted hardening of the EXISTING v1.8 access_requests schema.
-- Does not create, replace, or delete applicant tables or stored records.
BEGIN;
GRANT UPDATE(status) ON public.access_requests TO authenticated;
REVOKE UPDATE(first_name,last_name,staff_id,terms_version,terms_accepted_at,
              created_at,reviewed_at,reviewed_by,user_id) ON public.access_requests FROM authenticated;
CREATE OR REPLACE FUNCTION polaris_private.validate_access_decision()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
BEGIN
 IF NOT polaris_private.is_active_admin() THEN
   RAISE EXCEPTION 'Administrator MFA required' USING ERRCODE='42501';
 END IF;
 IF OLD.status <> 'pending' OR NEW.status NOT IN ('approved','rejected') THEN
   RAISE EXCEPTION 'Request transition not permitted' USING ERRCODE='22023';
 END IF;
 IF NEW.user_id=auth.uid() THEN
   RAISE EXCEPTION 'Cannot review own registration' USING ERRCODE='42501';
 END IF;
 IF NEW.status = 'approved' AND NOT EXISTS (
   SELECT 1 FROM auth.users u WHERE u.id = NEW.user_id AND u.email_confirmed_at IS NOT NULL
 ) THEN RAISE EXCEPTION 'Email confirmation required' USING ERRCODE='22023'; END IF;
 IF NEW.user_id IS DISTINCT FROM OLD.user_id
    OR NEW.first_name IS DISTINCT FROM OLD.first_name
    OR NEW.last_name IS DISTINCT FROM OLD.last_name
    OR NEW.staff_id IS DISTINCT FROM OLD.staff_id
    OR NEW.terms_version IS DISTINCT FROM OLD.terms_version
    OR NEW.terms_accepted_at IS DISTINCT FROM OLD.terms_accepted_at
    OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
   RAISE EXCEPTION 'Applicant fields are immutable' USING ERRCODE='22023';
 END IF;
 NEW.reviewed_by := auth.uid(); NEW.reviewed_at := now();
 RETURN NEW;
END $function$;
COMMIT;
