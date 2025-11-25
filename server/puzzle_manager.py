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

def load_puzzles():
    puzzle_list = []
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(BASE_DIR, '../data/lichess_puzzles_trim.csv')

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

    return puzzle_list


def get_random_puzzle(puzzle_list, theme_filter=None, popularity_bias=True):
    """
    Returns a random puzzle from puzzle_list. If popularity_bias is True,
    we weight the selection by puzzle popularity.
    """
    import random

    # Filter by theme if requested
    candidates = puzzle_list
    if theme_filter:
        candidates = [p for p in puzzle_list if theme_filter in p['themes']]
        if not candidates:
            return None

    if not popularity_bias:
        # Just pick randomly from candidates
        return random.choice(candidates)

    # Weighted pick by popularity. If popularity=0, fallback to minimal weight.
    # We'll build a list of (puzzle, weight) tuples.
    puzzle_weights = []
    for p in candidates:
        weight = max(1, p.get('popularity', 0))  # ensure at least weight=1
        puzzle_weights.append((p, weight))

    # Convert that to a random choice
    total_weight = sum(w for (_, w) in puzzle_weights)
    r = random.uniform(0, total_weight)
    running_sum = 0
    for puzzle, w in puzzle_weights:
        if running_sum + w >= r:
            return puzzle
        running_sum += w

    # Fallback, though we should never hit this if everything is correct
    return None


def get_rating_matched_puzzle(puzzle_list, theme, user_rating, rating_range=200):
    """
    Selects a puzzle from the given theme that matches the user's rating.
    Prefers puzzles within rating_range of the user's rating.
    """
    import random
    
    # Filter by theme
    theme_puzzles = [p for p in puzzle_list if theme in p['themes']]
    if not theme_puzzles:
        return None
    
    # Find puzzles within rating range (prefer slightly harder puzzles)
    # Target range: user_rating - 100 to user_rating + 200
    target_min = user_rating - 100
    target_max = user_rating + rating_range
    
    matched_puzzles = [p for p in theme_puzzles if target_min <= p['rating'] <= target_max]
    
    # If no exact matches, expand the range
    if not matched_puzzles:
        # Try wider range
        target_min = user_rating - 200
        target_max = user_rating + 300
        matched_puzzles = [p for p in theme_puzzles if target_min <= p['rating'] <= target_max]
    
    # If still no matches, use all puzzles from theme
    if not matched_puzzles:
        matched_puzzles = theme_puzzles
    
    # Weight by closeness to user rating (closer = higher weight)
    # Also factor in popularity
    puzzle_weights = []
    for p in matched_puzzles:
        rating_diff = abs(p['rating'] - user_rating)
        # Closer ratings get higher weight. Max weight at exact match.
        closeness_weight = max(1, 400 - rating_diff)
        popularity_weight = max(1, p.get('popularity', 0))
        # Combine weights (closeness matters more)
        total_weight = closeness_weight * 2 + popularity_weight
        puzzle_weights.append((p, total_weight))
    
    # Weighted random selection
    total_weight = sum(w for (_, w) in puzzle_weights)
    r = random.uniform(0, total_weight)
    running_sum = 0
    for puzzle, w in puzzle_weights:
        if running_sum + w >= r:
            return puzzle
        running_sum += w
    
    return random.choice(matched_puzzles)


def get_adaptive_puzzle(puzzle_list, user_ratings):
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
    puzzle = get_rating_matched_puzzle(puzzle_list, selected_theme, selected_rating)
    
    # If no puzzle found for that theme, fall back to random
    if not puzzle:
        puzzle = get_random_puzzle(puzzle_list)
    
    return puzzle

