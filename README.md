# Chess Puzzles Personalized

A personalized chess puzzle trainer that adapts to your skill level across different tactical themes. Track your progress, identify weaknesses, and improve your chess tactics with an intelligent rating system.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- **Adaptive Puzzle Selection**: Puzzles are selected based on your weaknesses across 10 tactical categories
- **Elo Rating System**: Track your rating in each category with a sophisticated Elo-based system
- **Multiple OAuth Providers**: Login with Lichess or Google
- **Progress Tracking**: View detailed statistics and identify areas for improvement
- **Responsive Design**: Dark-themed, modern UI that works on desktop and mobile

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Authentication](#authentication)
- [Rating System](#rating-system)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Deployment](#deployment)

---

## Quick Start

### Prerequisites

- Python 3.9+
- A Supabase account (for database)
- Lichess OAuth app (optional, for Lichess login)
- Google OAuth credentials (optional, for Google login)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd chess_puzzles_personalized
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows (PowerShell)
   .\venv\Scripts\Activate.ps1
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   # Flask
   FLASK_SECRET_KEY=your-secret-key-here
   
   # Supabase (required for user data)
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   
   # Lichess OAuth (optional)
   LICHESS_CLIENT_ID=your-lichess-client-id
   
   # Google OAuth (optional)
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   
   # Base URL (for OAuth redirects)
   BASE_URL=http://localhost:5000
   
   # Admin (optional)
   ADMIN_KEY=your-admin-key
   ```

5. **Set up the database**
   
   Run the SQL in `schema.sql` in your Supabase SQL Editor.

6. **Run the application**
   ```bash
   cd server
   python main.py
   ```
   
   Visit `http://localhost:5000`

---

## Architecture

### Project Structure

```
chess_puzzles_personalized/
├── server/                    # Backend application
│   ├── main.py               # Flask app & routes
│   ├── db_manager.py         # Database operations (Supabase)
│   ├── user_manager.py       # OAuth handlers (Lichess & Google)
│   ├── puzzle_manager.py     # Puzzle selection logic
│   ├── rating_manager.py     # Rating calculations
│   └── templates/            # Jinja2 HTML templates
│       ├── base.html         # Base template with header/nav
│       ├── index.html        # Home page
│       ├── puzzle.html       # Puzzle solving interface
│       ├── stats.html        # User statistics
│       └── error.html        # Error page
├── static/                    # Static assets
│   ├── style.css             # Main stylesheet
│   └── scripts.js            # Frontend JavaScript
├── data/                      # Puzzle data
│   └── filtered_puzzles.csv  # Local puzzle database
├── tests/                     # Test suite
│   ├── conftest.py           # Pytest fixtures
│   ├── test_puzzle_manager.py
│   ├── test_db_manager.py
│   ├── test_user_manager.py
│   ├── test_routes.py
│   └── test_rating_calculations.py
├── supabase/                  # Supabase configuration
│   └── migrations/           # Database migrations
├── requirements.txt           # Python dependencies
├── pytest.ini                # Pytest configuration
└── schema.sql                # Database schema
```

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Flask App (main.py)                      │
│                                                                  │
│  Routes:                                                         │
│  • /              → Home page                                    │
│  • /login         → Lichess OAuth                                │
│  • /login/google  → Google OAuth                                 │
│  • /callback      → Lichess OAuth callback                       │
│  • /callback/google → Google OAuth callback                      │
│  • /logout        → Clear session                                │
│  • /puzzle/random/view → Solve puzzles                           │
│  • /stats         → View statistics                              │
│  • /api/puzzle/attempt → Record attempt (POST)                   │
│  • /api/reset-ratings → Reset user ratings (POST)                │
└─────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  UserManager    │  │  DBManager      │  │  PuzzleManager  │
│                 │  │                 │  │                 │
│ • Lichess OAuth │  │ • User CRUD     │  │ • Load puzzles  │
│ • Google OAuth  │  │ • Ratings       │  │ • Random select │
│ • PKCE flow     │  │ • Attempts      │  │ • Adaptive pick │
│ • Token mgmt    │  │ • K-factor calc │  │ • Rating match  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │    Supabase     │
                    │                 │
                    │ • users         │
                    │ • puzzle_attempts│
                    │ • user_category_ratings │
                    │ • puzzles       │
                    └─────────────────┘
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_SECRET_KEY` | Yes | Secret key for session encryption |
| `SUPABASE_URL` | Yes* | Supabase project URL |
| `SUPABASE_KEY` | Yes* | Supabase anon/service key |
| `LICHESS_CLIENT_ID` | No | Lichess OAuth client ID |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth client secret |
| `BASE_URL` | No | Base URL for OAuth redirects (default: `http://localhost:5000`) |
| `ADMIN_KEY` | No | Admin API key for bulk operations |

*The app works without Supabase but won't persist user data.

### Database Schema

The app uses four main tables:

#### `users`
Stores user accounts from OAuth providers.

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lichess_id TEXT UNIQUE,        -- Lichess username
  lichess_username TEXT,
  google_id TEXT UNIQUE,         -- Google sub ID
  google_email TEXT,
  google_name TEXT,
  provider TEXT DEFAULT 'lichess', -- 'lichess' or 'google'
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `user_category_ratings`
Tracks Elo ratings per tactical category.

```sql
CREATE TABLE user_category_ratings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  category TEXT NOT NULL,        -- e.g., 'fork', 'pin', 'mate'
  rating INTEGER DEFAULT 1600,
  attempts INTEGER DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, category)
);
```

#### `puzzle_attempts`
Records each puzzle attempt.

```sql
CREATE TABLE puzzle_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  puzzle_id TEXT NOT NULL,
  success BOOLEAN NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `puzzles`
Stores puzzle data (optional - can use CSV instead).

```sql
CREATE TABLE puzzles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  puzzle_id TEXT UNIQUE NOT NULL,
  fen TEXT NOT NULL,
  moves TEXT NOT NULL,
  rating INTEGER,
  themes TEXT,
  popularity INTEGER
);
```

---

## Authentication

The app supports two OAuth providers:

### Lichess OAuth (PKCE)

Lichess uses OAuth 2.0 with PKCE (Proof Key for Code Exchange), which doesn't require a client secret.

1. **Register your app** at [lichess.org/account/oauth/app](https://lichess.org/account/oauth/app)
2. Set the redirect URI to `http://localhost:5000/callback`
3. Add `LICHESS_CLIENT_ID` to your `.env`

**Flow:**
```
User clicks "Login with Lichess"
    │
    ▼
Generate PKCE verifier + challenge
Store in session
    │
    ▼
Redirect to lichess.org/oauth
    │
    ▼
User authorizes
    │
    ▼
Lichess redirects to /callback with code
    │
    ▼
Exchange code + verifier for token
    │
    ▼
Fetch user info from Lichess API
    │
    ▼
Create/get user in database
Store in session
```

### Google OAuth

Google uses standard OAuth 2.0 with client credentials.

1. **Create credentials** in [Google Cloud Console](https://console.cloud.google.com/)
2. Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
3. Select **Web application**
4. Add redirect URI: `http://localhost:5000/callback/google`
5. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to your `.env`

**Required Scopes:** `openid`, `email`, `profile`

---

## Rating System

### Tracked Categories

The app tracks ratings across 10 tactical themes:

| Theme Key | Display Name | Description |
|-----------|--------------|-------------|
| `pin` | Pin | Pinning pieces to more valuable ones |
| `fork` | Fork | Attacking multiple pieces at once |
| `mate` | Mate | Checkmate patterns |
| `defensiveMove` | Defense | Defensive tactics |
| `endgame` | Endgame | Endgame positions |
| `deflection` | Deflection | Deflecting defenders |
| `quietMove` | Quiet Move | Non-capturing winning moves |
| `kingsideAttack` | Kingside Attack | Attacking the kingside |
| `discoveredAttack` | Discovered Attack | Discovered attacks |
| `capturingDefender` | Capturing Defender | Removing defenders |

### Elo Calculation

Ratings use a modified Elo system:

```
Expected Score = 1 / (1 + 10^((puzzle_rating - user_rating) / 400))
Rating Change = K × (Actual - Expected)
```

Where:
- **Actual** = 1 for success, 0 for failure
- **K** = K-factor (varies by experience)

### Adaptive K-Factor

The K-factor decreases as you solve more puzzles in a category:

| Attempts | K-Factor | Phase |
|----------|----------|-------|
| 0 | 250 | First attempt |
| 1-2 | 200 | Very early |
| 3-5 | 150 | Learning |
| 6-10 | 100 | Developing |
| 11-20 | 60 | Intermediate |
| 21-35 | 40 | Experienced |
| 35+ | 25 | Established |

### Minimum Rating Change

To ensure meaningful progress, minimum changes are enforced:

| Attempts | Minimum Change |
|----------|----------------|
| 0-5 | ±50 points |
| 6-15 | ±30 points |
| 16+ | ±15 points |

### Rating Bounds

Ratings are clamped between **400** and **2800**.

### Adaptive Puzzle Selection

When logged in, puzzles are selected to target your weaknesses:

1. **Weight categories** by weakness (lower rating = higher weight)
2. **Select category** probabilistically (favoring weak areas)
3. **Match puzzle rating** to your category rating (±200 points preferred)
4. **Weight by closeness** and popularity

```python
# Exponential weighting for stronger bias toward weaknesses
weight = (2800 - rating) ^ 1.3
```

---

## API Reference

### Public Routes

#### `GET /`
Home page. Shows login options or training buttons based on auth state.

#### `GET /login`
Initiates Lichess OAuth flow. Redirects to Lichess.

#### `GET /login/google`
Initiates Google OAuth flow. Redirects to Google.

#### `GET /callback`
Lichess OAuth callback. Exchanges code for token, creates user session.

#### `GET /callback/google`
Google OAuth callback. Exchanges code for token, creates user session.

#### `GET /logout`
Clears user session. Revokes Lichess token if applicable.

#### `GET /puzzle/random/view`
Displays a puzzle to solve.

**Query Parameters:**
- `theme` (optional): Filter by specific theme (e.g., `?theme=fork`)

#### `GET /stats`
Shows user statistics and ratings per category. Requires authentication.

### API Endpoints

#### `POST /api/puzzle/attempt`
Records a puzzle attempt and updates ratings.

**Request:**
```json
{
  "puzzle_id": "abc123",
  "success": true
}
```

**Response:**
```json
{
  "status": "success",
  "rating_changes": [
    {
      "category": "Fork",
      "old_rating": 1500,
      "new_rating": 1550,
      "change": 50,
      "attempts": 1,
      "k_factor": 250
    }
  ],
  "overall_rating": 1608
}
```

**Errors:**
- `401`: Not logged in or no `db_id`
- `400`: Missing `puzzle_id`

#### `POST /api/reset-ratings`
Resets all category ratings to default (1600).

**Response:**
```json
{
  "status": "success",
  "message": "Ratings reset to 1600",
  "new_rating": 1600
}
```

#### `POST /api/admin/reset-all-ratings`
Admin endpoint to reset ALL users' ratings.

**Headers:**
- `X-Admin-Key`: Must match `ADMIN_KEY` environment variable

**Response:**
```json
{
  "status": "success",
  "message": "Reset ratings for 5 users to 1600",
  "users_affected": 5,
  "new_rating": 1600
}
```

---

## Testing

### Running Tests

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # macOS/Linux

# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=server --cov-report=term-missing

# Run specific test file
pytest tests/test_user_manager.py

# Run specific test class
pytest tests/test_puzzle_manager.py::TestGetRandomPuzzle

# Run specific test
pytest tests/test_routes.py::TestGoogleOAuthRoutes::test_google_login_redirects
```

### Test Structure

| File | Description | Tests |
|------|-------------|-------|
| `conftest.py` | Shared fixtures (mock DB, OAuth, puzzles) | - |
| `test_puzzle_manager.py` | Puzzle selection, themes, adaptive logic | 25 |
| `test_db_manager.py` | Database operations, K-factor, ratings | 32 |
| `test_user_manager.py` | Lichess & Google OAuth flows | 29 |
| `test_routes.py` | All Flask route handlers | 28 |
| `test_rating_calculations.py` | Elo math, bounds, consistency | 22 |

**Total: 136 tests**

### Test Coverage

```
Name                       Stmts   Miss  Cover
----------------------------------------------
server/db_manager.py         224     71    68%
server/main.py               194     16    92%
server/puzzle_manager.py     110     19    83%
server/user_manager.py        71      0   100%
----------------------------------------------
TOTAL                        599    106    82%
```

---

## Deployment

### Production Checklist

1. **Set secure secret key**
   ```env
   FLASK_SECRET_KEY=<generate-a-long-random-string>
   ```

2. **Enable secure cookies**
   ```python
   app.config['SESSION_COOKIE_SECURE'] = True  # Requires HTTPS
   ```

3. **Update BASE_URL**
   ```env
   BASE_URL=https://your-domain.com
   ```

4. **Update OAuth redirect URIs** in Lichess and Google consoles

5. **Use a production WSGI server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 server.main:app
   ```

### Environment-Specific Settings

| Setting | Development | Production |
|---------|-------------|------------|
| `FLASK_SECRET_KEY` | Any string | Long random string |
| `SESSION_COOKIE_SECURE` | `False` | `True` |
| `BASE_URL` | `http://localhost:5000` | `https://your-domain.com` |
| Debug mode | `True` | `False` |

---

## Troubleshooting

### Common Issues

**"Session expired or cookies blocked"**
- Enable cookies in your browser
- Check that `SESSION_COOKIE_SAMESITE` is set to `'Lax'`

**"Invalid state parameter"**
- OAuth state mismatch - try logging in again
- May indicate session issues or CSRF attempt

**"Google login is not configured"**
- Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`

**"No puzzles available"**
- Check that `data/filtered_puzzles.csv` exists
- Or ensure puzzles are loaded in Supabase

**Database connection issues**
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Check Supabase dashboard for connection limits

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Puzzle data from [Lichess](https://lichess.org/)
- Chess board rendering with [chessboard.js](https://chessboardjs.com/)
- Chess logic with [chess.js](https://github.com/jhlywa/chess.js)

