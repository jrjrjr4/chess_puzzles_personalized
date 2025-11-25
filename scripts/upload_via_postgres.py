"""
Upload puzzles directly to Supabase PostgreSQL database.
Uses the connection details from supabase CLI.
"""
import csv
import os
import psycopg2
from psycopg2.extras import execute_values

# Database credentials from supabase CLI dry-run
DB_CONFIG = {
    'host': 'aws-1-us-east-1.pooler.supabase.com',
    'port': 5432,
    'user': 'cli_login_postgres.lggaasquagpvolkwimab',
    'password': 'uCwvIScervpbHrxWvGumqsLbFGtijxov',
    'database': 'postgres'
}

def upload_puzzles():
    """Upload puzzles directly via PostgreSQL connection."""
    
    # Read CSV
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, 'data', 'filtered_puzzles.csv')
    
    puzzles = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            puzzle = (
                row['PuzzleId'],
                row['FEN'],
                row['Moves'],
                int(row['Rating']),
                int(row['RatingDeviation']),
                int(row['Popularity']),
                int(row['NbPlays']),
                row['Themes'],
                row['GameUrl'],
                row.get('OpeningTags', '')
            )
            puzzles.append(puzzle)
    
    print(f"Read {len(puzzles)} puzzles from CSV")
    
    # Connect to database
    print("Connecting to Supabase PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Insert in batches using execute_values for efficiency
        batch_size = 1000
        total_uploaded = 0
        
        insert_sql = """
            INSERT INTO public.puzzles 
            (puzzle_id, fen, moves, rating, rating_deviation, popularity, nb_plays, themes, game_url, opening_tags)
            VALUES %s
            ON CONFLICT (puzzle_id) DO NOTHING
        """
        
        for i in range(0, len(puzzles), batch_size):
            batch = puzzles[i:i + batch_size]
            
            execute_values(cur, insert_sql, batch)
            conn.commit()
            
            total_uploaded += len(batch)
            print(f"Uploaded batch {i // batch_size + 1}: {total_uploaded}/{len(puzzles)} puzzles")
        
        print(f"\n✓ Successfully uploaded {total_uploaded} puzzles to Supabase!")
        
        # Verify
        cur.execute("SELECT COUNT(*) FROM public.puzzles")
        count = cur.fetchone()[0]
        print(f"\nVerification: {count} puzzles in database")
        
        # Sample
        cur.execute("SELECT puzzle_id, rating, themes FROM public.puzzles LIMIT 3")
        samples = cur.fetchall()
        print("\nSample puzzles:")
        for p in samples:
            themes = p[2][:40] if p[2] else ''
            print(f"  - {p[0]}: Rating {p[1]}, Themes: {themes}...")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        return False
        
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("Chess Puzzles Upload Script (Direct PostgreSQL)")
    print("=" * 60)
    
    upload_puzzles()

