# tests/test_puzzle_manager.py
"""
Tests for puzzle_manager.py - puzzle loading, filtering, and adaptive selection.
"""
import pytest
from unittest.mock import MagicMock, patch, mock_open
import random

from server.puzzle_manager import (
    load_puzzles,
    load_puzzles_from_csv,
    get_random_puzzle,
    get_rating_matched_puzzle,
    get_adaptive_puzzle,
    get_tracked_themes_for_puzzle,
    get_theme_display_name,
    TRACKED_THEMES,
    DEFAULT_RATING
)


class TestTrackedThemes:
    """Tests for theme tracking functionality."""
    
    def test_tracked_themes_has_10_themes(self):
        """Verify we have exactly 10 tracked themes."""
        assert len(TRACKED_THEMES) == 10
    
    def test_get_tracked_themes_for_puzzle_filters_correctly(self):
        """Test that only tracked themes are returned."""
        puzzle_themes = ['fork', 'middlegame', 'short', 'pin', 'someRandomTheme']
        result = get_tracked_themes_for_puzzle(puzzle_themes)
        
        assert 'fork' in result
        assert 'pin' in result
        assert 'middlegame' not in result  # Not a tracked theme
        assert 'someRandomTheme' not in result
        assert len(result) == 2
    
    def test_get_tracked_themes_empty_list(self):
        """Test with empty theme list."""
        result = get_tracked_themes_for_puzzle([])
        assert result == []
    
    def test_get_tracked_themes_no_matches(self):
        """Test when no themes match tracked themes."""
        puzzle_themes = ['opening', 'middlegame', 'short']
        result = get_tracked_themes_for_puzzle(puzzle_themes)
        assert result == []
    
    def test_get_theme_display_name_known_theme(self):
        """Test display name for known theme."""
        assert get_theme_display_name('fork') == 'Fork'
        assert get_theme_display_name('kingsideAttack') == 'Kingside Attack'
        assert get_theme_display_name('defensiveMove') == 'Defense'
    
    def test_get_theme_display_name_unknown_theme(self):
        """Test display name for unknown theme returns the theme itself."""
        assert get_theme_display_name('unknownTheme') == 'unknownTheme'


class TestLoadPuzzles:
    """Tests for puzzle loading functionality."""
    
    def test_load_puzzles_prefers_csv(self, mock_db_manager):
        """CSV is the primary source; Supabase isn't queried when it loads."""
        with patch('server.puzzle_manager.load_puzzles_from_csv') as mock_csv:
            mock_csv.return_value = [{'id': 'csv_puzzle'}]
            puzzles = load_puzzles(mock_db_manager)

            mock_csv.assert_called_once()
            mock_db_manager.get_all_puzzles.assert_not_called()
            assert puzzles == [{'id': 'csv_puzzle'}]

    def test_load_puzzles_fallback_to_supabase(self, mock_db_manager, sample_puzzles):
        """Supabase is used when the local CSV is missing/empty."""
        mock_db_manager.get_all_puzzles.return_value = sample_puzzles

        with patch('server.puzzle_manager.load_puzzles_from_csv') as mock_csv:
            mock_csv.return_value = []
            puzzles = load_puzzles(mock_db_manager)

            assert len(puzzles) == len(sample_puzzles)
            mock_db_manager.get_all_puzzles.assert_called_once()
    
    def test_load_puzzles_no_db_manager(self):
        """Test loading puzzles when no DB manager provided."""
        with patch('server.puzzle_manager.load_puzzles_from_csv') as mock_csv:
            mock_csv.return_value = [{'id': 'csv_puzzle'}]
            puzzles = load_puzzles(None)
            
            mock_csv.assert_called_once()
    
    def test_load_puzzles_db_manager_no_client(self):
        """Test loading puzzles when DB manager has no client."""
        mock_db = MagicMock()
        mock_db.client = None
        
        with patch('server.puzzle_manager.load_puzzles_from_csv') as mock_csv:
            mock_csv.return_value = [{'id': 'csv_puzzle'}]
            puzzles = load_puzzles(mock_db)
            
            mock_csv.assert_called_once()


