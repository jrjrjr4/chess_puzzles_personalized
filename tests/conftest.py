# tests/conftest.py
"""
Pytest configuration and shared fixtures for the chess puzzles app.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add project root and server directory to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'server'))

# Sample puzzle data for testing
SAMPLE_PUZZLES = [
    {
        'id': 'puzzle1',
        'fen': 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
        'moves': ['e4', 'e5', 'Nf3'],
        'rating': 1500,
        'themes': ['fork', 'middlegame', 'short'],
        'popularity': 85
    },
    {
        'id': 'puzzle2',
        'fen': 'r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3',
        'moves': ['d4', 'exd4'],
        'rating': 1200,
        'themes': ['pin', 'opening', 'short'],
        'popularity': 92
    },
    {
        'id': 'puzzle3',
        'fen': '8/8/4k3/8/8/4K3/4P3/8 w - - 0 1',
        'moves': ['Kd4', 'Kd6', 'e4'],
        'rating': 1800,
        'themes': ['endgame', 'pawnEndgame'],
        'popularity': 78
    },
    {
        'id': 'puzzle4',
        'fen': 'r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
        'moves': ['Ng5', 'd5'],
        'rating': 1600,
        'themes': ['mate', 'mateIn2', 'middlegame'],
        'popularity': 95
    },
    {
        'id': 'puzzle5',
        'fen': 'r2qkb1r/ppp2ppp/2n1bn2/3pp3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 0 5',
        'moves': ['exd5', 'Nxd5'],
        'rating': 1400,
        'themes': ['deflection', 'middlegame'],
        'popularity': 70
    },
    {
        'id': 'puzzle6',
        'fen': 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
        'moves': ['d3', 'Be7'],
        'rating': 1550,
        'themes': ['quietMove', 'positional'],
        'popularity': 60
    },
    {
        'id': 'puzzle7',
        'fen': 'r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R b KQkq - 0 4',
        'moves': ['O-O', 'Bg5'],
        'rating': 1700,
        'themes': ['kingsideAttack', 'attack'],
        'popularity': 88
    },
    {
        'id': 'puzzle8',
        'fen': 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
        'moves': ['Nc3', 'Bb4'],
        'rating': 1650,
        'themes': ['discoveredAttack', 'tactics'],
        'popularity': 75
    },
    {
        'id': 'puzzle9',
        'fen': 'r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
        'moves': ['c3', 'd6'],
        'rating': 1450,
        'themes': ['defensiveMove', 'solid'],
        'popularity': 65
    },
    {
        'id': 'puzzle10',
        'fen': 'r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
        'moves': ['Bxf7+', 'Kxf7'],
        'rating': 1750,
        'themes': ['capturingDefender', 'sacrifice'],
        'popularity': 90
    },
]


@pytest.fixture
def sample_puzzles():
    """Returns a list of sample puzzles for testing."""
    return SAMPLE_PUZZLES.copy()


@pytest.fixture
def mock_db_manager():
    """Returns a mocked DBManager instance."""
    mock = MagicMock()
    mock.client = MagicMock()
    mock.get_all_puzzles.return_value = SAMPLE_PUZZLES.copy()
    mock.get_or_create_user.return_value = {'id': 'user-uuid-123', 'lichess_id': 'testuser'}
    mock.get_or_create_google_user.return_value = {'id': 'user-uuid-456', 'google_id': '12345'}
    mock.get_user_category_ratings.return_value = {}
    mock.get_user_category_full_data.return_value = {}
    return mock


@pytest.fixture
def mock_user_manager():
    """Returns a mocked UserManager instance."""
    mock = MagicMock()
    mock.generate_pkce_pair.return_value = ('verifier123', 'challenge123')
    mock.get_login_url.return_value = 'https://lichess.org/oauth?...'
    mock.handle_callback.return_value = {'access_token': 'test_token'}
    mock.get_user_info.return_value = {'id': 'testuser', 'username': 'TestUser'}
    mock.revoke_token.return_value = True
    return mock


@pytest.fixture
def mock_google_oauth():
    """Returns a mocked GoogleOAuth instance."""
    mock = MagicMock()
    mock.is_configured.return_value = True
    mock.get_login_url.return_value = 'https://accounts.google.com/o/oauth2/v2/auth?...'
    mock.handle_callback.return_value = {
        'sub': 'google-user-123',
        'email': 'test@gmail.com',
        'name': 'Test User',
        'picture': 'https://example.com/photo.jpg'
    }
    return mock


@pytest.fixture
def app_client(mock_db_manager, mock_user_manager, mock_google_oauth):
    """Returns a Flask test client with mocked dependencies."""
    # We need to patch before importing
    with patch.dict(os.environ, {'FLASK_SECRET_KEY': 'test-secret-key'}):
        with patch('server.main.db_manager', mock_db_manager):
            with patch('server.main.user_manager', mock_user_manager):
                with patch('server.main.google_oauth', mock_google_oauth):
                    from server.main import app
                    app.config['TESTING'] = True
                    app.config['WTF_CSRF_ENABLED'] = False
                    with app.test_client() as client:
                        yield client


@pytest.fixture
def logged_in_client(app_client):
    """Returns a Flask test client with a logged-in user session."""
    with app_client.session_transaction() as sess:
        sess['user'] = {
            'id': 'testuser',
            'username': 'TestUser',
            'db_id': 'user-uuid-123',
            'access_token': 'test_token',
            'provider': 'lichess'
        }
    return app_client


@pytest.fixture
def google_logged_in_client(app_client):
    """Returns a Flask test client with a Google-logged-in user session."""
    with app_client.session_transaction() as sess:
        sess['user'] = {
            'id': 'google-user-123',
            'username': 'Test User',
            'email': 'test@gmail.com',
            'db_id': 'user-uuid-456',
            'provider': 'google'
        }
    return app_client


# Mock environment for tests that don't need real credentials
@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set up mock environment variables for all tests."""
    monkeypatch.setenv('FLASK_SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('LICHESS_CLIENT_ID', 'test-lichess-client')
    # Don't set Google credentials by default - tests can add them if needed

