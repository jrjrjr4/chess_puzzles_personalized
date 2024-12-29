import csv
import os

# server/puzzle_manager.py (for example)

def load_puzzles():
    puzzle_list = []
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(BASE_DIR, '../data/lichess_puzzles_trim.csv')

    with open(data_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert Themes
            themes_str = row.get('Themes', '')
            themes_list = [t.strip() for t in themes_str.split(',')] if themes_str else []

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