class TestGetRandomPuzzle:
    """Tests for random puzzle selection."""
    
    def test_get_random_puzzle_returns_puzzle(self, sample_puzzles):
        """Test that a puzzle is returned."""
        puzzle = get_random_puzzle(sample_puzzles)
        
        assert puzzle is not None
        assert 'id' in puzzle
        assert 'fen' in puzzle
        assert 'moves' in puzzle
    
    def test_get_random_puzzle_with_theme_filter(self, sample_puzzles):
        """Test filtering by theme."""
        puzzle = get_random_puzzle(sample_puzzles, theme_filter='fork')
        
        assert puzzle is not None
        assert 'fork' in puzzle['themes']
    
    def test_get_random_puzzle_theme_not_found(self, sample_puzzles):
        """Test returns None when theme not found."""
        puzzle = get_random_puzzle(sample_puzzles, theme_filter='nonexistentTheme')
        
        assert puzzle is None
    
    def test_get_random_puzzle_empty_list(self):
        """Test with empty puzzle list returns None."""
        result = get_random_puzzle([])
        assert result is None

    def test_get_random_puzzle_excludes_seen(self, sample_puzzles):
        """Excluded puzzle ids are never served while alternatives exist."""
        random.seed(42)
        seen = {p['id'] for p in sample_puzzles[:-1]}
        only_fresh = sample_puzzles[-1]

        for _ in range(50):
            puzzle = get_random_puzzle(sample_puzzles, exclude_ids=seen)
            assert puzzle['id'] == only_fresh['id']

    def test_get_random_puzzle_all_excluded_allows_repeats(self, sample_puzzles):
        """When everything has been seen, repeats are allowed over failing."""
        seen = {p['id'] for p in sample_puzzles}
        puzzle = get_random_puzzle(sample_puzzles, exclude_ids=seen)
        assert puzzle is not None

    def test_get_random_puzzle_uniform_selection(self, sample_puzzles):
        """Selection is roughly uniform (no popularity concentration)."""
        random.seed(42)
        selections = {}
        for _ in range(1000):
            puzzle = get_random_puzzle(sample_puzzles)
            selections[puzzle['id']] = selections.get(puzzle['id'], 0) + 1

        expected = 1000 / len(sample_puzzles)
        for count in selections.values():
            assert count > expected * 0.5


class TestGetRatingMatchedPuzzle:
    """Tests for rating-matched puzzle selection."""
    
    def test_get_rating_matched_puzzle_finds_match(self, sample_puzzles):
        """Test finding a puzzle within rating range."""
        puzzle = get_rating_matched_puzzle(sample_puzzles, 'fork', 1500)
        
        assert puzzle is not None
        assert 'fork' in puzzle['themes']
    
    def test_get_rating_matched_puzzle_prefers_close_ratings(self, sample_puzzles):
        """Test that puzzles closer to user rating are preferred."""
        random.seed(42)
        
        # Create puzzles with varying ratings for the same theme
        test_puzzles = [
            {'id': 'p1', 'rating': 1500, 'themes': ['fork'], 'popularity': 50},
            {'id': 'p2', 'rating': 1600, 'themes': ['fork'], 'popularity': 50},
            {'id': 'p3', 'rating': 2000, 'themes': ['fork'], 'popularity': 50},
        ]
        
        selections = {}
        for _ in range(500):
            puzzle = get_rating_matched_puzzle(test_puzzles, 'fork', 1550)
            pid = puzzle['id']
            selections[pid] = selections.get(pid, 0) + 1
        
        # p1 and p2 should be selected more than p3 (which is far from 1550)
        assert selections.get('p1', 0) + selections.get('p2', 0) > selections.get('p3', 0)
    
    def test_get_rating_matched_puzzle_theme_not_found(self, sample_puzzles):
        """Test returns None when theme not found."""
        puzzle = get_rating_matched_puzzle(sample_puzzles, 'nonexistentTheme', 1500)
        
        assert puzzle is None
    
    def test_get_rating_matched_puzzle_excludes_seen(self):
        """Unseen puzzles win even when a seen one matches the rating better."""
        random.seed(42)
        test_puzzles = [
            {'id': 'seen', 'rating': 1550, 'themes': ['fork'], 'popularity': 90},
            {'id': 'fresh', 'rating': 1700, 'themes': ['fork'], 'popularity': 50},
        ]
        for _ in range(25):
            puzzle = get_rating_matched_puzzle(test_puzzles, 'fork', 1550,
                                               exclude_ids={'seen'})
            assert puzzle['id'] == 'fresh'

    def test_get_rating_matched_puzzle_all_seen_allows_repeats(self):
        """A fully-seen theme still serves a puzzle rather than nothing."""
        test_puzzles = [
            {'id': 'seen', 'rating': 1550, 'themes': ['fork'], 'popularity': 90},
        ]
        puzzle = get_rating_matched_puzzle(test_puzzles, 'fork', 1550,
                                           exclude_ids={'seen'})
        assert puzzle is not None

    def test_get_rating_matched_puzzle_expands_range(self):
        """Test that range expands when no exact matches found."""
        # All puzzles are far from target rating
        test_puzzles = [
            {'id': 'p1', 'rating': 2500, 'themes': ['fork'], 'popularity': 50},
        ]
        
        puzzle = get_rating_matched_puzzle(test_puzzles, 'fork', 1200)
        
        # Should still return a puzzle (expanded range)
        assert puzzle is not None


