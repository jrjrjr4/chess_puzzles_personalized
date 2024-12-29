# tests/test_puzzle_manager.py
import pytest
from server.puzzle_manager import load_puzzles, get_random_puzzle

def test_load_puzzles():
    puzzles = load_puzzles()
    assert len(puzzles) > 0, "Should load at least one puzzle"

def test_get_random_puzzle():
    puzzles = load_puzzles()
    puzzle = get_random_puzzle(puzzles, theme_filter="fork")  # or something
    if puzzle:
        assert "fork" in puzzle['themes'], "Puzzle should have 'fork' theme"
