-- Add attempts column to track number of attempts per category
ALTER TABLE public.user_category_ratings 
ADD COLUMN IF NOT EXISTS attempts integer DEFAULT 0;


