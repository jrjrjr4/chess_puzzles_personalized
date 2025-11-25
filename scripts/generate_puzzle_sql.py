"""
Generate SQL INSERT statements from the filtered_puzzles.csv file.
This creates a SQL file that can be pushed to Supabase.
"""
import csv
import os

def escape_sql_string(s):
    """Escape single quotes for SQL."""
    if s is None:
        return ''
    return s.replace("'", "''")

def generate_sql():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, 'data', 'filtered_puzzles.csv')
    output_path = os.path.join(base_dir, 'supabase', 'seed.sql')
    
    print(f"Reading from: {csv_path}")
    print(f"Writing to: {output_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Read {len(rows)} puzzles")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("-- Auto-generated puzzle seed data\n")
        f.write("-- Generated from filtered_puzzles.csv\n\n")
        
        # Use batch inserts for efficiency
        batch_size = 100
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            
            f.write("INSERT INTO public.puzzles (puzzle_id, fen, moves, rating, rating_deviation, popularity, nb_plays, themes, game_url, opening_tags) VALUES\n")
            
            values = []
            for row in batch:
                puzzle_id = escape_sql_string(row['PuzzleId'])
                fen = escape_sql_string(row['FEN'])
                moves = escape_sql_string(row['Moves'])
                rating = int(row['Rating'])
                rating_dev = int(row['RatingDeviation'])
                popularity = int(row['Popularity'])
                nb_plays = int(row['NbPlays'])
                themes = escape_sql_string(row['Themes'])
                game_url = escape_sql_string(row['GameUrl'])
                opening_tags = escape_sql_string(row.get('OpeningTags', ''))
                
                value = f"('{puzzle_id}', '{fen}', '{moves}', {rating}, {rating_dev}, {popularity}, {nb_plays}, '{themes}', '{game_url}', '{opening_tags}')"
                values.append(value)
            
            f.write(',\n'.join(values))
            f.write('\nON CONFLICT (puzzle_id) DO NOTHING;\n\n')
        
    print(f"Generated SQL file with {len(rows)} puzzles")
    return output_path

if __name__ == '__main__':
    generate_sql()

