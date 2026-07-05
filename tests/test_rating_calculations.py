# tests/test_rating_calculations.py
"""
Tests for rating calculation logic - Elo formulas and overall rating computation.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from puzzle_manager import TRACKED_THEMES, DEFAULT_RATING


class TestOverallRatingCalculation:
    """Tests for overall rating calculation across categories."""
    
    def get_calculate_overall_rating(self):
        """Import the function from main.py."""
        # We need to import this carefully to avoid DB initialization
        from unittest.mock import patch, MagicMock
        
        with patch('server.main.DBManager') as MockDB:
            MockDB.return_value = MagicMock(client=None)
            with patch('server.main.load_puzzles') as MockLoad:
                MockLoad.return_value = []
                from server.main import calculate_overall_rating
                return calculate_overall_rating
    
    def test_overall_rating_all_defaults(self):
        """Test overall rating when all categories are default."""
        calculate_overall_rating = self.get_calculate_overall_rating()
        
        # Empty dict = all defaults (1600)
        result = calculate_overall_rating({})
        
        assert result == DEFAULT_RATING
    
    def test_overall_rating_mixed_values(self):
        """Test overall rating with mixed category values."""
        calculate_overall_rating = self.get_calculate_overall_rating()
        
        ratings = {
            'fork': 1500,
            'pin': 1700,
            'mate': 1600,
        }
        
        result = calculate_overall_rating(ratings)
        
        # Should average all 10 categories (7 default + 3 specified)
        expected = (1500 + 1700 + 1600 + (7 * DEFAULT_RATING)) // 10
        assert result == expected
    
    def test_overall_rating_all_specified(self):
        """Test overall rating when all categories are specified."""
        calculate_overall_rating = self.get_calculate_overall_rating()
        
        # Set all 10 tracked themes
        ratings = {theme: 1500 + (i * 50) for i, theme in enumerate(TRACKED_THEMES.keys())}
        
        result = calculate_overall_rating(ratings)
        
        # Should be average of all specified values
        expected = sum(ratings.values()) // len(TRACKED_THEMES)
        assert result == expected
    
    def test_overall_rating_ignores_non_tracked_themes(self):
        """Test that non-tracked themes are ignored."""
        calculate_overall_rating = self.get_calculate_overall_rating()
        
        ratings = {
            'fork': 1500,
            'nonTrackedTheme': 2500,  # Should be ignored
            'anotherFakeTheme': 100,   # Should be ignored
        }
        
        result = calculate_overall_rating(ratings)
        
        # Should only consider 'fork' and defaults for others
        expected = (1500 + (9 * DEFAULT_RATING)) // 10
        assert result == expected


class TestEloCalculation:
    """Tests for Elo rating calculation formulas."""
    
    def test_expected_score_equal_ratings(self):
        """Test expected score when ratings are equal."""
        # E = 1 / (1 + 10^((opponent - player) / 400))
        # When equal: E = 1 / (1 + 10^0) = 1 / 2 = 0.5
        user_rating = 1600
        puzzle_rating = 1600
        
        expected = 1 / (1 + 10 ** ((puzzle_rating - user_rating) / 400))
        
        assert abs(expected - 0.5) < 0.001
    
    def test_expected_score_higher_user(self):
        """Test expected score when user rating is higher."""
        user_rating = 1800
        puzzle_rating = 1600
        
        expected = 1 / (1 + 10 ** ((puzzle_rating - user_rating) / 400))
        
        # Higher rated player should have > 0.5 expected score
        assert expected > 0.5
        assert expected < 1.0
    
    def test_expected_score_lower_user(self):
        """Test expected score when user rating is lower."""
        user_rating = 1400
        puzzle_rating = 1600
        
        expected = 1 / (1 + 10 ** ((puzzle_rating - user_rating) / 400))
        
        # Lower rated player should have < 0.5 expected score
        assert expected < 0.5
        assert expected > 0.0
    
    def test_expected_score_400_difference(self):
        """Test expected score with 400 point difference."""
        # 400 points difference should give ~10:1 odds
        user_rating = 1600
        puzzle_rating = 2000  # 400 points higher
        
        expected = 1 / (1 + 10 ** ((puzzle_rating - user_rating) / 400))
        
        # E ≈ 1 / (1 + 10) ≈ 0.091
        assert abs(expected - 0.091) < 0.01
    
    def test_rating_change_win_against_equal(self):
        """Test rating change when winning against equal opponent."""
        user_rating = 1600
        puzzle_rating = 1600
        k_factor = 100
        
        expected = 1 / (1 + 10 ** ((puzzle_rating - user_rating) / 400))
        actual = 1  # Win
        
        change = k_factor * (actual - expected)
        
        # Should gain about K/2 points
        assert abs(change - 50) < 1
    
    def test_rating_change_loss_against_equal(self):
        """Test rating change when losing against equal opponent."""
        user_rating = 1600
        puzzle_rating = 1600
        k_factor = 100
        
        expected = 1 / (1 + 10 ** ((puzzle_rating - user_rating) / 400))
        actual = 0  # Loss
        
        change = k_factor * (actual - expected)
        
        # Should lose about K/2 points
        assert abs(change - (-50)) < 1
    
    def test_rating_change_win_against_harder(self):
        """Test rating change when winning against harder puzzle."""
        user_rating = 1400
        puzzle_rating = 1600
        k_factor = 100
        
        expected = 1 / (1 + 10 ** ((puzzle_rating - user_rating) / 400))
        actual = 1  # Win
        
        change = k_factor * (actual - expected)
        
        # Should gain more than K/2 (upset win)
        assert change > 50
    
    def test_rating_change_loss_against_easier(self):
        """Test rating change when losing against easier puzzle."""
        user_rating = 1800
        puzzle_rating = 1600
        k_factor = 100
        
        expected = 1 / (1 + 10 ** ((puzzle_rating - user_rating) / 400))
        actual = 0  # Loss
        
        change = k_factor * (actual - expected)
        
        # Should lose more than K/2 (upset loss)
        assert change < -50


class TestKFactorProgression:
    """Tests for K-factor progression over attempts."""
    
    def test_k_factor_decreases_over_time(self):
        """Test that K-factor generally decreases as attempts increase."""
        from server.db_manager import DBManager
        
        db = DBManager.__new__(DBManager)
        db.client = None
        
        k_factors = [db.calculate_k_factor(i) for i in range(0, 50, 5)]
        
        # K-factors should generally decrease (not strictly, but overall trend)
        assert k_factors[0] > k_factors[-1]
    
    def test_k_factor_never_zero(self):
        """Test that K-factor never reaches zero."""
        from server.db_manager import DBManager
        
        db = DBManager.__new__(DBManager)
        db.client = None
        
        for attempts in range(0, 1000, 10):
            k = db.calculate_k_factor(attempts)
            assert k > 0


class TestRatingBounds:
    """Tests for rating boundary conditions."""
    
    def test_rating_minimum(self):
        """Test that ratings don't go below minimum (400)."""
        from server.db_manager import DBManager
        from unittest.mock import MagicMock
        
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        
        # Mock a user with very low rating
        mock_response = MagicMock()
        mock_response.data = [{'rating': 450, 'attempts': 100}]
        db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
        
        result = db.update_user_category_rating('user', 'fork', success=False, puzzle_rating=2500)
        
        assert result['new_rating'] >= 400
    
    def test_rating_maximum(self):
        """Test that ratings don't go above maximum (2800)."""
        from server.db_manager import DBManager
        from unittest.mock import MagicMock
        
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        
        # Mock a user with very high rating
        mock_response = MagicMock()
        mock_response.data = [{'rating': 2750, 'attempts': 100}]
        db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
        
        result = db.update_user_category_rating('user', 'fork', success=True, puzzle_rating=800)
        
        assert result['new_rating'] <= 2800


