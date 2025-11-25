import csv
import os

# server/puzzle_manager.py

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
                'rating': int(row.get('Rating', 1200)),
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


def get_adaptive_puzzle(puzzle_list, user_ratings):
    """
    Selects a puzzle based on user weaknesses in the 10 tracked themes.
    user_ratings: dict mapping category -> rating (int)
    
    Logic:
    1. Only use the 10 tracked themes
    2. Assign weights to each category. Lower rating = Higher weight.
       Default rating is 1200.
    3. Select a category probabilistically (favoring weaknesses).
    4. Select a random puzzle from that category.
    """
    import random
    
    # Only use tracked themes for adaptive selection
    tracked_theme_keys = list(TRACKED_THEMES.keys())
    
    # Calculate weights - lower rating = higher weight (more likely to be selected)
    # Weight = max(50, 2400 - Rating)
    # Rating 1200 -> weight 1200, Rating 1400 -> weight 1000, Rating 1000 -> weight 1400
    category_weights = []
    for theme in tracked_theme_keys:
        rating = user_ratings.get(theme, 1200)
        weight = max(50, 2400 - rating)
        category_weights.append((theme, weight))
        
    # Select Category probabilistically
    total_weight = sum(w for (_, w) in category_weights)
    r = random.uniform(0, total_weight)
    running_sum = 0
    selected_theme = None
    
    for theme, w in category_weights:
        if running_sum + w >= r:
            selected_theme = theme
            break
        running_sum += w
        
    if not selected_theme:
        selected_theme = random.choice(tracked_theme_keys)
        
    # Select puzzle from category
    puzzle = get_random_puzzle(puzzle_list, theme_filter=selected_theme)
    
    # If no puzzle found for that theme, fall back to random
    if not puzzle:
        puzzle = get_random_puzzle(puzzle_list)
    
    return puzzle

