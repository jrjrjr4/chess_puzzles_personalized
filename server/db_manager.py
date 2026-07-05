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
                'provider': 'lichess',
            }
            response = self.client.table('users').insert(new_user).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"Error in get_or_create_user: {e}")
            return None

    def get_or_create_google_user(self, google_user_data):
        """
        Checks if a user exists by google_id, creates them if not.
        Returns the user record.
        """
        if not self.client:
            return None

        google_id = google_user_data.get('sub')  # Google's unique user ID
        email = google_user_data.get('email')
        name = google_user_data.get('name', email)

        try:
            # Check if user exists
            response = self.client.table('users').select("*").eq('google_id', google_id).execute()
            if response.data:
                return response.data[0]

            # Create new user
            new_user = {
                'google_id': google_id,
                'google_email': email,
                'google_name': name,
                'provider': 'google',
            }
            response = self.client.table('users').insert(new_user).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"Error in get_or_create_google_user: {e}")
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

    def get_user_attempted_puzzle_ids(self, user_id):
        """
        Returns the set of puzzle_ids this user has ever attempted.
        Paginated to dodge the 1000-row response cap.
        """
        if not self.client or not user_id:
            return set()

        try:
            attempted = set()
            page_size = 1000
            offset = 0
            while True:
                # .range() end bound is exclusive in this client, so a full
                # page is page_size - 1 rows; shorter means last page
                response = self.client.table('puzzle_attempts').select('puzzle_id') \
                    .eq('user_id', user_id).range(offset, offset + page_size - 1).execute()
                rows = response.data or []
                attempted.update(row['puzzle_id'] for row in rows)
                if len(rows) < page_size - 1:
                    break
                offset += len(rows)
            return attempted
        except Exception as e:
            print(f"Error in get_user_attempted_puzzle_ids: {e}")
            return set()

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

    @staticmethod
    def calculate_k_factor(attempts):
        """
        Calculate K-factor based on number of attempts.
        - 0 attempts: K = 250
        - 1-2 attempts: K = 200
        - 3-5 attempts: K = 150
        - 6-10 attempts: K = 100
        - 11-20 attempts: K = 60
        - 21-35 attempts: K = 40
        - 35+ attempts: K = 25
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
            
            if attempts <= 5:
                min_change = 50
            elif attempts <= 15:
                min_change = 30
            else:
                min_change = 15
            
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

    def bulk_upsert_category_ratings(self, rows):
        """Upserts multiple category rating rows in one request (spillover updates)."""
        if not self.client or not rows:
            return False

        try:
            self.client.table('user_category_ratings').upsert(rows, on_conflict='user_id, category').execute()
            return True
        except Exception as e:
            print(f"Error in bulk_upsert_category_ratings: {e}")
            return False

    def get_user_overall_rating(self, user_id):
        """Get the user's overall rating and attempts count."""
        if not self.client or not user_id:
            return {'rating': DEFAULT_RATING, 'attempts': 0}
        
        try:
            response = self.client.table('user_overall_rating').select("*").eq('user_id', user_id).execute()
            if response.data:
                return {
                    'rating': response.data[0]['rating'],
                    'attempts': response.data[0].get('attempts', 0) or 0
                }
            return {'rating': DEFAULT_RATING, 'attempts': 0}
        except Exception as e:
            print(f"Error in get_user_overall_rating: {e}")
            return {'rating': DEFAULT_RATING, 'attempts': 0}

    def update_user_overall_rating(self, user_id, success, puzzle_rating=1600):
        """
        Updates the user's overall rating using the same Elo system as categories.
        Returns dict with old_rating, new_rating, change, attempts, k_factor.
        """
        if not self.client or not user_id:
            return None
        
        try:
            # Get current overall rating data
            current_data = self.get_user_overall_rating(user_id)
            old_rating = current_data['rating']
            attempts = current_data['attempts']
            
            # Calculate K-factor based on attempts (same as categories)
            k_factor = self.calculate_k_factor(attempts)
            
            # Calculate expected score (Elo formula)
            expected = 1 / (1 + 10 ** ((puzzle_rating - old_rating) / 400))
            
            # Actual score: 1 for success, 0 for failure
            actual = 1 if success else 0
            
            # Calculate raw change
            raw_change = k_factor * (actual - expected)
            
            # Apply minimum change based on attempts
            if attempts <= 5:
                min_change = 50
            elif attempts <= 15:
                min_change = 30
            else:
                min_change = 15
            
            # Apply minimum, preserving direction
            if actual == 1:
                change = round(max(raw_change, min_change))
            else:
                change = round(min(raw_change, -min_change))
            
            new_rating = old_rating + change
            new_rating = max(400, min(2800, new_rating))
            new_attempts = attempts + 1
            
            # Upsert the data
            data = {
                'user_id': user_id,
                'rating': new_rating,
                'attempts': new_attempts,
                'updated_at': 'now()'
            }
            self.client.table('user_overall_rating').upsert(data, on_conflict='user_id').execute()
            
            return {
                'old_rating': old_rating,
                'new_rating': new_rating,
                'change': change,
                'attempts': new_attempts,
                'k_factor': k_factor
            }
        except Exception as e:
            print(f"Error in update_user_overall_rating: {e}")
            return None

    def reset_user_ratings(self, user_id, new_rating=None):
        """
        Resets all category ratings AND overall rating for a user.
        Also resets attempt counts to 0.
        Returns True on success, False on failure.
        """
        if not self.client or not user_id:
            return False
        
        reset_rating = new_rating if new_rating is not None else DEFAULT_RATING
        
        try:
            # Delete all existing category ratings for this user
            self.client.table('user_category_ratings').delete().eq('user_id', user_id).execute()
            # Delete overall rating for this user
            self.client.table('user_overall_rating').delete().eq('user_id', user_id).execute()
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

    # ==================== PUZZLE METHODS ====================
    
    def get_all_puzzles(self):
        """
        Fetches all puzzles from Supabase.
        Returns a list of puzzle dictionaries formatted for the app.
        """
        if not self.client:
            return []
        
        try:
            # Fetch all puzzles (may need pagination for very large datasets)
            puzzles = []
            page_size = 1000
            offset = 0
            
            while True:
                # NOTE: this client's .range() end bound is exclusive, so a
                # full page is page_size - 1 rows. Treat anything shorter as
                # the final page (correct under either bound semantics).
                response = self.client.table('puzzles').select('*').range(offset, offset + page_size - 1).execute()
                rows = response.data or []

                for row in rows:
                    puzzle = {
                        'id': row['puzzle_id'],
                        'fen': row['fen'],
                        'moves': row['moves'].split(),
                        'rating': row['rating'],
                        'themes': row['themes'].split() if row['themes'] else [],
                        'popularity': row['popularity']
                    }
                    puzzles.append(puzzle)

                if len(rows) < page_size - 1:
                    break
                offset += len(rows)
            
            print(f"Loaded {len(puzzles)} puzzles from Supabase")
            return puzzles
        except Exception as e:
            print(f"Error in get_all_puzzles: {e}")
            return []
    
    def get_puzzles_by_theme(self, theme, limit=100):
        """
        Fetches puzzles containing a specific theme.
        Uses text search on the themes column.
        """
        if not self.client:
            return []
        
        try:
            # Use ilike for case-insensitive partial match
            response = self.client.table('puzzles').select('*').ilike('themes', f'%{theme}%').limit(limit).execute()
            
            puzzles = []
            for row in response.data:
                puzzle = {
                    'id': row['puzzle_id'],
                    'fen': row['fen'],
                    'moves': row['moves'].split(),
                    'rating': row['rating'],
                    'themes': row['themes'].split() if row['themes'] else [],
                    'popularity': row['popularity']
                }
                puzzles.append(puzzle)
            
            return puzzles
        except Exception as e:
            print(f"Error in get_puzzles_by_theme: {e}")
            return []
    
    def get_puzzles_by_rating_range(self, min_rating, max_rating, theme=None, limit=100):
        """
        Fetches puzzles within a rating range, optionally filtered by theme.
        """
        if not self.client:
            return []
        
        try:
            query = self.client.table('puzzles').select('*').gte('rating', min_rating).lte('rating', max_rating)
            
            if theme:
                query = query.ilike('themes', f'%{theme}%')
            
            response = query.limit(limit).execute()
            
            puzzles = []
            for row in response.data:
                puzzle = {
                    'id': row['puzzle_id'],
                    'fen': row['fen'],
                    'moves': row['moves'].split(),
                    'rating': row['rating'],
                    'themes': row['themes'].split() if row['themes'] else [],
                    'popularity': row['popularity']
                }
                puzzles.append(puzzle)
            
            return puzzles
        except Exception as e:
            print(f"Error in get_puzzles_by_rating_range: {e}")
            return []
    
    def get_puzzle_count(self):
        """Returns the total number of puzzles in the database."""
        if not self.client:
            return 0
        
        try:
            response = self.client.table('puzzles').select('puzzle_id', count='exact').limit(1).execute()
            return response.count or 0
        except Exception as e:
            print(f"Error in get_puzzle_count: {e}")
            return 0
