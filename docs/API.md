# API Reference

This document describes all routes and API endpoints in the Chess Puzzles Personalized application.

## Base URL

- **Development**: `http://localhost:5000`
- **Production**: Your deployed domain

## Authentication

Most API endpoints require authentication via session cookies. Users authenticate through OAuth (Lichess or Google), which creates a session.

### Session Data

After successful login, the session contains:

```python
session['user'] = {
    'id': 'lichess-username',        # or Google sub ID
    'username': 'DisplayName',
    'db_id': 'uuid-from-database',   # Required for API calls
    'access_token': 'oauth-token',   # For Lichess only
    'provider': 'lichess',           # or 'google'
    'email': 'user@gmail.com',       # Google only
    'picture': 'https://...',        # Google only
}
```

---

## Page Routes

### `GET /`

**Home Page**

Displays the landing page with login options or training buttons.

**Response**: HTML page

**Behavior**:
- Not logged in: Shows Lichess and Google login buttons
- Logged in: Shows "Continue Training" and "View Stats" buttons

---

### `GET /login`

**Initiate Lichess OAuth**

Redirects to Lichess for authentication using PKCE flow.

**Response**: 302 Redirect to `https://lichess.org/oauth`

**Session Effects**:
- Stores `oauth_code_verifier` (PKCE)
- Stores `oauth_state` (CSRF protection)

---

### `GET /login/google`

**Initiate Google OAuth**

Redirects to Google for authentication.

**Response**: 
- 302 Redirect to `https://accounts.google.com/o/oauth2/v2/auth`
- 500 Error if Google OAuth not configured

**Session Effects**:
- Stores `google_oauth_state` (CSRF protection)

---

### `GET /callback`

**Lichess OAuth Callback**

Handles the redirect from Lichess after user authorization.

**Query Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| `code` | Yes | Authorization code from Lichess |
| `state` | Yes | State parameter for CSRF validation |
| `error` | No | Error code if authorization failed |
| `error_description` | No | Human-readable error message |

**Response**:
- Success: 302 Redirect to `/`
- Error: 400 with error page

**Possible Errors**:
- "Login failed: {error_description}" - User denied or Lichess error
- "Session expired or cookies blocked" - No stored state in session
- "Invalid state parameter" - State mismatch (possible CSRF)
- "No authorization code received" - Missing code parameter
- "Failed to get access token" - Token exchange failed
- "Failed to get user info" - Lichess API error

---

### `GET /callback/google`

**Google OAuth Callback**

Handles the redirect from Google after user authorization.

**Query Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| `code` | Yes | Authorization code from Google |
| `state` | Yes | State parameter for CSRF validation |
| `error` | No | Error code if authorization failed |
| `error_description` | No | Human-readable error message |

**Response**:
- Success: 302 Redirect to `/`
- Error: 400 with error page

---

### `GET /logout`

**Logout User**

Clears the user session and revokes OAuth tokens.

**Response**: 302 Redirect to `/`

**Behavior**:
- Revokes Lichess token (if Lichess user)
- Clears session

---

### `GET /puzzle/random/view`

**Puzzle Page**

Displays a puzzle for the user to solve.

**Query Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| `theme` | No | Filter puzzles by theme (e.g., `fork`, `pin`) |

**Response**: HTML page with puzzle interface

**Behavior**:
- Logged in (no theme): Uses adaptive puzzle selection based on weaknesses
- Logged in (with theme): Random puzzle from that theme
- Not logged in: Random puzzle (with optional theme filter)

**Page Data**:
- Puzzle FEN, moves, rating, themes
- User's category ratings (if logged in)
- Overall rating (if logged in)

---

### `GET /stats`

**Statistics Page**

Shows the user's ratings across all categories.

**Authentication**: Required

**Response**: 
- 200: HTML page with statistics
- 302: Redirect to `/login` if not authenticated

**Page Data**:
- Category ratings sorted by rating (weakest first)
- Overall rating
- Display names for all categories

---

## API Endpoints

### `POST /api/puzzle/attempt`

**Record Puzzle Attempt**

Records whether the user solved a puzzle and updates their ratings.

**Authentication**: Required (must have `db_id` in session)

