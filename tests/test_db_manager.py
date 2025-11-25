# tests/test_db_manager.py
"""
Tests for db_manager.py - database operations with mocked Supabase client.
"""
import pytest
from unittest.mock import MagicMock, patch
import os

from server.db_manager import DBManager, DEFAULT_RATING


class TestDBManagerInit:
    """Tests for DBManager initialization."""
    
    def test_init_with_credentials(self, monkeypatch):
        """Test initialization with valid credentials."""
        monkeypatch.setenv('SUPABASE_URL', 'https://test.supabase.co')
        monkeypatch.setenv('SUPABASE_KEY', 'test-key')
        
        with patch('server.db_manager.create_client') as mock_create:
            mock_create.return_value = MagicMock()
            db = DBManager()
            
            assert db.client is not None
            mock_create.assert_called_once_with('https://test.supabase.co', 'test-key')
    
    def test_init_without_credentials(self, monkeypatch):
        """Test initialization without credentials."""
        monkeypatch.delenv('SUPABASE_URL', raising=False)
        monkeypatch.delenv('SUPABASE_KEY', raising=False)
        
        db = DBManager()
        
        assert db.client is None
    
    def test_init_with_partial_credentials(self, monkeypatch):
        """Test initialization with only URL (no key)."""
        monkeypatch.setenv('SUPABASE_URL', 'https://test.supabase.co')
        monkeypatch.delenv('SUPABASE_KEY', raising=False)
        
        db = DBManager()
        
        assert db.client is None


class TestGetOrCreateUser:
    """Tests for Lichess user creation/retrieval."""
    
    @pytest.fixture
    def db_with_mock_client(self):
        """Create DBManager with mocked client."""
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        return db
    
    def test_get_existing_user(self, db_with_mock_client):
        """Test retrieving an existing user."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid-123', 'lichess_id': 'testuser', 'lichess_username': 'TestUser'}]
        db_with_mock_client.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = db_with_mock_client.get_or_create_user({'id': 'testuser', 'username': 'TestUser'})
        
        assert result['lichess_id'] == 'testuser'
    
    def test_create_new_user(self, db_with_mock_client):
        """Test creating a new user."""
        # First call (select) returns empty
        mock_select_response = MagicMock()
        mock_select_response.data = []
        
        # Second call (insert) returns new user
        mock_insert_response = MagicMock()
        mock_insert_response.data = [{'id': 'uuid-new', 'lichess_id': 'newuser', 'lichess_username': 'NewUser'}]
        
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_select_response
        mock_table.insert.return_value.execute.return_value = mock_insert_response
        db_with_mock_client.client.table.return_value = mock_table
        
        result = db_with_mock_client.get_or_create_user({'id': 'newuser', 'username': 'NewUser'})
        
        assert result['lichess_id'] == 'newuser'
    
    def test_get_or_create_user_no_client(self):
        """Test returns None when no client."""
        db = DBManager.__new__(DBManager)
        db.client = None
        
        result = db.get_or_create_user({'id': 'test', 'username': 'Test'})
        
        assert result is None


class TestGetOrCreateGoogleUser:
    """Tests for Google user creation/retrieval."""
    
    @pytest.fixture
    def db_with_mock_client(self):
        """Create DBManager with mocked client."""
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        return db
    
    def test_get_existing_google_user(self, db_with_mock_client):
        """Test retrieving an existing Google user."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid-456', 'google_id': '12345', 'google_email': 'test@gmail.com'}]
        db_with_mock_client.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = db_with_mock_client.get_or_create_google_user({
            'sub': '12345',
            'email': 'test@gmail.com',
            'name': 'Test User'
        })
        
        assert result['google_id'] == '12345'
    
    def test_create_new_google_user(self, db_with_mock_client):
        """Test creating a new Google user."""
        mock_select_response = MagicMock()
        mock_select_response.data = []
        
        mock_insert_response = MagicMock()
        mock_insert_response.data = [{
            'id': 'uuid-new',
            'google_id': '67890',
            'google_email': 'new@gmail.com',
            'google_name': 'New User',
            'provider': 'google'
        }]
        
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_select_response
        mock_table.insert.return_value.execute.return_value = mock_insert_response
        db_with_mock_client.client.table.return_value = mock_table
        
        result = db_with_mock_client.get_or_create_google_user({
            'sub': '67890',
            'email': 'new@gmail.com',
            'name': 'New User'
        })
        
        assert result['google_id'] == '67890'
        assert result['provider'] == 'google'


