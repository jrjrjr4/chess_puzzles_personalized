# server/main.py
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from puzzle_manager import load_puzzles, get_random_puzzle, TRACKED_THEMES, get_tracked_themes_for_puzzle, get_theme_display_name
from db_manager import DBManager
from user_manager import UserManager, GoogleOAuth
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='../static', static_url_path='/static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'super-secret-key')

# Configure session cookies for OAuth compatibility
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow cookies on OAuth redirects
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Initialize managers first
db_manager = DBManager()
user_manager = UserManager()
google_oauth = GoogleOAuth()

# Load puzzles - tries Supabase first, falls back to CSV
puzzles = load_puzzles(db_manager)


DEFAULT_RATING = 1600  # Starting rating for all categories


def calculate_overall_rating(stored_ratings):
    """Calculate average rating across tracked categories, filling missing values."""
    ratings = [stored_ratings.get(theme, DEFAULT_RATING) for theme in TRACKED_THEMES]
    return sum(ratings) // len(ratings)


def get_overall_rating(user_id):
    """
    Get the user's independent overall rating from the database.
    This is a separate rating that updates with each puzzle using Elo.
    """
    if not user_id:
        return DEFAULT_RATING
    data = db_manager.get_user_overall_rating(user_id)
    return data['rating']


def get_all_user_ratings(stored_ratings):
    """
    Get ratings for all 10 categories with display names.
    Returns dict mapping display_name -> rating.
    """
    user_ratings = {}
    for theme_key, display_name in TRACKED_THEMES.items():
        user_ratings[display_name] = stored_ratings.get(theme_key, DEFAULT_RATING)
    return user_ratings


@app.route('/')
def index():
    user = session.get('user')
    google_enabled = google_oauth.is_configured()
    return render_template('index.html', user=user, google_enabled=google_enabled)


@app.route('/login')
def login():
    """Redirect to Lichess OAuth login with PKCE."""
    # Generate PKCE code verifier and challenge
    code_verifier, code_challenge = user_manager.generate_pkce_pair()
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store in session for verification in callback
    session['oauth_code_verifier'] = code_verifier
    session['oauth_state'] = state
    
    # Redirect to Lichess
    login_url = user_manager.get_login_url(code_challenge, state)
    return redirect(login_url)


@app.route('/callback')
def oauth_callback():
    """Handle OAuth callback from Lichess."""
    # Check for errors
    error = request.args.get('error')
    if error:
        error_desc = request.args.get('error_description', 'Unknown error')
        return render_template('error.html', error=f"Login failed: {error_desc}"), 400
    
    # Verify state to prevent CSRF
    state = request.args.get('state')
    stored_state = session.get('oauth_state')  # Don't pop yet, for debugging
    
    # Debug logging
    print(f"OAuth callback - received state: {state}")
    print(f"OAuth callback - stored state: {stored_state}")
    print(f"OAuth callback - session keys: {list(session.keys())}")
    
    if not state or state != stored_state:
        # More helpful error message
        if not stored_state:
            return render_template('error.html', error="Session expired or cookies blocked. Please enable cookies and try logging in again."), 400
        return render_template('error.html', error="Invalid state parameter. Please try logging in again."), 400
    
    # Now pop the state since verification passed
    session.pop('oauth_state', None)
    
    # Get the authorization code
    code = request.args.get('code')
    if not code:
        return render_template('error.html', error="No authorization code received."), 400
    
    # Get the stored code verifier
    code_verifier = session.pop('oauth_code_verifier', None)
    if not code_verifier:
        return render_template('error.html', error="Session expired. Please try logging in again."), 400
    
    # Exchange code for token
    token_data = user_manager.handle_callback(code, code_verifier)
    if not token_data:
        return render_template('error.html', error="Failed to get access token from Lichess."), 400
    
    access_token = token_data.get('access_token')
    
    # Get user info from Lichess
    lichess_user = user_manager.get_user_info(access_token)
    if not lichess_user:
        return render_template('error.html', error="Failed to get user info from Lichess."), 400
    
    # Create or get user in our database
    db_user = db_manager.get_or_create_user(lichess_user)
    
    if not db_user:
        return render_template('error.html', error="Failed to create user account. Please try again later."), 500
    
    # Store user in session
    user_data = {
        'id': lichess_user.get('id'),
        'username': lichess_user.get('username'),
        'access_token': access_token,  # Store for potential API calls or logout
        'db_id': db_user['id']
    }
    
    session['user'] = user_data
    
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """Logout user and optionally revoke Lichess token."""
    user = session.get('user')
    if user and user.get('access_token') and user.get('provider') != 'google':
        # Revoke the Lichess token (Google tokens don't need revocation for this app)
        user_manager.revoke_token(user['access_token'])
    
    session.pop('user', None)
    return redirect(url_for('index'))