**Request Body** (JSON):
```json
{
  "puzzle_id": "abc123",
  "success": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `puzzle_id` | string | Yes | ID of the attempted puzzle |
| `success` | boolean | Yes | Whether the puzzle was solved |

**Response** (200 OK):
```json
{
  "status": "success",
  "rating_changes": [
    {
      "category": "Fork",
      "old_rating": 1500,
      "new_rating": 1550,
      "change": 50,
      "attempts": 5,
      "k_factor": 150
    },
    {
      "category": "Pin",
      "old_rating": 1600,
      "new_rating": 1630,
      "change": 30,
      "attempts": 12,
      "k_factor": 60
    }
  ],
  "overall_rating": 1608
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always "success" on 200 |
| `rating_changes` | array | Changes for each affected category |
| `rating_changes[].category` | string | Display name of the category |
| `rating_changes[].old_rating` | int | Rating before this attempt |
| `rating_changes[].new_rating` | int | Rating after this attempt |
| `rating_changes[].change` | int | Points gained/lost |
| `rating_changes[].attempts` | int | Total attempts in this category |
| `rating_changes[].k_factor` | int | K-factor used for this calculation |
| `overall_rating` | int | New overall rating (average of all 10) |

**Error Responses**:

401 Unauthorized:
```json
{
  "status": "error",
  "message": "Not logged in"
}
```

400 Bad Request:
```json
{
  "status": "error",
  "message": "No data provided"
}
```

```json
{
  "status": "error",
  "message": "Missing puzzle_id"
}
```

---

### `POST /api/reset-ratings`

**Reset User Ratings**

Resets all of the current user's category ratings to the default (1600).

**Authentication**: Required

**Request Body**: None

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Ratings reset to 1600",
  "new_rating": 1600
}
```

**Error Responses**:

401 Unauthorized:
```json
{
  "status": "error",
  "message": "Not logged in"
}
```

500 Internal Server Error:
```json
{
  "status": "error",
  "message": "Failed to reset ratings"
}
```

---

### `POST /api/admin/reset-all-ratings`

**Admin: Reset All User Ratings**

Resets ratings for ALL users in the database. Use with caution!

**Authentication**: Admin key required

**Request Headers**:
| Header | Required | Description |
|--------|----------|-------------|
| `X-Admin-Key` | Yes | Must match `ADMIN_KEY` environment variable |

**Request Body**: None

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Reset ratings for 5 users to 1600",
  "users_affected": 5,
  "new_rating": 1600
}
```

**Error Responses**:

403 Forbidden:
```json
{
  "status": "error",
  "message": "Unauthorized"
}
```

---

## Data Models

### User Object

```typescript
interface User {
  id: string;           // UUID
  lichess_id?: string;  // Lichess username (null for Google users)
  lichess_username?: string;
  google_id?: string;   // Google sub ID (null for Lichess users)
  google_email?: string;
  google_name?: string;
  provider: 'lichess' | 'google';
  created_at: string;   // ISO 8601 timestamp
}
```

### Puzzle Object

```typescript
interface Puzzle {
  id: string;           // Puzzle ID (e.g., "00sHx")
  fen: string;          // FEN position
  moves: string[];      // Solution moves
  rating: number;       // Puzzle difficulty rating
  themes: string[];     // Tactical themes
  popularity: number;   // Popularity score (0-100)
}
```

### Category Rating Object

```typescript
interface CategoryRating {
  user_id: string;      // UUID
  category: string;     // Theme key (e.g., "fork")
  rating: number;       // Current rating
  attempts: number;     // Total attempts in category
  updated_at: string;   // ISO 8601 timestamp
}
```

### Rating Change Object

```typescript
interface RatingChange {
  category: string;     // Display name (e.g., "Fork")
  old_rating: number;
  new_rating: number;
  change: number;       // Can be positive or negative
  attempts: number;     // Attempts after this change
  k_factor: number;     // K-factor used
}
```

---

## Error Handling

All API errors return JSON with this structure:

```json
{
  "status": "error",
  "message": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 302 | Redirect (OAuth flows) |
| 400 | Bad Request (missing/invalid parameters) |
| 401 | Unauthorized (not logged in) |
| 403 | Forbidden (invalid admin key) |
| 500 | Internal Server Error |

---

## Rate Limiting

Currently, there is no rate limiting implemented. For production deployments, consider adding rate limiting via:
- Nginx/Apache configuration
- Flask-Limiter extension
- Cloudflare or similar CDN

---

## CORS

The API does not set CORS headers by default. If you need to access the API from a different domain, add Flask-CORS:

```python
from flask_cors import CORS
CORS(app, origins=['https://your-frontend.com'])
```