class TestPuzzleAttempts:
    """Tests for puzzle attempt recording."""
    
    @pytest.fixture
    def db_with_mock_client(self):
        """Create DBManager with mocked client."""
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        return db
    
    def test_save_puzzle_attempt(self, db_with_mock_client):
        """Test saving a puzzle attempt."""
        db_with_mock_client.save_puzzle_attempt('user-uuid', 'puzzle-123', True)
        
        db_with_mock_client.client.table.assert_called_with('puzzle_attempts')
        insert_call = db_with_mock_client.client.table.return_value.insert
        insert_call.assert_called_once()
        
        # Check the data passed to insert
        call_args = insert_call.call_args[0][0]
        assert call_args['user_id'] == 'user-uuid'
        assert call_args['puzzle_id'] == 'puzzle-123'
        assert call_args['success'] == True
    
    def test_save_puzzle_attempt_no_client(self):
        """Test save attempt does nothing without client."""
        db = DBManager.__new__(DBManager)
        db.client = None
        
        # Should not raise
        db.save_puzzle_attempt('user-uuid', 'puzzle-123', True)
    
    def test_save_puzzle_attempt_no_user_id(self):
        """Test save attempt does nothing without user_id."""
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        
        db.save_puzzle_attempt(None, 'puzzle-123', True)
        
        db.client.table.assert_not_called()
    
    def test_get_user_history(self, db_with_mock_client):
        """Test retrieving user puzzle history."""
        mock_response = MagicMock()
        mock_response.data = [
            {'puzzle_id': 'p1', 'success': True},
            {'puzzle_id': 'p2', 'success': False},
        ]
        db_with_mock_client.client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        
        history = db_with_mock_client.get_user_history('user-uuid')
        
        assert len(history) == 2
        assert history[0]['puzzle_id'] == 'p1'


class TestCategoryRatings:
    """Tests for category rating operations."""
    
    @pytest.fixture
    def db_with_mock_client(self):
        """Create DBManager with mocked client."""
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        return db
    
    def test_get_user_category_ratings(self, db_with_mock_client):
        """Test retrieving user category ratings."""
        mock_response = MagicMock()
        mock_response.data = [
            {'category': 'fork', 'rating': 1500},
            {'category': 'pin', 'rating': 1650},
        ]
        db_with_mock_client.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        ratings = db_with_mock_client.get_user_category_ratings('user-uuid')
        
        assert ratings['fork'] == 1500
        assert ratings['pin'] == 1650
    
    def test_get_user_category_ratings_empty(self, db_with_mock_client):
        """Test returns empty dict when no ratings."""
        mock_response = MagicMock()
        mock_response.data = []
        db_with_mock_client.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        ratings = db_with_mock_client.get_user_category_ratings('user-uuid')
        
        assert ratings == {}
    
    def test_get_user_category_ratings_no_client(self):
        """Test returns empty dict without client."""
        db = DBManager.__new__(DBManager)
        db.client = None
        
        ratings = db.get_user_category_ratings('user-uuid')
        
        assert ratings == {}


class TestKFactorCalculation:
    """Tests for K-factor calculation based on attempts."""
    
    @pytest.fixture
    def db_manager(self):
        """Create DBManager instance for testing."""
        db = DBManager.__new__(DBManager)
        db.client = None  # Not needed for K-factor tests
        return db
    
    def test_k_factor_first_attempt(self, db_manager):
        """Test K-factor for first attempt (0 attempts)."""
        assert db_manager.calculate_k_factor(0) == 250
    
    def test_k_factor_early_attempts(self, db_manager):
        """Test K-factor for early attempts (1-2)."""
        assert db_manager.calculate_k_factor(1) == 200
        assert db_manager.calculate_k_factor(2) == 200
    
    def test_k_factor_learning_phase(self, db_manager):
        """Test K-factor for learning phase (3-5)."""
        assert db_manager.calculate_k_factor(3) == 150
        assert db_manager.calculate_k_factor(5) == 150
    
    def test_k_factor_intermediate(self, db_manager):
        """Test K-factor for intermediate phase (6-10)."""
        assert db_manager.calculate_k_factor(6) == 100
        assert db_manager.calculate_k_factor(10) == 100
    
    def test_k_factor_established(self, db_manager):
        """Test K-factor for established ratings (11-20)."""
        assert db_manager.calculate_k_factor(11) == 60
        assert db_manager.calculate_k_factor(20) == 60
    
    def test_k_factor_stable(self, db_manager):
        """Test K-factor for stable ratings (21-35)."""
        assert db_manager.calculate_k_factor(21) == 40
        assert db_manager.calculate_k_factor(35) == 40
    
    def test_k_factor_veteran(self, db_manager):
        """Test K-factor for veteran ratings (35+)."""
        assert db_manager.calculate_k_factor(36) == 25
        assert db_manager.calculate_k_factor(100) == 25


