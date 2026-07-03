-- Bring the original users table in line with the current OAuth-aware app code.

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS google_id text UNIQUE,
  ADD COLUMN IF NOT EXISTS google_email text,
  ADD COLUMN IF NOT EXISTS google_name text,
  ADD COLUMN IF NOT EXISTS provider text DEFAULT 'lichess';

ALTER TABLE public.users
  ALTER COLUMN lichess_id DROP NOT NULL,
  ALTER COLUMN lichess_username DROP NOT NULL;

ALTER TABLE public.users
  ALTER COLUMN provider SET NOT NULL;

ALTER TABLE public.user_category_ratings
  ALTER COLUMN rating SET DEFAULT 1600;
