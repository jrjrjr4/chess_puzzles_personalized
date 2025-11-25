"""
Script to upload puzzles from filtered_puzzles.csv to Supabase.
Run this once to populate the puzzles table.
"""
import os
import csv
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def upload_puzzles():
    # Initialize Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        print("Please set them in your .env file or environment")
        return False
    
    client: Client = create_client(url, key)
    print("Connected to Supabase")
    
    # Read CSV file
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'filtered_puzzles.csv')
    
    puzzles = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            puzzle = {
                'puzzle_id': row['PuzzleId'],
                'fen': row['FEN'],
                'moves': row['Moves'],
                'rating': int(row['Rating']),
                'rating_deviation': int(row['RatingDeviation']),
                'popularity': int(row['Popularity']),
                'nb_plays': int(row['NbPlays']),
                'themes': row['Themes'],
                'game_url': row['GameUrl'],
                'opening_tags': row.get('OpeningTags', '')
            }
            puzzles.append(puzzle)
    
    print(f"Read {len(puzzles)} puzzles from CSV")
    
    # Upload in batches (Supabase has limits on batch size)
    batch_size = 500
    total_uploaded = 0
    
    for i in range(0, len(puzzles), batch_size):
        batch = puzzles[i:i + batch_size]
        try:
            # Use upsert to handle potential duplicates
            response = client.table('puzzles').upsert(batch, on_conflict='puzzle_id').execute()
            total_uploaded += len(batch)
            print(f"Uploaded batch {i // batch_size + 1}: {total_uploaded}/{len(puzzles)} puzzles")
        except Exception as e:
            print(f"Error uploading batch {i // batch_size + 1}: {e}")
            return False
    
    print(f"\nSuccessfully uploaded {total_uploaded} puzzles to Supabase!")
    return True

def verify_upload():
    """Verify the upload by counting puzzles in the database."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        return
    
    client: Client = create_client(url, key)
    
    # Get count
    response = client.table('puzzles').select('puzzle_id', count='exact').limit(1).execute()
    print(f"\nVerification: {response.count} puzzles in database")
    
    # Sample a few puzzles
    sample = client.table('puzzles').select('*').limit(3).execute()
    print("\nSample puzzles:")
    for p in sample.data:
        print(f"  - {p['puzzle_id']}: Rating {p['rating']}, Themes: {p['themes'][:50]}...")

if __name__ == '__main__':
    print("=" * 60)
    print("Chess Puzzles Upload Script")
    print("=" * 60)
    
    success = upload_puzzles()
    
    if success:
        verify_upload()
    else:
        print("\nUpload failed. Please check the errors above.")