class TestUpdateCategoryRating:
    """Tests for rating update calculations."""
    
    @pytest.fixture
    def db_with_mock_client(self):
        """Create DBManager with mocked client."""
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        return db
    
    def test_update_rating_success_first_attempt(self, db_with_mock_client):
        """Test rating increase on successful first attempt."""
        # Mock no existing rating
        mock_select = MagicMock()
        mock_select.data = []
        db_with_mock_client.client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select
        
        result = db_with_mock_client.update_user_category_rating(
            'user-uuid', 'fork', success=True, puzzle_rating=1600
        )
        
        assert result is not None
        assert result['old_rating'] == DEFAULT_RATING
        assert result['new_rating'] > result['old_rating']
        assert result['change'] > 0
        assert result['attempts'] == 1
        assert result['k_factor'] == 250  # First attempt
    
    def test_update_rating_failure(self, db_with_mock_client):
        """Test rating decrease on failed attempt."""
        mock_select = MagicMock()
        mock_select.data = [{'rating': 1600, 'attempts': 5}]
        db_with_mock_client.client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select
        
        result = db_with_mock_client.update_user_category_rating(
            'user-uuid', 'fork', success=False, puzzle_rating=1600
        )
        
        assert result is not None
        assert result['new_rating'] < result['old_rating']
        assert result['change'] < 0
    
    def test_update_rating_clamped_high(self, db_with_mock_client):
        """Test rating is clamped at 2800."""
        mock_select = MagicMock()
        mock_select.data = [{'rating': 2750, 'attempts': 0}]
        db_with_mock_client.client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select
        
        result = db_with_mock_client.update_user_category_rating(
            'user-uuid', 'fork', success=True, puzzle_rating=1000
        )
        
        assert result['new_rating'] <= 2800
    
    def test_update_rating_clamped_low(self, db_with_mock_client):
        """Test rating is clamped at 400."""
        mock_select = MagicMock()
        mock_select.data = [{'rating': 450, 'attempts': 0}]
        db_with_mock_client.client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_select
        
        result = db_with_mock_client.update_user_category_rating(
            'user-uuid', 'fork', success=False, puzzle_rating=2500
        )
        
        assert result['new_rating'] >= 400


class TestResetRatings:
    """Tests for rating reset functionality."""
    
    @pytest.fixture
    def db_with_mock_client(self):
        """Create DBManager with mocked client."""
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        return db
    
    def test_reset_user_ratings(self, db_with_mock_client):
        """Test resetting a single user's ratings."""
        result = db_with_mock_client.reset_user_ratings('user-uuid')
        
        assert result == True
        db_with_mock_client.client.table.return_value.delete.return_value.eq.return_value.execute.assert_called_once()
    
    def test_reset_user_ratings_no_client(self):
        """Test reset returns False without client."""
        db = DBManager.__new__(DBManager)
        db.client = None
        
        result = db.reset_user_ratings('user-uuid')
        
        assert result == False
    
    def test_reset_all_user_ratings(self, db_with_mock_client):
        """Test resetting all users' ratings."""
        mock_response = MagicMock()
        mock_response.data = [
            {'user_id': 'user-1'},
            {'user_id': 'user-2'},
            {'user_id': 'user-1'},  # Duplicate
        ]
        db_with_mock_client.client.table.return_value.select.return_value.execute.return_value = mock_response
        
        count = db_with_mock_client.reset_all_user_ratings()
        
        assert count == 2  # Unique users


class TestPuzzleRetrieval:
    """Tests for puzzle retrieval from database."""
    
    @pytest.fixture
    def db_with_mock_client(self):
        """Create DBManager with mocked client."""
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        return db
    
    def test_get_all_puzzles(self, db_with_mock_client):
        """Test retrieving all puzzles."""
        mock_response = MagicMock()
        mock_response.data = [
            {'puzzle_id': 'p1', 'fen': 'fen1', 'moves': 'e4 e5', 'rating': 1500, 'themes': 'fork pin', 'popularity': 85},
        ]
        db_with_mock_client.client.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response
        
        puzzles = db_with_mock_client.get_all_puzzles()
        
        assert len(puzzles) == 1
        assert puzzles[0]['id'] == 'p1'
        assert puzzles[0]['moves'] == ['e4', 'e5']
        assert puzzles[0]['themes'] == ['fork', 'pin']
    
    def test_get_puzzles_by_theme(self, db_with_mock_client):
        """Test retrieving puzzles by theme."""
        mock_response = MagicMock()
        mock_response.data = [
            {'puzzle_id': 'p1', 'fen': 'fen1', 'moves': 'e4', 'rating': 1500, 'themes': 'fork', 'popularity': 85},
        ]
        db_with_mock_client.client.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response
        
        puzzles = db_with_mock_client.get_puzzles_by_theme('fork')
        
        assert len(puzzles) == 1
    
    def test_get_puzzle_count(self, db_with_mock_client):
        """Test getting puzzle count."""
        mock_response = MagicMock()
        mock_response.count = 1000
        db_with_mock_client.client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response
        
        count = db_with_mock_client.get_puzzle_count()
        
        assert count == 1000

