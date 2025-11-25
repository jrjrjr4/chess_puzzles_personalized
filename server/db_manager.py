import os
from supabase import create_client, Client

class DBManager:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        self.client: Client = None
        if url and key:
            try:
                self.client = create_client(url, key)
                print("Supabase client initialized.")
            except Exception as e:
                print(f"Failed to initialize Supabase client: {e}")
        else:
            print("Supabase credentials not found. DB features disabled.")

    def get_or_create_user(self, lichess_user_data):
        """
        Checks if a user exists by lichess_id, creates them if not.
        Returns the user record.
        """
        if not self.client:
            return None

        lichess_id = lichess_user_data.get('id')
        username = lichess_user_data.get('username')

        try:
            # Check if user exists
            response = self.client.table('users').select("*").eq('lichess_id', lichess_id).execute()
            if response.data:
                return response.data[0]

            # Create new user
            new_user = {
                'lichess_id': lichess_id,
                'lichess_username': username,
            }
            response = self.client.table('users').insert(new_user).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"Error in get_or_create_user: {e}")
            return None

    def save_puzzle_attempt(self, user_id, puzzle_id, success):
        """Records a puzzle attempt."""
        if not self.client or not user_id:
            return

        try:
            attempt = {
                'user_id': user_id,
                'puzzle_id': puzzle_id,
                'success': success
            }
            self.client.table('puzzle_attempts').insert(attempt).execute()
        except Exception as e:
            print(f"Error in save_puzzle_attempt: {e}")

    def get_user_history(self, user_id):
        """Fetches puzzle history for a user."""
        if not self.client or not user_id:
            return []

        try:
            response = self.client.table('puzzle_attempts').select("*").eq('user_id', user_id).order('created_at', desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Error in get_user_history: {e}")
            return []

    def get_user_category_ratings(self, user_id):
        """Fetches all category ratings for a user (just the rating values)."""
        if not self.client or not user_id:
            return {}

        try:
            response = self.client.table('user_category_ratings').select("*").eq('user_id', user_id).execute()
            ratings = {}
            if response.data:
                for row in response.data:
                    ratings[row['category']] = row['rating']
            return ratings
        except Exception as e:
            print(f"Error in get_user_category_ratings: {e}")
            return {}

    def get_user_category_full_data(self, user_id):
        """Fetches all category data including attempts count."""
        if not self.client or not user_id:
            return {}

        try:
            response = self.client.table('user_category_ratings').select("*").eq('user_id', user_id).execute()
            data = {}
            if response.data:
                for row in response.data:
                    data[row['category']] = {
                        'rating': row['rating'],
                        'attempts': row.get('attempts', 0) or 0
                    }
            return data
        except Exception as e:
            print(f"Error in get_user_category_full_data: {e}")
            return {}

    def calculate_k_factor(self, attempts):
        """
        Calculate K-factor based on number of attempts.
        - 0 attempts: K = 150 (very provisional, big swings)
        - 1-3 attempts: K = 120
        - 4-7 attempts: K = 80
        - 8-15 attempts: K = 50
        - 16-25 attempts: K = 30
        - 25+ attempts: K = 15 (established rating)
        """
        if attempts <= 0:
            return 150
        elif attempts <= 3:
            return 120
        elif attempts <= 7:
            return 80
        elif attempts <= 15:
            return 50
        elif attempts <= 25:
            return 30
        else:
            return 15

    def update_user_category_rating(self, user_id, category, success, puzzle_rating=1200):
        """
        Updates rating for a category using adaptive K-factor.
        Returns (old_rating, new_rating, change, attempts).
        """
        if not self.client or not user_id:
            return None

        try:
            # Get current data for this category
            response = self.client.table('user_category_ratings').select("*").eq('user_id', user_id).eq('category', category).execute()
            
            if response.data:
                current = response.data[0]
                old_rating = current['rating']
                attempts = current.get('attempts', 0) or 0
            else:
                old_rating = 1200
                attempts = 0
            
            # Calculate K-factor based on attempts
            k_factor = self.calculate_k_factor(attempts)
            
            # Calculate expected score (Elo formula)
            # Expected = 1 / (1 + 10^((puzzle_rating - user_rating) / 400))
            expected = 1 / (1 + 10 ** ((puzzle_rating - old_rating) / 400))
            
            # Actual score: 1 for success, 0 for failure
            actual = 1 if success else 0
            
            # New rating = old + K * (actual - expected)
            change = round(k_factor * (actual - expected))
            new_rating = old_rating + change
            
            # Clamp rating to reasonable bounds
            new_rating = max(400, min(2800, new_rating))
            
            new_attempts = attempts + 1
            
            # Upsert the data
            data = {
                'user_id': user_id,
                'category': category,
                'rating': new_rating,
                'attempts': new_attempts,
                'updated_at': 'now()'
            }
            self.client.table('user_category_ratings').upsert(data, on_conflict='user_id, category').execute()
            
            return {
                'old_rating': old_rating,
                'new_rating': new_rating,
                'change': change,
                'attempts': new_attempts,
                'k_factor': k_factor
            }
            
        except Exception as e:
            print(f"Error in update_user_category_rating: {e}")
            return None