class TestGetAdaptivePuzzle:
    """Tests for adaptive puzzle selection based on user weaknesses."""
    
    def test_get_adaptive_puzzle_returns_puzzle(self, sample_puzzles):
        """Test that a puzzle is returned."""
        user_ratings = {'fork': 1400, 'pin': 1600, 'mate': 1500}
        
        puzzle = get_adaptive_puzzle(sample_puzzles, user_ratings)
        
        assert puzzle is not None
    
    def test_get_adaptive_puzzle_prefers_weak_categories(self, sample_puzzles):
        """Test that weaker categories are selected more often."""
        random.seed(42)
        
        # User is very weak in 'fork', strong in others
        user_ratings = {
            'fork': 1000,  # Very weak
            'pin': 2000,   # Very strong
            'mate': 2000,
            'endgame': 2000,
            'deflection': 2000,
            'quietMove': 2000,
            'kingsideAttack': 2000,
            'discoveredAttack': 2000,
            'capturingDefender': 2000,
            'defensiveMove': 2000,
        }
        
        theme_selections = {}
        for _ in range(500):
            puzzle = get_adaptive_puzzle(sample_puzzles, user_ratings)
            if puzzle:
                for theme in puzzle['themes']:
                    if theme in TRACKED_THEMES:
                        theme_selections[theme] = theme_selections.get(theme, 0) + 1
        
        # Fork should be selected significantly more often
        fork_count = theme_selections.get('fork', 0)
        pin_count = theme_selections.get('pin', 0)
        
        assert fork_count > pin_count
    
    def test_get_adaptive_puzzle_empty_ratings(self, sample_puzzles):
        """Test with empty user ratings (all default)."""
        puzzle = get_adaptive_puzzle(sample_puzzles, {})
        
        assert puzzle is not None
    
    def test_get_adaptive_puzzle_fallback_to_random(self):
        """Test fallback when no themed puzzle found."""
        # Puzzles with themes not in tracked themes
        test_puzzles = [
            {'id': 'p1', 'rating': 1500, 'themes': ['opening'], 'popularity': 50},
        ]
        
        with patch('server.puzzle_manager.get_random_puzzle') as mock_random:
            mock_random.return_value = test_puzzles[0]
            puzzle = get_adaptive_puzzle(test_puzzles, {'fork': 1200})
            
            # Should fall back to random puzzle
            mock_random.assert_called()


class TestDefaultRating:
    """Tests for default rating constant."""
    
    def test_default_rating_value(self):
        """Verify default rating is 1600."""
        assert DEFAULT_RATING == 1600
