# tests/test_routes.py
"""
Tests for Flask routes - comprehensive testing of all endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))


class TestIndexRoute:
    """Tests for the index/home route."""
    
    def test_index_not_logged_in(self, app_client):
        """Test index page when not logged in."""
        response = app_client.get('/')
        
        assert response.status_code == 200
        assert b'Login' in response.data or b'login' in response.data
    
    def test_index_logged_in(self, logged_in_client):
        """Test index page when logged in."""
        response = logged_in_client.get('/')
        
        assert response.status_code == 200
        # Should show training options instead of login
        assert b'Training' in response.data or b'Continue' in response.data or b'Puzzle' in response.data


class TestLichessOAuthRoutes:
    """Tests for Lichess OAuth routes."""
    
    def test_login_redirects_to_lichess(self, app_client):
        """Test that /login redirects to Lichess OAuth."""
        response = app_client.get('/login', follow_redirects=False)
        
        assert response.status_code == 302
        assert 'lichess.org' in response.location
    
    def test_login_stores_state_in_session(self, app_client):
        """Test that login stores OAuth state in session."""
        with app_client.session_transaction() as sess:
            # Clear any existing state
            sess.pop('oauth_state', None)
        
        response = app_client.get('/login', follow_redirects=False)
        
        with app_client.session_transaction() as sess:
            assert 'oauth_state' in sess
            assert 'oauth_code_verifier' in sess
    
    def test_callback_without_code(self, app_client):
        """Test callback without authorization code."""
        with app_client.session_transaction() as sess:
            sess['oauth_state'] = 'test-state'
            sess['oauth_code_verifier'] = 'test-verifier'
        
        response = app_client.get('/callback?state=test-state')
        
        assert response.status_code == 400
        assert b'No authorization code' in response.data
    
    def test_callback_with_error(self, app_client):
        """Test callback with OAuth error."""
        response = app_client.get('/callback?error=access_denied&error_description=User%20denied')
        
        assert response.status_code == 400
        assert b'User denied' in response.data or b'Login failed' in response.data
    
    def test_callback_invalid_state(self, app_client):
        """Test callback with mismatched state."""
        with app_client.session_transaction() as sess:
            sess['oauth_state'] = 'correct-state'
            sess['oauth_code_verifier'] = 'test-verifier'
        
        response = app_client.get('/callback?code=test-code&state=wrong-state')
        
        assert response.status_code == 400
        assert b'Invalid state' in response.data or b'state' in response.data.lower()
    
    def test_callback_no_stored_state(self, app_client):
        """Test callback when session has no stored state."""
        response = app_client.get('/callback?code=test-code&state=some-state')
        
        assert response.status_code == 400
        assert b'Session expired' in response.data or b'cookies' in response.data.lower()
    
    def test_callback_success(self, app_client, mock_user_manager, mock_db_manager):
        """Test successful OAuth callback."""
        with app_client.session_transaction() as sess:
            sess['oauth_state'] = 'test-state'
            sess['oauth_code_verifier'] = 'test-verifier'
        
        with patch('server.main.user_manager', mock_user_manager):
            with patch('server.main.db_manager', mock_db_manager):
                response = app_client.get('/callback?code=valid-code&state=test-state', follow_redirects=False)
        
        # Should redirect to index after successful login
        assert response.status_code == 302
    
    def test_logout_clears_session(self, logged_in_client):
        """Test that logout clears user session."""
        response = logged_in_client.get('/logout', follow_redirects=False)
        
        assert response.status_code == 302
        
        with logged_in_client.session_transaction() as sess:
            assert 'user' not in sess


class TestGoogleOAuthRoutes:
    """Tests for Google OAuth routes."""
    
    def test_google_login_not_configured(self, app_client, mock_google_oauth):
        """Test Google login when not configured."""
        mock_google_oauth.is_configured.return_value = False
        
        with patch('server.main.google_oauth', mock_google_oauth):
            response = app_client.get('/login/google')
        
        assert response.status_code == 500
        assert b'not configured' in response.data.lower()
    
    def test_google_login_redirects(self, app_client, mock_google_oauth):
        """Test Google login redirects to Google."""
        mock_google_oauth.is_configured.return_value = True
        mock_google_oauth.get_login_url.return_value = 'https://accounts.google.com/oauth'
        
        with patch('server.main.google_oauth', mock_google_oauth):
            response = app_client.get('/login/google', follow_redirects=False)
        
        assert response.status_code == 302
        assert 'google' in response.location.lower()
    
    def test_google_callback_with_error(self, app_client):
        """Test Google callback with error."""
        response = app_client.get('/callback/google?error=access_denied&error_description=Denied')
        
        assert response.status_code == 400
        assert b'Google login failed' in response.data or b'Denied' in response.data
    
    def test_google_callback_invalid_state(self, app_client):
        """Test Google callback with mismatched state."""
        with app_client.session_transaction() as sess:
            sess['google_oauth_state'] = 'correct-state'
        
        response = app_client.get('/callback/google?code=test-code&state=wrong-state')
        
        assert response.status_code == 400
    
    def test_google_callback_success(self, app_client, mock_google_oauth, mock_db_manager):
        """Test successful Google OAuth callback."""
        with app_client.session_transaction() as sess:
            sess['google_oauth_state'] = 'test-state'
        
        with patch('server.main.google_oauth', mock_google_oauth):
            with patch('server.main.db_manager', mock_db_manager):
                response = app_client.get('/callback/google?code=valid-code&state=test-state', follow_redirects=False)
        
        assert response.status_code == 302


class TestPuzzleRoutes:
    """Tests for puzzle-related routes."""
    
    def test_random_puzzle_view(self, app_client):
        """Test random puzzle view."""
        response = app_client.get('/puzzle/random/view')
        
        assert response.status_code == 200
        # Should render puzzle template
        assert b'puzzle' in response.data.lower() or b'chess' in response.data.lower()
    
    def test_random_puzzle_view_with_theme(self, app_client):
        """Test random puzzle view with theme filter."""
        response = app_client.get('/puzzle/random/view?theme=fork')
        
        assert response.status_code == 200
    
    def test_random_puzzle_view_logged_in(self, logged_in_client):
        """Test random puzzle view when logged in (adaptive selection)."""
        response = logged_in_client.get('/puzzle/random/view')
        
        assert response.status_code == 200


class TestAttemptAPI:
    """Tests for puzzle attempt API."""
    
    def test_record_attempt_not_logged_in(self, app_client):
        """Test attempt recording when not logged in."""
        response = app_client.post('/api/puzzle/attempt', json={
            'puzzle_id': 'test-puzzle',
            'success': True
        })
        
        assert response.status_code == 401
    
    def test_record_attempt_no_db_id(self, app_client):
        """Test attempt recording when user has no db_id."""
        with app_client.session_transaction() as sess:
            sess['user'] = {'username': 'test'}  # No db_id
        
        response = app_client.post('/api/puzzle/attempt', json={
            'puzzle_id': 'test-puzzle',
            'success': True
        })
        
        assert response.status_code == 401
    
    def test_record_attempt_no_data(self, logged_in_client):
        """Test attempt recording with no JSON data."""
        response = logged_in_client.post('/api/puzzle/attempt', 
                                         content_type='application/json')
        
        # Flask returns 400 or 415 depending on content-type handling
        assert response.status_code in [400, 415]
    
    def test_record_attempt_missing_puzzle_id(self, logged_in_client):
        """Test attempt recording without puzzle_id."""
        response = logged_in_client.post('/api/puzzle/attempt', json={
            'success': True
        })
        
        assert response.status_code == 400
    
    def test_record_attempt_success(self, logged_in_client, mock_db_manager):
        """Test successful attempt recording."""
        mock_db_manager.get_user_category_ratings.return_value = {'fork': 1500}
        mock_db_manager.update_user_category_rating.return_value = {
            'old_rating': 1500,
            'new_rating': 1520,
            'change': 20,
            'attempts': 1,
            'k_factor': 250
        }
        
        with patch('server.main.db_manager', mock_db_manager):
            response = logged_in_client.post('/api/puzzle/attempt', json={
                'puzzle_id': 'puzzle1',  # From sample_puzzles (has 'fork' theme)
                'success': True
            })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'overall_rating' in data


class TestStatsRoute:
    """Tests for stats route."""
    
    def test_stats_not_logged_in(self, app_client):
        """Test stats page redirects when not logged in."""
        response = app_client.get('/stats', follow_redirects=False)
        
        assert response.status_code == 302
        assert 'login' in response.location
    
    def test_stats_logged_in(self, logged_in_client, mock_db_manager):
        """Test stats page when logged in."""
        mock_db_manager.get_user_category_ratings.return_value = {
            'fork': 1500,
            'pin': 1600
        }
        
        with patch('server.main.db_manager', mock_db_manager):
            response = logged_in_client.get('/stats')
        
        assert response.status_code == 200
        assert b'stats' in response.data.lower() or b'rating' in response.data.lower()


class TestResetRatingsAPI:
    """Tests for rating reset API."""
    
    def test_reset_ratings_not_logged_in(self, app_client):
        """Test reset ratings when not logged in."""
        response = app_client.post('/api/reset-ratings')
        
        assert response.status_code == 401
    
    def test_reset_ratings_success(self, logged_in_client, mock_db_manager):
        """Test successful rating reset."""
        mock_db_manager.reset_user_ratings.return_value = True
        
        with patch('server.main.db_manager', mock_db_manager):
            response = logged_in_client.post('/api/reset-ratings')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_reset_ratings_failure(self, logged_in_client, mock_db_manager):
        """Test rating reset failure."""
        mock_db_manager.reset_user_ratings.return_value = False
        
        with patch('server.main.db_manager', mock_db_manager):
            response = logged_in_client.post('/api/reset-ratings')
        
        assert response.status_code == 500


class TestAdminResetAPI:
    """Tests for admin reset all ratings API."""
    
    def test_admin_reset_no_key(self, app_client):
        """Test admin reset without API key."""
        response = app_client.post('/api/admin/reset-all-ratings')
        
        assert response.status_code == 403
    
    def test_admin_reset_wrong_key(self, app_client):
        """Test admin reset with wrong API key."""
        response = app_client.post('/api/admin/reset-all-ratings',
                                   headers={'X-Admin-Key': 'wrong-key'})
        
        assert response.status_code == 403
    
    def test_admin_reset_success(self, app_client, mock_db_manager, monkeypatch):
        """Test successful admin reset."""
        monkeypatch.setenv('ADMIN_KEY', 'correct-key')
        mock_db_manager.reset_all_user_ratings.return_value = 5
        
        with patch('server.main.db_manager', mock_db_manager):
            response = app_client.post('/api/admin/reset-all-ratings',
                                       headers={'X-Admin-Key': 'correct-key'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['users_affected'] == 5

