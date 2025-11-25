# Setup Guide

This guide walks you through setting up Chess Puzzles Personalized from scratch.

## Prerequisites

- **Python 3.9+** - [Download Python](https://www.python.org/downloads/)
- **Git** - [Download Git](https://git-scm.com/downloads)
- **Supabase Account** - [Sign up free](https://supabase.com/)

## Step 1: Clone and Install

```bash
# Clone the repository
git clone <your-repo-url>
cd chess_puzzles_personalized

# Create virtual environment
python -m venv venv

# Activate it
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Set Up Supabase

### Create a Project

1. Go to [supabase.com](https://supabase.com/) and sign in
2. Click **New Project**
3. Choose a name and password
4. Select a region close to you
5. Wait for the project to be created (~2 minutes)

### Get Your Credentials

1. Go to **Settings** → **API**
2. Copy the **Project URL** (e.g., `https://abc123.supabase.co`)
3. Copy the **anon/public** key (starts with `eyJ...`)

### Create the Database Tables

1. Go to **SQL Editor** in Supabase
2. Click **New Query**
3. Paste the contents of `schema.sql`:

```sql
-- Create users table (supports both Lichess and Google OAuth)
create table public.users (
  id uuid default gen_random_uuid() primary key,
  lichess_id text unique,
  lichess_username text,
  google_id text unique,
  google_email text,
  google_name text,
  provider text not null default 'lichess',
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

-- Create user_category_ratings table
create table public.user_category_ratings (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.users(id) not null,
  category text not null,
  rating integer default 1600 not null,
  attempts integer default 0,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
  unique(user_id, category)
);

-- Enable Row Level Security
alter table public.users enable row level security;
alter table public.puzzle_attempts enable row level security;
alter table public.user_category_ratings enable row level security;

-- Create policies (open for this app - restrict as needed)
create policy "Enable all for users" on public.users for all using (true);
create policy "Enable all for attempts" on public.puzzle_attempts for all using (true);
create policy "Enable all for ratings" on public.user_category_ratings for all using (true);
```

4. Click **Run** to execute

## Step 3: Configure Environment

Create a `.env` file in the project root:

```env
# Flask Configuration
FLASK_SECRET_KEY=change-this-to-a-random-string

# Supabase (paste your values from Step 2)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# OAuth (optional - see Step 4)
# LICHESS_CLIENT_ID=your-lichess-client-id
# GOOGLE_CLIENT_ID=your-google-client-id
# GOOGLE_CLIENT_SECRET=your-google-client-secret

# Base URL (change for production)
BASE_URL=http://localhost:5000
```

## Step 4: Set Up OAuth (Optional)

You can skip this step to run the app without login functionality.

### Lichess OAuth

1. Go to [lichess.org/account/oauth/app](https://lichess.org/account/oauth/app)
2. Click **Register a new app**
3. Fill in:
   - **App name**: Chess Puzzles Personalized
   - **App description**: Personal chess puzzle trainer
   - **Redirect URI**: `http://localhost:5000/callback`
4. Click **Create**
5. Copy the **Client ID** and add to `.env`:
   ```env
   LICHESS_CLIENT_ID=your-client-id
   ```

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Go to **APIs & Services** → **OAuth consent screen**
   - Choose **External**
   - Fill in app name, support email
   - Add scopes: `email`, `profile`, `openid`
   - Save
4. Go to **APIs & Services** → **Credentials**
5. Click **Create Credentials** → **OAuth client ID**
6. Select **Web application**
7. Add **Authorized redirect URIs**: `http://localhost:5000/callback/google`
8. Click **Create**
9. Copy credentials and add to `.env`:
   ```env
   GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxx
   ```

## Step 5: Run the Application

```bash
# Make sure virtual environment is activated
cd server
python main.py
```

Open your browser to **http://localhost:5000**

## Step 6: Verify Everything Works

1. **Home page loads** - You should see the login buttons
2. **Puzzles work** - Click through to solve a puzzle (works without login)
3. **OAuth works** - Try logging in with Lichess or Google
4. **Stats page** - After logging in, check your stats

## Troubleshooting

### "No module named 'flask'"
```bash
# Make sure venv is activated
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # macOS/Linux

# Reinstall dependencies
pip install -r requirements.txt
```

### "Supabase credentials not found"
- Check your `.env` file exists in the project root
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are set correctly
- Make sure there are no extra spaces around the `=` sign

### "Session expired" on OAuth
- Clear your browser cookies for localhost
- Try in an incognito/private window
- Check that `BASE_URL` matches your actual URL

### "redirect_uri_mismatch" from Google
- Go to Google Cloud Console → Credentials
- Edit your OAuth client
- Add the exact redirect URI: `http://localhost:5000/callback/google`
- Wait a few minutes for changes to propagate

## Next Steps

- Read the [full documentation](../README.md)
- Explore the [API reference](./API.md)
- Learn about the [rating system](./RATING_SYSTEM.md)

