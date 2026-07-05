import csv
import os

# server/puzzle_manager.py

DEFAULT_RATING = 1600  # Starting rating for all categories

# The 10 core tactical themes we track ratings for
# Maps from Lichess theme names to display names
TRACKED_THEMES = {
    'pin': 'Pin',
    'fork': 'Fork',
    'mate': 'Mate',
    'defensiveMove': 'Defense',
    'endgame': 'Endgame',
    'deflection': 'Deflection',
    'quietMove': 'Quiet Move',
    'kingsideAttack': 'Kingside Attack',
    'discoveredAttack': 'Discovered Attack',
    'capturingDefender': 'Capturing Defender'
}

def get_tracked_themes_for_puzzle(puzzle_themes):
    """Returns only the tracked themes from a puzzle's theme list."""
    return [t for t in puzzle_themes if t in TRACKED_THEMES]

def get_theme_display_name(theme):
    """Returns the display name for a theme."""
    return TRACKED_THEMES.get(theme, theme)

def load_puzzles(db_manager=None):
    """
    Load puzzles from the bundled CSV if present, otherwise from Supabase.

    CSV-first keeps startup fast (one file read instead of ~60 paginated
    requests) and lets the app serve puzzles even when the Supabase
    project is paused — the database is only required for accounts,
    attempts and ratings.

    Args:
        db_manager: Optional DBManager instance for Supabase access

    Returns:
        List of puzzle dictionaries
    """
    puzzles = load_puzzles_from_csv()
    if puzzles:
        return puzzles

    print("No local puzzle CSV, falling back to Supabase")
    if db_manager and db_manager.client:
        puzzles = db_manager.get_all_puzzles()
        if puzzles:
            print(f"Loaded {len(puzzles)} puzzles from Supabase")
            return puzzles

    return []

def load_puzzles_from_csv():
    """Load puzzles from the local CSV file."""
    puzzle_list = []
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(BASE_DIR, '../data/filtered_puzzles.csv')

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert Themes (space-separated in Lichess CSV)
                themes_str = row.get('Themes', '')
                themes_list = themes_str.split() if themes_str else []

                # Convert popularity (default to 0 if missing)
                popularity = int(row.get('Popularity', 0))

                puzzle = {
                    'id': row.get('PuzzleId', ''),
                    'fen': row.get('FEN', ''),
                    'moves': row.get('Moves', '').split(),
                    'rating': int(row.get('Rating', DEFAULT_RATING)),
                    'themes': themes_list,
                    'popularity': popularity
                }
                puzzle_list.append(puzzle)
        print(f"Loaded {len(puzzle_list)} puzzles from CSV")
    except FileNotFoundError:
        print(f"Warning: CSV file not found at {data_file}")
    
    return puzzle_list


def _drop_excluded(candidates, exclude_ids):
    """Returns candidates not in exclude_ids; falls back to the full list
    rather than returning nothing (repeats beat no puzzle at all)."""
    if not exclude_ids:
        return candidates
    fresh = [p for p in candidates if p['id'] not in exclude_ids]
    return fresh if fresh else candidates


def get_random_puzzle(puzzle_list, theme_filter=None, exclude_ids=None):
    """
    Returns a uniformly random puzzle, optionally filtered by theme and
    excluding already-seen puzzle ids. The pool is popularity-curated at
    build time, so selection itself is unweighted — per-pick popularity
    weighting concentrated picks on the same few puzzles.
    """
    import random

    # Filter by theme if requested
    candidates = puzzle_list
    if theme_filter:
        candidates = [p for p in puzzle_list if theme_filter in p['themes']]
    if not candidates:
        return None

    candidates = _drop_excluded(candidates, exclude_ids)
    return random.choice(candidates)


def get_rating_matched_puzzle(puzzle_list, theme, user_rating, rating_range=200, exclude_ids=None):
    """
    Selects a puzzle from the given theme near the user's rating, preferring
    puzzles the user hasn't attempted. Fallback ladder: rating window minus
    seen -> widened window minus seen -> whole theme minus seen -> whole
    theme (repeats allowed as a last resort).
    """
    import random

    # Filter by theme
    theme_puzzles = [p for p in puzzle_list if theme in p['themes']]
    if not theme_puzzles:
        return None

    exclude_ids = exclude_ids or set()
    fresh_theme_puzzles = [p for p in theme_puzzles if p['id'] not in exclude_ids]

    # Find puzzles within rating range (prefer slightly harder puzzles)
    # Target range: user_rating - 100 to user_rating + 200
    windows = [
        (user_rating - 100, user_rating + rating_range),
        (user_rating - 200, user_rating + 300),
    ]
    for target_min, target_max in windows:
        matched = [p for p in fresh_theme_puzzles if target_min <= p['rating'] <= target_max]
        if matched:
            return random.choice(matched)

    # Nothing unseen near the rating: any unseen theme puzzle
    if fresh_theme_puzzles:
        return random.choice(fresh_theme_puzzles)

    # Everything in the theme has been attempted: allow repeats,
    # still preferring the rating window
    for target_min, target_max in windows:
        matched = [p for p in theme_puzzles if target_min <= p['rating'] <= target_max]
        if matched:
            return random.choice(matched)
    return random.choice(theme_puzzles)


def get_adaptive_puzzle(puzzle_list, user_ratings, exclude_ids=None):
    """
    Selects a puzzle based on user weaknesses in the 10 tracked themes.
    user_ratings: dict mapping category -> rating (int)
    
    Logic:
    1. Only use the 10 tracked themes
    2. Assign weights to each category. Lower rating = Higher weight.
       Default rating is 1600.
    3. Select a category probabilistically (favoring weaknesses).
    4. Select a puzzle from that category matching the user's rating.
    """
    import random
    
    # Only use tracked themes for adaptive selection
    tracked_theme_keys = list(TRACKED_THEMES.keys())
    
    # Calculate weights - lower rating = higher weight (more likely to be selected)
    # Using exponential weighting for stronger bias toward weaknesses
    # Weight = (2800 - Rating)^1.5 for much stronger preference for weak areas
    category_weights = []
    for theme in tracked_theme_keys:
        rating = user_ratings.get(theme, DEFAULT_RATING)
        # Exponential weighting gives much stronger preference to weak areas
        base_weight = max(100, 2800 - rating)
        weight = base_weight ** 1.3  # Exponential boost
        category_weights.append((theme, weight, rating))
        
    # Select Category probabilistically
    total_weight = sum(w for (_, w, _) in category_weights)
    r = random.uniform(0, total_weight)
    running_sum = 0
    selected_theme = None
    selected_rating = DEFAULT_RATING
    
    for theme, w, rating in category_weights:
        if running_sum + w >= r:
            selected_theme = theme
            selected_rating = rating
            break
        running_sum += w
        
    if not selected_theme:
        selected_theme = random.choice(tracked_theme_keys)
        selected_rating = user_ratings.get(selected_theme, DEFAULT_RATING)
    
    # Select puzzle from category, matching user's rating in that category
    puzzle = get_rating_matched_puzzle(puzzle_list, selected_theme, selected_rating,
                                       exclude_ids=exclude_ids)

    # If no puzzle found for that theme, fall back to random
    if not puzzle:
        puzzle = get_random_puzzle(puzzle_list, exclude_ids=exclude_ids)

    return puzzle

