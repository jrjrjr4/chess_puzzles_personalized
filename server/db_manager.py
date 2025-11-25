import os
from supabase import create_client, Client

DEFAULT_RATING = 1600  # Starting rating for all categories


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
        Much higher K-factors for faster convergence with 10 categories.
        - 0 attempts: K = 250 (first attempt, massive swing to quickly find level)
        - 1-2 attempts: K = 200
        - 3-5 attempts: K = 150
        - 6-10 attempts: K = 100
        - 11-20 attempts: K = 60
        - 21-35 attempts: K = 40
        - 35+ attempts: K = 25 (established rating, still responsive)
        """
        if attempts <= 0:
            return 250
        elif attempts <= 2:
            return 200
        elif attempts <= 5:
            return 150
        elif attempts <= 10:
            return 100
        elif attempts <= 20:
            return 60
        elif attempts <= 35:
            return 40
        else:
            return 25

    def update_user_category_rating(self, user_id, category, success, puzzle_rating=1600):
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
                old_rating = DEFAULT_RATING
                attempts = 0
            
            # Calculate K-factor based on attempts
            k_factor = self.calculate_k_factor(attempts)
            
            # Calculate expected score (Elo formula)
            # Expected = 1 / (1 + 10^((puzzle_rating - user_rating) / 400))
            expected = 1 / (1 + 10 ** ((puzzle_rating - old_rating) / 400))
            
            # Actual score: 1 for success, 0 for failure
            actual = 1 if success else 0
            
            # MINIMUM CHANGE: Ensure meaningful rating changes even with mismatched puzzles
            # This helps with small datasets where puzzle ratings don't match user ratings
            raw_change = k_factor * (actual - expected)
            
            # Apply minimum change based on attempts (more provisional = higher minimum)
            if attempts <= 5:
                min_change = 50  # At least ±50 for first 5 attempts
            elif attempts <= 15:
                min_change = 30  # At least ±30 for next 10
            else:
                min_change = 15  # At least ±15 after that
            
            # Apply minimum, preserving direction
            if actual == 1:  # Won
                change = round(max(raw_change, min_change))
            else:  # Lost
                change = round(min(raw_change, -min_change))
            
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

    def reset_user_ratings(self, user_id, new_rating=None):
        """
        Resets all category ratings for a user to the default rating.
        Also resets attempt counts to 0.
        Returns True on success, False on failure.
        """
        if not self.client or not user_id:
            return False
        
        reset_rating = new_rating if new_rating is not None else DEFAULT_RATING
        
        try:
            # Delete all existing ratings for this user
            self.client.table('user_category_ratings').delete().eq('user_id', user_id).execute()
            print(f"Reset ratings for user {user_id} to {reset_rating}")
            return True
        except Exception as e:
            print(f"Error in reset_user_ratings: {e}")
            return False

    def reset_all_user_ratings(self, new_rating=None):
        """
        Resets ALL users' category ratings to the default rating.
        Use with caution - this affects all users!
        Returns number of users affected.
        """
        if not self.client:
            return 0
        
        reset_rating = new_rating if new_rating is not None else DEFAULT_RATING
        
        try:
            # Get all unique user_ids from ratings table
            response = self.client.table('user_category_ratings').select('user_id').execute()
            if not response.data:
                return 0
            
            # Get unique user IDs
            user_ids = set(row['user_id'] for row in response.data)
            
            # Delete ratings for each user
            for user_id in user_ids:
                self.client.table('user_category_ratings').delete().eq('user_id', user_id).execute()
            
            print(f"Reset ratings for {len(user_ids)} users to {reset_rating}")
            return len(user_ids)
        except Exception as e:
            print(f"Error in reset_all_user_ratings: {e}")
            return 0