class TestMinimumRatingChange:
    """Tests for minimum rating change enforcement."""
    
    def test_minimum_change_early_attempts(self):
        """Test minimum change is enforced for early attempts."""
        from server.db_manager import DBManager
        from unittest.mock import MagicMock
        
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        
        # Mock user with few attempts solving a much easier puzzle
        mock_response = MagicMock()
        mock_response.data = [{'rating': 2000, 'attempts': 2}]
        db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
        
        # Win against easy puzzle - normally would give small gain
        result = db.update_user_category_rating('user', 'fork', success=True, puzzle_rating=1200)
        
        # Should have at least minimum change (50 for early attempts)
        assert abs(result['change']) >= 50
    
    def test_minimum_change_later_attempts(self):
        """Test minimum change decreases for later attempts."""
        from server.db_manager import DBManager
        from unittest.mock import MagicMock
        
        db = DBManager.__new__(DBManager)
        db.client = MagicMock()
        
        # Mock user with many attempts
        mock_response = MagicMock()
        mock_response.data = [{'rating': 2000, 'attempts': 50}]
        db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
        
        result = db.update_user_category_rating('user', 'fork', success=True, puzzle_rating=1200)
        
        # Should have at least minimum change (15 for veteran)
        assert abs(result['change']) >= 15