# ==================== GOOGLE OAUTH ROUTES ====================

@app.route('/login/google')
def google_login():
    """Redirect to Google OAuth login."""
    if not google_oauth.is_configured():
        return render_template('error.html', error="Google login is not configured."), 500
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session['google_oauth_state'] = state
    
    login_url = google_oauth.get_login_url(state)
    return redirect(login_url)


@app.route('/callback/google')
def google_callback():
    """Handle OAuth callback from Google."""
    # Check for errors
    error = request.args.get('error')
    if error:
        error_desc = request.args.get('error_description', 'Unknown error')
        return render_template('error.html', error=f"Google login failed: {error_desc}"), 400
    
    # Verify state to prevent CSRF
    state = request.args.get('state')
    stored_state = session.get('google_oauth_state')
    
    if not state or state != stored_state:
        if not stored_state:
            return render_template('error.html', error="Session expired or cookies blocked. Please enable cookies and try logging in again."), 400
        return render_template('error.html', error="Invalid state parameter. Please try logging in again."), 400
    
    session.pop('google_oauth_state', None)
    
    # Get the authorization code
    code = request.args.get('code')
    if not code:
        return render_template('error.html', error="No authorization code received from Google."), 400
    
    # Exchange code for user info
    google_user = google_oauth.handle_callback(code)
    if not google_user:
        return render_template('error.html', error="Failed to get user info from Google."), 400
    
    # Create or get user in our database
    db_user = db_manager.get_or_create_google_user(google_user)
    
    if not db_user:
        return render_template('error.html', error="Failed to create user account. Please try again later."), 500
    
    # Store user in session
    user_data = {
        'id': google_user.get('sub'),  # Google's unique user ID
        'username': google_user.get('name', google_user.get('email', 'Google User')),
        'email': google_user.get('email'),
        'picture': google_user.get('picture'),
        'provider': 'google',
        'db_id': db_user['id']
    }
    
    session['user'] = user_data
    
    return redirect(url_for('index'))


@app.route('/api/puzzle/attempt', methods=['POST'])
def record_attempt():
    user = session.get('user')
    if not user or 'db_id' not in user:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
    puzzle_id = data.get('puzzle_id')
    success = data.get('success')
    
    if not puzzle_id:
        return jsonify({'status': 'error', 'message': 'Missing puzzle_id'}), 400
    
    # Convert puzzle_id to string for consistent comparison
    puzzle_id = str(puzzle_id)
    
    # Record the attempt
    db_manager.save_puzzle_attempt(user['db_id'], puzzle_id, success)
    
    # Find the puzzle
    puzzle = next((p for p in puzzles if str(p['id']) == puzzle_id), None)
    rating_changes = []
    puzzle_rating = DEFAULT_RATING
    
    if puzzle:
        tracked_themes = get_tracked_themes_for_puzzle(puzzle['themes'])
        puzzle_rating = puzzle.get('rating', 1200)
        
        for theme in tracked_themes:
            result = db_manager.update_user_category_rating(
                user['db_id'], 
                theme, 
                success, 
                puzzle_rating
            )
            if result:
                rating_changes.append({
                    'category': get_theme_display_name(theme),
                    'old_rating': result['old_rating'],
                    'new_rating': result['new_rating'],
                    'change': result['change'],
                    'attempts': result['attempts'],
                    'k_factor': result['k_factor']
                })
    
    # Update overall rating independently (its own Elo rating)
    overall_result = db_manager.update_user_overall_rating(
        user['db_id'],
        success,
        puzzle_rating
    )
    
    overall_rating = DEFAULT_RATING
    overall_change = None
    if isinstance(overall_result, dict):
        overall_rating = overall_result['new_rating']
        overall_change = {
            'old_rating': overall_result['old_rating'],
            'new_rating': overall_result['new_rating'],
            'change': overall_result['change'],
            'k_factor': overall_result['k_factor']
        }
            
    return jsonify({
        'status': 'success',
        'rating_changes': rating_changes,
        'overall_rating': overall_rating,
        'overall_change': overall_change
    })


