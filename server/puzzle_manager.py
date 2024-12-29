import csv
import os

def load_puzzles():
    """Loads puzzle data from CSV file and returns a list of puzzle dicts."""
    puzzle_list = []
    data_file = os.path.join(os.path.dirname(__file__), '../data/lichess_puzzles_trim.csv')
    
    with open(data_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert Themes from "pin,fork" to a Python list
            themes_str = row['Themes']
            themes_list = [t.strip() for t in themes_str.split(',')]
            
            puzzle = {
                'id': row['PuzzleId'],
                'fen': row['FEN'],
                'moves': row['Moves'].split(),  # or parse more elegantly
                'rating': int(row['Rating']),
                'themes': themes_list
            }
            puzzle_list.append(puzzle)
    
    return puzzle_list

def get_random_puzzle(puzzle_list, theme_filter=None):
    """Returns a random puzzle from the puzzle_list (optionally filtered by theme)."""
    import random
    
    if theme_filter:
        filtered = [p for p in puzzle_list if theme_filter in p['themes']]
        if not filtered:
            return None
        return random.choice(filtered)
    else:
        return random.choice(puzzle_list)