class TestTrackedThemesConsistency:
    """Tests for tracked themes consistency."""
    
    def test_tracked_themes_count(self):
        """Test that there are exactly 10 tracked themes."""
        assert len(TRACKED_THEMES) == 10
    
    def test_tracked_themes_have_display_names(self):
        """Test all tracked themes have display names."""
        for theme_key, display_name in TRACKED_THEMES.items():
            assert isinstance(theme_key, str)
            assert isinstance(display_name, str)
            assert len(display_name) > 0
    
    def test_tracked_themes_keys_are_valid(self):
        """Test tracked theme keys are valid identifiers."""
        expected_themes = {
            'pin', 'fork', 'mate', 'defensiveMove', 'endgame',
            'deflection', 'quietMove', 'kingsideAttack', 
            'discoveredAttack', 'capturingDefender'
        }
        
        assert set(TRACKED_THEMES.keys()) == expected_themes
    
    def test_default_rating_value(self):
        """Test default rating is 1600."""
        assert DEFAULT_RATING == 1600



class TestSpilloverChange:
    """Tests for spillover rating changes on categories a puzzle doesn't test."""

    def get_calculate_spillover_change(self):
        """Import the function from main.py without DB initialization."""
        from unittest.mock import patch, MagicMock

        with patch('server.main.DBManager') as MockDB:
            MockDB.return_value = MagicMock(client=None)
            with patch('server.main.load_puzzles') as MockLoad:
                MockLoad.return_value = []
                from server.main import calculate_spillover_change
                return calculate_spillover_change

    def test_new_category_moves_substantially(self):
        """A never-tested category should move a lot from any result."""
        spill = self.get_calculate_spillover_change()
        change = spill(1600, 0, True, 1600)
        # K=250, expected=0.5, weight=0.5 -> ~62
        assert 50 <= change <= 70

    def test_loss_is_symmetric(self):
        """Losses drift provisional categories down as much as wins drift up."""
        spill = self.get_calculate_spillover_change()
        up = spill(1600, 0, True, 1600)
        down = spill(1600, 0, False, 1600)
        assert down == -up

    def test_spillover_fades_with_attempts(self):
        """More direct attempts -> smaller spillover."""
        spill = self.get_calculate_spillover_change()
        changes = [spill(1600, a, True, 1600) for a in range(5)]
        assert all(changes[i] > changes[i + 1] for i in range(4))

    def test_established_category_gets_no_spillover(self):
        """At or past the cutoff, spillover stops entirely."""
        spill = self.get_calculate_spillover_change()
        assert spill(1600, 5, True, 1600) == 0
        assert spill(1600, 20, False, 1600) == 0

    def test_respects_elo_expectation(self):
        """Beating an easy puzzle moves a high provisional rating less."""
        spill = self.get_calculate_spillover_change()
        vs_equal = spill(1600, 0, True, 1600)
        vs_easy = spill(2000, 0, True, 1400)
        assert vs_easy < vs_equal

    def test_no_minimum_change_floor(self):
        """Unlike direct updates, spillover can round to zero."""
        spill = self.get_calculate_spillover_change()
        # Very easy puzzle vs high rating: expected ~1, win changes ~nothing
        assert spill(2600, 4, True, 800) == 0