@app.route('/puzzle/random/view')
def random_puzzle_view():
    """Route to display a random puzzle in HTML form."""
    user = session.get('user')
    theme = request.args.get('theme')
    
    # Get stored ratings from DB
    stored_ratings = {}
    overall_rating = DEFAULT_RATING
    if user and 'db_id' in user:
        stored_ratings = db_manager.get_user_category_ratings(user['db_id'])
        overall_rating = get_overall_rating(user['db_id'])
    
    # Build ratings dict with all 10 categories
    user_ratings = get_all_user_ratings(stored_ratings)
    
    # Select puzzle
    puzzle = None
    if user and 'db_id' in user and not theme:
        from puzzle_manager import get_adaptive_puzzle
        puzzle = get_adaptive_puzzle(puzzles, stored_ratings)
    else:
        puzzle = get_random_puzzle(puzzles, theme_filter=theme)
    
    # Fallbacks
    if not puzzle:
        puzzle = get_random_puzzle(puzzles)
    if not puzzle:
        return "No puzzles available", 500
    
    # Get tracked themes for this puzzle (with display names)
    puzzle_tracked_themes = [TRACKED_THEMES[t] for t in puzzle['themes'] if t in TRACKED_THEMES]
        
    return render_template('puzzle.html', 
                         puzzle=puzzle, 
                         user=user, 
                         user_ratings=user_ratings,
                         overall_rating=overall_rating,
                         puzzle_tracked_themes=puzzle_tracked_themes)


@app.route('/stats')
def stats():
    """Show user statistics and ratings per category."""
    user = session.get('user')
    if not user or 'db_id' not in user:
        return redirect(url_for('login'))
    
    # Get stored ratings from DB
    stored_ratings = db_manager.get_user_category_ratings(user['db_id'])
    overall_rating = get_overall_rating(user['db_id'])
    
    # Build full list with all 10 categories (using display names)
    all_ratings = []
    for theme_key, display_name in TRACKED_THEMES.items():
        rating = stored_ratings.get(theme_key, DEFAULT_RATING)
        all_ratings.append((display_name, rating))
    
    # Sort by rating (lowest first - weaknesses)
    sorted_ratings = sorted(all_ratings, key=lambda x: x[1])
    
    return render_template('stats.html', 
                         user=user, 
                         category_ratings=sorted_ratings,
                         overall_rating=overall_rating)


@app.route('/api/reset-ratings', methods=['POST'])
def reset_ratings():
    """Reset current user's ratings to default (1600)."""
    user = session.get('user')
    if not user or 'db_id' not in user:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    success = db_manager.reset_user_ratings(user['db_id'])
    if success:
        return jsonify({
            'status': 'success', 
            'message': f'Ratings reset to {DEFAULT_RATING}',
            'new_rating': DEFAULT_RATING
        })
    else:
        return jsonify({'status': 'error', 'message': 'Failed to reset ratings'}), 500


@app.route('/api/admin/reset-all-ratings', methods=['POST'])
def admin_reset_all_ratings():
    """Admin endpoint to reset ALL users' ratings. Use with caution!"""
    # Simple admin check - in production you'd want proper auth
    admin_key = request.headers.get('X-Admin-Key')
    expected_key = os.environ.get('ADMIN_KEY', 'dev-admin-key')
    
    if admin_key != expected_key:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    count = db_manager.reset_all_user_ratings()
    return jsonify({
        'status': 'success',
        'message': f'Reset ratings for {count} users to {DEFAULT_RATING}',
        'users_affected': count,
        'new_rating': DEFAULT_RATING
    })


if __name__ == '__main__':
    app.run(debug=True)
