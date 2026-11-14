-- POLARIS isolated workspace schema — apply ONLY to the dedicated new POLARIS
-- Supabase project after reviewing. Never apply to unrelated Supabase projects.
-- Design: verified, administrator-provisioned legal/display name; aal2 MFA;
-- deny-by-default and owner-level Row Level Security.
BEGIN;

CREATE TABLE IF NOT EXISTS public.operator_profiles (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  verified_name text NOT NULL CHECK (char_length(btrim(verified_name)) BETWEEN 3 AND 160),
  role text NOT NULL DEFAULT 'engineer' CHECK (role IN ('engineer','reviewer','administrator')),
  active boolean NOT NULL DEFAULT false,
  verified_at timestamptz,
  verified_by uuid REFERENCES auth.users(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.mission_plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
  title text NOT NULL CHECK (char_length(btrim(title)) BETWEEN 3 AND 160),
  input_configuration jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(id,owner_id)
);
CREATE INDEX IF NOT EXISTS polaris_missions_owner_idx ON public.mission_plans(owner_id);

CREATE TABLE IF NOT EXISTS public.simulation_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id uuid NOT NULL REFERENCES public.mission_plans(id) ON DELETE RESTRICT,
  owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
  engine_version text NOT NULL,
  data_fingerprint text NOT NULL CHECK (data_fingerprint ~ '^[a-f0-9]{64}$'),
  computed_results jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(id,owner_id),
  FOREIGN KEY(mission_id,owner_id) REFERENCES public.mission_plans(id,owner_id)
);
CREATE INDEX IF NOT EXISTS polaris_runs_owner_idx ON public.simulation_runs(owner_id);

CREATE TABLE IF NOT EXISTS public.report_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES public.simulation_runs(id) ON DELETE RESTRICT,
  owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
  report_kind text NOT NULL CHECK (report_kind IN ('brief','dossier')),
  object_path text NOT NULL,
  sha256 text NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY(run_id,owner_id) REFERENCES public.simulation_runs(id,owner_id)
);
CREATE INDEX IF NOT EXISTS polaris_reports_owner_idx ON public.report_records(owner_id);

CREATE TABLE IF NOT EXISTS public.engineering_audit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
  event_type text NOT NULL CHECK (event_type IN ('report_export','mission_create','mission_update','scenario_run','access_rejected')),
  review_fingerprint text,
  report_kind text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS polaris_audit_actor_idx ON public.engineering_audit(actor_user_id,created_at DESC);

ALTER TABLE public.operator_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mission_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.simulation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.engineering_audit ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.operator_profiles, public.mission_plans, public.simulation_runs,
  public.report_records, public.engineering_audit FROM anon, authenticated;

-- No client can create/update authoritative operator name. Admin/service workflow
-- provisions the profile and sets active=true after organizational verification.
GRANT SELECT ON public.operator_profiles TO authenticated;
CREATE POLICY operator_read_self ON public.operator_profiles FOR SELECT TO authenticated
  USING (user_id=(SELECT auth.uid()) AND (auth.jwt()->>'aal')='aal2' AND active=true);

GRANT SELECT, INSERT, UPDATE ON public.mission_plans TO authenticated;
CREATE POLICY mission_read_own ON public.mission_plans FOR SELECT TO authenticated
  USING (owner_id=(SELECT auth.uid()) AND (auth.jwt()->>'aal')='aal2' AND EXISTS (SELECT 1 FROM public.operator_profiles op WHERE op.user_id=(SELECT auth.uid()) AND op.active=true));
CREATE POLICY mission_insert_own ON public.mission_plans FOR INSERT TO authenticated
  WITH CHECK (owner_id=(SELECT auth.uid()) AND (auth.jwt()->>'aal')='aal2' AND EXISTS (SELECT 1 FROM public.operator_profiles op WHERE op.user_id=(SELECT auth.uid()) AND op.active=true));
CREATE POLICY mission_update_own ON public.mission_plans FOR UPDATE TO authenticated
  USING (owner_id=(SELECT auth.uid()) AND (auth.jwt()->>'aal')='aal2' AND EXISTS (SELECT 1 FROM public.operator_profiles op WHERE op.user_id=(SELECT auth.uid()) AND op.active=true))
  WITH CHECK (owner_id=(SELECT auth.uid()) AND (auth.jwt()->>'aal')='aal2' AND EXISTS (SELECT 1 FROM public.operator_profiles op WHERE op.user_id=(SELECT auth.uid()) AND op.active=true));
-- No authenticated DELETE: retain mission history. No other-user reading.

-- Computed traces and engineering exports must be inserted by trusted backend
-- after recomputation. Clients can only read their own stored results.
GRANT SELECT ON public.simulation_runs,public.report_records TO authenticated;
CREATE POLICY run_read_own ON public.simulation_runs FOR SELECT TO authenticated
  USING (owner_id=(SELECT auth.uid()) AND (auth.jwt()->>'aal')='aal2' AND EXISTS (SELECT 1 FROM public.operator_profiles op WHERE op.user_id=(SELECT auth.uid()) AND op.active=true));
CREATE POLICY report_read_own ON public.report_records FOR SELECT TO authenticated
  USING (owner_id=(SELECT auth.uid()) AND (auth.jwt()->>'aal')='aal2' AND EXISTS (SELECT 1 FROM public.operator_profiles op WHERE op.user_id=(SELECT auth.uid()) AND op.active=true));
-- No direct SELECT/INSERT/UPDATE/DELETE for client role on audit table.

COMMIT;
