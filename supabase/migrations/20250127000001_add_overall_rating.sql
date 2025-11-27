-- Add user_overall_rating table for independent overall rating tracking
CREATE TABLE IF NOT EXISTS public.user_overall_rating (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    rating integer NOT NULL DEFAULT 1600,
    attempts integer NOT NULL DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(user_id)
);

-- Enable RLS
ALTER TABLE public.user_overall_rating ENABLE ROW LEVEL SECURITY;

-- Allow all operations for now (adjust based on your auth setup)
CREATE POLICY "Allow all operations on user_overall_rating" ON public.user_overall_rating
    FOR ALL USING (true) WITH CHECK (true);

