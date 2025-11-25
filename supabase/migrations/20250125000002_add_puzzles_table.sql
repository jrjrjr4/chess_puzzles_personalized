-- Create puzzles table to store all chess puzzles
create table public.puzzles (
  puzzle_id text primary key,
  fen text not null,
  moves text not null,
  rating integer not null,
  rating_deviation integer not null,
  popularity integer not null,
  nb_plays integer not null,
  themes text not null,
  game_url text not null,
  opening_tags text
);

-- Create indexes for efficient querying
create index idx_puzzles_rating on public.puzzles(rating);
create index idx_puzzles_themes on public.puzzles using gin(to_tsvector('english', themes));

-- Enable Row Level Security
alter table public.puzzles enable row level security;

-- Allow read access for all users (puzzles are public data)
create policy "Enable read access for all users" on public.puzzles for select using (true);

