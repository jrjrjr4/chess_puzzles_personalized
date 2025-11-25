# Development Guide

This guide covers development workflows, code organization, and best practices for contributing to Chess Puzzles Personalized.

## Development Setup

### Prerequisites

- Python 3.9+
- Git
- A code editor (VS Code recommended)
- PowerShell (Windows) or Bash (macOS/Linux)

### Initial Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd chess_puzzles_personalized

# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env  # Or create manually
```

### Running the App

```bash
cd server
python main.py
```

The app runs at `http://localhost:5000` with debug mode enabled.

### Running Tests

```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=server --cov-report=html

# Specific file
pytest tests/test_puzzle_manager.py

# Specific test
pytest tests/test_routes.py::TestIndexRoute::test_index_not_logged_in -v
```

---

## Code Organization

### Directory Structure

```
chess_puzzles_personalized/
├── server/                 # Backend Python code
│   ├── main.py            # Flask app, routes, view logic
│   ├── db_manager.py      # All database operations
│   ├── user_manager.py    # OAuth handlers
│   ├── puzzle_manager.py  # Puzzle selection logic
│   └── templates/         # Jinja2 templates
├── static/                # CSS, JS, images
├── tests/                 # Test suite
├── docs/                  # Documentation
├── data/                  # Puzzle CSV data
└── supabase/              # Database migrations
```

### Module Responsibilities

#### `main.py`
- Flask app initialization
- Route definitions
- Request/response handling
- Session management
- View logic (what data to pass to templates)

**Should NOT contain**: Database queries, OAuth logic, puzzle algorithms

#### `db_manager.py`
- All Supabase interactions
- User CRUD operations
- Rating calculations and updates
- Puzzle retrieval from database

**Should NOT contain**: Route handling, session logic, OAuth

#### `user_manager.py`
- OAuth flow implementation
- PKCE generation (Lichess)
- Token exchange
- User info fetching

**Should NOT contain**: Database operations, route handling

#### `puzzle_manager.py`
- Puzzle loading (from DB or CSV)
- Random puzzle selection
- Adaptive puzzle selection
- Theme filtering and matching

**Should NOT contain**: Database writes, user management

---

## Coding Standards

### Python Style

We follow PEP 8 with these specifics:

```python
# Imports: stdlib, third-party, local (separated by blank lines)
import os
import secrets

from flask import Flask, session
import requests

from db_manager import DBManager

# Constants: UPPER_SNAKE_CASE
DEFAULT_RATING = 1600
TRACKED_THEMES = {...}

# Functions: snake_case
def get_random_puzzle(puzzle_list, theme_filter=None):
    pass

# Classes: PascalCase
class DBManager:
    pass

# Private methods: leading underscore
def _calculate_weight(rating):
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def get_rating_matched_puzzle(puzzle_list, theme, user_rating, rating_range=200):
    """
    Selects a puzzle matching the user's rating in a given theme.
    
    Args:
        puzzle_list: List of puzzle dictionaries
        theme: Theme to filter by (e.g., 'fork')
        user_rating: User's current rating in this theme
        rating_range: Acceptable rating difference (default 200)
    
    Returns:
        A puzzle dict, or None if no matching puzzle found
    
    Example:
        puzzle = get_rating_matched_puzzle(puzzles, 'fork', 1500)
    """
```

### Type Hints (Optional but Encouraged)

```python
def calculate_k_factor(attempts: int) -> int:
    """Calculate K-factor based on attempt count."""
    if attempts <= 0:
        return 250
    # ...
```

---

## Testing Guidelines

### Test Structure

Each test file mirrors a source file:
- `server/puzzle_manager.py` → `tests/test_puzzle_manager.py`
- `server/db_manager.py` → `tests/test_db_manager.py`

### Test Organization

```python
class TestFeatureName:
    """Tests for a specific feature or function."""
    
    def test_happy_path(self):
        """Test normal/expected behavior."""
        pass
    
    def test_edge_case(self):
        """Test boundary conditions."""
        pass
    
    def test_error_handling(self):
        """Test error conditions."""
        pass
```

### Fixtures

Use fixtures from `conftest.py`:

```python
def test_something(sample_puzzles, mock_db_manager):
    """Test using shared fixtures."""
    mock_db_manager.get_all_puzzles.return_value = sample_puzzles
    # ...
```

### Mocking

Mock external dependencies:

```python
from unittest.mock import patch, MagicMock

@patch('server.user_manager.requests.post')
def test_token_exchange(self, mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'access_token': 'token'}
    # ...
```

### Test Naming

```python
def test_<function>_<scenario>_<expected_result>(self):
    pass

# Examples:
def test_get_random_puzzle_with_theme_filter_returns_matching_puzzle(self):
def test_update_rating_failure_decreases_rating(self):
def test_login_without_credentials_returns_401(self):
```

---

## Database Development

### Local Development

For local development, you can:

1. **Use Supabase** (recommended): Create a free project
2. **Use CSV only**: App works without DB (no user persistence)
3. **Use local PostgreSQL**: Point `SUPABASE_URL` to local instance

### Migrations

Database changes go in `supabase/migrations/`:

```sql
-- supabase/migrations/20250126000001_add_new_column.sql
ALTER TABLE users ADD COLUMN new_field TEXT;
```

Run migrations in Supabase SQL Editor or via CLI.

### Schema Changes

1. Update `schema.sql` with the new schema
2. Create a migration file for existing databases
3. Update `db_manager.py` if needed
4. Update tests
5. Update documentation

---

## Adding New Features

### Adding a New Route

1. **Define the route in `main.py`**:
```python
@app.route('/new-feature')
def new_feature():
    user = session.get('user')
    # ... logic ...
    return render_template('new_feature.html', data=data)
```

2. **Create the template** in `server/templates/new_feature.html`

3. **Add tests** in `tests/test_routes.py`:
```python
class TestNewFeature:
    def test_new_feature_returns_200(self, app_client):
        response = app_client.get('/new-feature')
        assert response.status_code == 200
```

### Adding a New API Endpoint

1. **Define the endpoint**:
```python
@app.route('/api/new-endpoint', methods=['POST'])
def new_endpoint():
    user = session.get('user')
    if not user:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    data = request.json
    # ... process ...
    return jsonify({'status': 'success', 'result': result})
```

2. **Add tests**:
```python
def test_new_endpoint_success(self, logged_in_client):
    response = logged_in_client.post('/api/new-endpoint', 
                                     json={'key': 'value'})
    assert response.status_code == 200
```

3. **Document in `docs/API.md`**

### Adding a New Tracked Theme

1. **Update `TRACKED_THEMES` in `puzzle_manager.py`**:
```python
TRACKED_THEMES = {
    # ... existing ...
    'newTheme': 'New Theme Display Name',
}
```

2. **Update tests** to expect 11 themes instead of 10

3. **Update documentation**

---

## Debugging

### Flask Debug Mode

Debug mode is enabled by default in development:
```python
if __name__ == '__main__':
    app.run(debug=True)
```

This provides:
- Auto-reload on code changes
- Detailed error pages
- Interactive debugger

### Logging

Add logging for debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In your code
logging.debug(f"Processing puzzle {puzzle_id}")
logging.error(f"Failed to fetch user: {e}")
```

### Session Debugging

Print session contents:
```python
@app.route('/debug-session')
def debug_session():
    return jsonify(dict(session))
```

**Warning**: Remove before production!

### Database Debugging

Check Supabase dashboard:
1. Go to your project
2. Click **Table Editor**
3. View/edit data directly

---

## Common Tasks

### Updating Dependencies

```bash
# Update a specific package
pip install --upgrade flask

# Update requirements.txt
pip freeze > requirements.txt

# Or manually edit and reinstall
pip install -r requirements.txt
```

### Running a Single Test

```bash
pytest tests/test_puzzle_manager.py::TestGetRandomPuzzle::test_get_random_puzzle_returns_puzzle -v
```

### Checking Test Coverage

```bash
pytest tests/ --cov=server --cov-report=html
# Open htmlcov/index.html in browser
```

### Formatting Code

```bash
# Install black (optional)
pip install black

# Format all Python files
black server/ tests/
```

---

## Git Workflow

### Branch Naming

- `feature/add-google-oauth`
- `fix/session-expiry-bug`
- `docs/update-readme`

### Commit Messages

```
type: short description

Longer explanation if needed.

- Bullet points for multiple changes
- Reference issues: Fixes #123
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `style`

### Pull Request Checklist

- [ ] Tests pass (`pytest tests/`)
- [ ] New code has tests
- [ ] Documentation updated
- [ ] No linting errors
- [ ] Commits are clean and descriptive

