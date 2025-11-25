-- Run this in the Supabase SQL Editor

-- Create users table
create table public.users (
  id uuid default gen_random_uuid() primary key,
  lichess_id text unique not null,
  lichess_username text not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create puzzle_attempts table
create table public.puzzle_attempts (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.users(id) not null,
  puzzle_id text not null,
  success boolean not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security (RLS) - Optional for now but good practice
alter table public.users enable row level security;
alter table public.puzzle_attempts enable row level security;

-- Create policies (allowing public access for this simple app, or restrict as needed)
-- For simplicity in this demo, we'll allow all operations for now since we use the service key or anon key with open policies
create policy "Enable read access for all users" on public.users for select using (true);
create policy "Enable insert access for all users" on public.users for insert with check (true);

create policy "Enable read access for all users" on public.puzzle_attempts for select using (true);
create policy "Enable insert access for all users" on public.puzzle_attempts for insert with check (true);

-- Create user_category_ratings table
create table public.user_category_ratings (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.users(id) not null,
  category text not null,
  rating integer default 1200 not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
  unique(user_id, category)
);

-- Enable RLS for ratings
alter table public.user_category_ratings enable row level security;

-- Policies for ratings
create policy "Enable read access for all users" on public.user_category_ratings for select using (true);
create policy "Enable insert/update access for all users" on public.user_category_ratings for all using (true);
