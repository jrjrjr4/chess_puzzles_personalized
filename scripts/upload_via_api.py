"""
Upload puzzles to Supabase using the REST API.
Uses the project credentials from the CLI.
"""
import csv
import os
import httpx
import subprocess
import re
import time

def get_supabase_credentials():
    """Extract credentials from supabase CLI dry-run output."""
    result = subprocess.run(
        ['npx', 'supabase', 'db', 'dump', '--linked', '--dry-run'],
        capture_output=True,
        text=True,
        shell=True
    )
    
    output = result.stdout + result.stderr
    
    # Extract the project ref from the linked project
    # The API URL is https://<project-ref>.supabase.co
    project_ref = "lggaasquagpvolkwimab"
    
    # For REST API, we need the anon key or service role key
    # Let's get it from the supabase CLI
    return project_ref

def upload_puzzles_via_rest():
    """Upload puzzles using Supabase REST API."""
    project_ref = "lggaasquagpvolkwimab"
    
    # Get API key from environment or prompt
    api_key = os.environ.get('SUPABASE_KEY')
    
    if not api_key:
        print("=" * 60)
        print("SUPABASE_KEY not found in environment.")
        print("")
        print("Please get your API key from:")
        print(f"https://supabase.com/dashboard/project/{project_ref}/settings/api")
        print("")
        print("Then run:")
        print(f'$env:SUPABASE_KEY = "your-anon-or-service-key"')
        print("python scripts/upload_via_api.py")
        print("=" * 60)
        return False
    
    url = f"https://{project_ref}.supabase.co"
    
    # Read CSV
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, 'data', 'filtered_puzzles.csv')
    
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
    
    # Upload in batches
    headers = {
        'apikey': api_key,
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates'  # Upsert behavior
    }
    
    batch_size = 500
    total_uploaded = 0
    
    with httpx.Client(timeout=60.0) as client:
        for i in range(0, len(puzzles), batch_size):
            batch = puzzles[i:i + batch_size]
            
            try:
                response = client.post(
                    f"{url}/rest/v1/puzzles",
                    headers=headers,
                    json=batch
                )
                
                if response.status_code in [200, 201]:
                    total_uploaded += len(batch)
                    print(f"Uploaded batch {i // batch_size + 1}: {total_uploaded}/{len(puzzles)} puzzles")
                else:
                    print(f"Error uploading batch {i // batch_size + 1}: {response.status_code}")
                    print(response.text[:500])
                    return False
                    
            except Exception as e:
                print(f"Error uploading batch {i // batch_size + 1}: {e}")
                return False
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
    
    print(f"\n✓ Successfully uploaded {total_uploaded} puzzles to Supabase!")
    return True

def verify_upload():
    """Verify the upload by counting puzzles."""
    project_ref = "lggaasquagpvolkwimab"
    api_key = os.environ.get('SUPABASE_KEY')
    
    if not api_key:
        return
    
    url = f"https://{project_ref}.supabase.co"
    headers = {
        'apikey': api_key,
        'Authorization': f'Bearer {api_key}',
    }
    
    with httpx.Client() as client:
        # Get count
        response = client.get(
            f"{url}/rest/v1/puzzles?select=puzzle_id",
            headers={**headers, 'Prefer': 'count=exact', 'Range': '0-0'}
        )
        
        content_range = response.headers.get('content-range', '')
        if '/' in content_range:
            count = content_range.split('/')[-1]
            print(f"\nVerification: {count} puzzles in database")
        
        # Sample puzzles
        response = client.get(
            f"{url}/rest/v1/puzzles?select=puzzle_id,rating,themes&limit=3",
            headers=headers
        )
        
        if response.status_code == 200:
            puzzles = response.json()
            print("\nSample puzzles:")
            for p in puzzles:
                themes = p.get('themes', '')[:40]
                print(f"  - {p['puzzle_id']}: Rating {p['rating']}, Themes: {themes}...")

if __name__ == '__main__':
    print("=" * 60)
    print("Chess Puzzles Upload Script (REST API)")
    print("=" * 60)
    
    success = upload_puzzles_via_rest()
    
    if success:
        verify_upload()

