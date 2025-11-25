# server/main.py
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from puzzle_manager import load_puzzles, get_random_puzzle, TRACKED_THEMES, get_tracked_themes_for_puzzle, get_theme_display_name
from db_manager import DBManager
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='../static', static_url_path='/static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'super-secret-key')

puzzles = load_puzzles()
db_manager = DBManager()


def calculate_overall_rating(stored_ratings):
    """
    Calculate overall rating consistently across the app.
    Always uses all 10 tracked themes, defaulting to 1200 for missing ones.
    """
    total = 0
    for theme_key in TRACKED_THEMES.keys():
        total += stored_ratings.get(theme_key, 1200)
    return total // len(TRACKED_THEMES)


def get_all_user_ratings(stored_ratings):
    """
    Get ratings for all 10 categories with display names.
    Returns dict mapping display_name -> rating.
    """
    user_ratings = {}
    for theme_key, display_name in TRACKED_THEMES.items():
        user_ratings[display_name] = stored_ratings.get(theme_key, 1200)
    return user_ratings


@app.route('/')
def index():
    user = session.get('user')
    return render_template('index.html', user=user)


@app.route('/login')
def login():
    """Simple local login - creates/gets a test user."""
    test_user_data = {
        'id': 'local_user',
        'username': 'TestPlayer'
    }
    db_user = db_manager.get_or_create_user(test_user_data)
    if db_user:
        test_user_data['db_id'] = db_user['id']
    
    session['user'] = test_user_data
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user', None)
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
    
    # Calculate overall rating consistently (using all 10 categories)
    updated_ratings = db_manager.get_user_category_ratings(user['db_id'])
    overall_rating = calculate_overall_rating(updated_ratings)
            
    return jsonify({
        'status': 'success',
        'rating_changes': rating_changes,
        'overall_rating': overall_rating
    })


@app.route('/puzzle/random/view')
def random_puzzle_view():
    """Route to display a random puzzle in HTML form."""
    user = session.get('user')
    theme = request.args.get('theme')
    
    # Get stored ratings from DB
    stored_ratings = {}
    if user and 'db_id' in user:
        stored_ratings = db_manager.get_user_category_ratings(user['db_id'])
    
    # Build ratings dict with all 10 categories
    user_ratings = get_all_user_ratings(stored_ratings)
    
    # Calculate overall rating consistently
    overall_rating = calculate_overall_rating(stored_ratings)
    
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
    
    # Build full list with all 10 categories (using display names)
    all_ratings = []
    for theme_key, display_name in TRACKED_THEMES.items():
        rating = stored_ratings.get(theme_key, 1200)
        all_ratings.append((display_name, rating))
    
    # Sort by rating (lowest first - weaknesses)
    sorted_ratings = sorted(all_ratings, key=lambda x: x[1])
    
    # Calculate overall rating consistently
    overall_rating = calculate_overall_rating(stored_ratings)
    
    return render_template('stats.html', 
                         user=user, 
                         category_ratings=sorted_ratings,
                         overall_rating=overall_rating)


if __name__ == '__main__':
    app.run(debug=True)
