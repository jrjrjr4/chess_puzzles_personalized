# Documentation Index

Welcome to the Chess Puzzles Personalized documentation!

## Quick Links

| Document | Description |
|----------|-------------|
| [Main README](../README.md) | Project overview, features, quick start |
| [Setup Guide](./SETUP.md) | Step-by-step installation instructions |
| [API Reference](./API.md) | All routes and endpoints |
| [OAuth Guide](./OAUTH.md) | Authentication setup (Lichess & Google) |
| [Rating System](./RATING_SYSTEM.md) | How ratings and adaptive selection work |
| [Development Guide](./DEVELOPMENT.md) | Contributing, code standards, testing |

## Getting Started

**New to the project?** Start here:

1. Read the [Main README](../README.md) for an overview
2. Follow the [Setup Guide](./SETUP.md) to get running
3. Check [OAuth Guide](./OAUTH.md) to enable login

**Want to understand the rating system?**

→ [Rating System](./RATING_SYSTEM.md) explains the Elo calculations, K-factors, and adaptive puzzle selection.

**Building an integration?**

→ [API Reference](./API.md) documents all endpoints with request/response examples.

**Contributing code?**

→ [Development Guide](./DEVELOPMENT.md) covers code standards, testing, and workflows.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Flask Application                       │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Routes  │  │   OAuth  │  │  Puzzles │  │ Ratings  │    │
│  │ main.py  │  │user_mgr  │  │puzzle_mgr│  │ db_mgr   │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │             │             │             │           │
│       └─────────────┴─────────────┴─────────────┘           │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   Supabase    │
                    │  (PostgreSQL) │
                    └───────────────┘
```

## Key Concepts

### Tracked Themes

The app tracks ratings across 10 tactical categories:
- Pin, Fork, Mate, Defense, Endgame
- Deflection, Quiet Move, Kingside Attack
- Discovered Attack, Capturing Defender

### Adaptive Selection

Puzzles are selected to target your weaknesses:
1. Categories weighted by how weak you are
2. Random category chosen (favoring weak areas)
3. Puzzle matched to your rating in that category

### Elo Rating

Modified Elo system with:
- Adaptive K-factor (decreases with experience)
- Minimum rating changes (ensures progress)
- Per-category tracking

## File Structure

```
chess_puzzles_personalized/
├── README.md              ← Start here
├── docs/
│   ├── README.md          ← You are here
│   ├── SETUP.md           ← Installation
│   ├── API.md             ← Endpoints
│   ├── OAUTH.md           ← Authentication
│   ├── RATING_SYSTEM.md   ← Ratings explained
│   └── DEVELOPMENT.md     ← Contributing
├── server/                ← Backend code
├── static/                ← CSS, JS
├── tests/                 ← Test suite
└── data/                  ← Puzzle data
```

## Need Help?

1. Check the relevant documentation above
2. Look at existing code for examples
3. Run tests to verify your setup: `pytest tests/`
4. Open an issue on GitHub

