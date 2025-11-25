# tests/test_user_manager.py
"""
Tests for user_manager.py - Lichess and Google OAuth functionality.
"""
import unittest
from unittest.mock import patch, MagicMock
import pytest

from server.user_manager import UserManager, GoogleOAuth


class TestUserManager(unittest.TestCase):
    """Tests for Lichess OAuth (UserManager class)."""
    
    def setUp(self):
        self.user_manager = UserManager()

    def test_generate_pkce_pair(self):
        """Test that PKCE pair generation produces valid values."""
        verifier, challenge = self.user_manager.generate_pkce_pair()
        
        # Verifier should be a non-empty string
        self.assertIsInstance(verifier, str)
        self.assertTrue(len(verifier) > 40)  # Should be ~86 chars for 64 bytes
        
        # Challenge should be a non-empty string (base64url encoded)
        self.assertIsInstance(challenge, str)
        self.assertTrue(len(challenge) > 0)
        
        # Challenge should not contain padding
        self.assertNotIn('=', challenge)

    def test_pkce_pair_unique(self):
        """Test that each PKCE pair is unique."""
        pairs = [self.user_manager.generate_pkce_pair() for _ in range(10)]
        verifiers = [p[0] for p in pairs]
        
        # All verifiers should be unique
        self.assertEqual(len(verifiers), len(set(verifiers)))

    def test_get_login_url(self):
        """Test that login URL contains all required PKCE parameters."""
        verifier, challenge = self.user_manager.generate_pkce_pair()
        state = 'test_state_123'
        
        url = self.user_manager.get_login_url(challenge, state)
        
        self.assertIn('https://lichess.org/oauth', url)
        self.assertIn('client_id=', url)
        self.assertIn('redirect_uri=', url)
        self.assertIn('code_challenge=', url)
        self.assertIn('code_challenge_method=S256', url)
        self.assertIn('state=test_state_123', url)
        self.assertIn('response_type=code', url)

    def test_get_login_url_scope(self):
        """Test that login URL requests correct scope."""
        verifier, challenge = self.user_manager.generate_pkce_pair()
        url = self.user_manager.get_login_url(challenge, 'state')
        
        self.assertIn('scope=', url)

    @patch('server.user_manager.requests.post')
    def test_handle_callback_success(self, mock_post):
        """Test successful token exchange with PKCE."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'fake_token'}
        mock_post.return_value = mock_response

        result = self.user_manager.handle_callback('fake_code', 'fake_verifier')
        
        self.assertEqual(result, {'access_token': 'fake_token'})
        
        # Verify the request was made with code_verifier
        call_args = mock_post.call_args
        self.assertIn('code_verifier', call_args.kwargs.get('data', call_args[1].get('data', {})))

    @patch('server.user_manager.requests.post')
    def test_handle_callback_failure(self, mock_post):
        """Test failed token exchange."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid code'
        mock_post.return_value = mock_response

        result = self.user_manager.handle_callback('bad_code', 'fake_verifier')
        
        self.assertIsNone(result)

    @patch('server.user_manager.requests.post')
    def test_handle_callback_server_error(self, mock_post):
        """Test token exchange with server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        result = self.user_manager.handle_callback('code', 'verifier')
        
        self.assertIsNone(result)

    @patch('server.user_manager.requests.get')
    def test_get_user_info_success(self, mock_get):
        """Test fetching user info with access token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'testuser', 'username': 'TestUser'}
        mock_get.return_value = mock_response

        result = self.user_manager.get_user_info('fake_token')
        
        self.assertEqual(result, {'id': 'testuser', 'username': 'TestUser'})
        
        # Verify Authorization header was set
        call_args = mock_get.call_args
        headers = call_args.kwargs.get('headers', call_args[1].get('headers', {}))
        self.assertEqual(headers.get('Authorization'), 'Bearer fake_token')

    @patch('server.user_manager.requests.get')
    def test_get_user_info_failure(self, mock_get):
        """Test failed user info fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = self.user_manager.get_user_info('invalid_token')
        
        self.assertIsNone(result)

    @patch('server.user_manager.requests.delete')
    def test_revoke_token_success(self, mock_delete):
        """Test successful token revocation."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        result = self.user_manager.revoke_token('fake_token')
        
        self.assertTrue(result)

    @patch('server.user_manager.requests.delete')
    def test_revoke_token_failure(self, mock_delete):
        """Test failed token revocation."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_delete.return_value = mock_response

        result = self.user_manager.revoke_token('invalid_token')
        
        self.assertFalse(result)


class TestGoogleOAuth:
    """Tests for Google OAuth functionality."""
    
    def test_is_configured_with_credentials(self, monkeypatch):
        """Test is_configured returns True with credentials."""
        monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
        
        google = GoogleOAuth()
        
        assert google.is_configured() == True
    
    def test_is_configured_without_credentials(self, monkeypatch):
        """Test is_configured returns False without credentials."""
        monkeypatch.delenv('GOOGLE_CLIENT_ID', raising=False)
        monkeypatch.delenv('GOOGLE_CLIENT_SECRET', raising=False)
        
        google = GoogleOAuth()
        
        assert google.is_configured() == False
    
    def test_is_configured_partial_credentials(self, monkeypatch):
        """Test is_configured returns False with only client ID."""
        monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client-id')
        monkeypatch.delenv('GOOGLE_CLIENT_SECRET', raising=False)
        
        google = GoogleOAuth()
        
        assert google.is_configured() == False
    
    def test_get_login_url_not_configured(self, monkeypatch):
        """Test get_login_url returns None when not configured."""
        monkeypatch.delenv('GOOGLE_CLIENT_ID', raising=False)
        monkeypatch.delenv('GOOGLE_CLIENT_SECRET', raising=False)
        
        google = GoogleOAuth()
        
        assert google.get_login_url('state123') is None
    
    def test_get_login_url_configured(self, monkeypatch):
        """Test get_login_url returns valid URL when configured."""
        monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
        monkeypatch.setenv('BASE_URL', 'http://localhost:5000')
        
        google = GoogleOAuth()
        
        with patch('server.user_manager.OAuth2Session') as MockSession:
            mock_session = MagicMock()
            mock_session.create_authorization_url.return_value = ('https://accounts.google.com/auth?...', 'state')
            MockSession.return_value = mock_session
            
            url = google.get_login_url('state123')
            
            assert url is not None
            assert 'google' in url.lower()
    
    def test_handle_callback_not_configured(self, monkeypatch):
        """Test handle_callback returns None when not configured."""
        monkeypatch.delenv('GOOGLE_CLIENT_ID', raising=False)
        monkeypatch.delenv('GOOGLE_CLIENT_SECRET', raising=False)
        
        google = GoogleOAuth()
        
        result = google.handle_callback('auth-code')
        
        assert result is None
    
    def test_handle_callback_success(self, monkeypatch):
        """Test successful Google OAuth callback."""
        monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
        
        google = GoogleOAuth()
        
        with patch('server.user_manager.OAuth2Session') as MockSession:
            mock_session = MagicMock()
            mock_session.fetch_token.return_value = {'access_token': 'google-token'}
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'sub': '12345',
                'email': 'test@gmail.com',
                'name': 'Test User',
                'picture': 'https://example.com/photo.jpg'
            }
            mock_session.get.return_value = mock_response
            
            MockSession.return_value = mock_session
            
            result = google.handle_callback('auth-code')
            
            assert result is not None
            assert result['sub'] == '12345'
            assert result['email'] == 'test@gmail.com'
    
    def test_handle_callback_token_error(self, monkeypatch):
        """Test callback when token exchange fails."""
        monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
        
        google = GoogleOAuth()
        
        with patch('server.user_manager.OAuth2Session') as MockSession:
            mock_session = MagicMock()
            mock_session.fetch_token.side_effect = Exception('Token error')
            MockSession.return_value = mock_session
            
            result = google.handle_callback('auth-code')
            
            assert result is None
    
    def test_handle_callback_userinfo_error(self, monkeypatch):
        """Test callback when user info fetch fails."""
        monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
        
        google = GoogleOAuth()
        
        with patch('server.user_manager.OAuth2Session') as MockSession:
            mock_session = MagicMock()
            mock_session.fetch_token.return_value = {'access_token': 'token'}
            
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_session.get.return_value = mock_response
            
            MockSession.return_value = mock_session
            
            result = google.handle_callback('auth-code')
            
            assert result is None
    
    def test_redirect_uri_from_base_url(self, monkeypatch):
        """Test that redirect URI is correctly built from BASE_URL."""
        monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-id')
        monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
        monkeypatch.setenv('BASE_URL', 'https://myapp.com')
        
        google = GoogleOAuth()
        
        assert google.redirect_uri == 'https://myapp.com/callback/google'
    
    def test_redirect_uri_default(self, monkeypatch):
        """Test default redirect URI when BASE_URL not set."""
        monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-id')
        monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
        monkeypatch.delenv('BASE_URL', raising=False)
        
        google = GoogleOAuth()
        
        assert google.redirect_uri == 'http://localhost:5000/callback/google'


class TestUserManagerEnvironment:
    """Tests for UserManager environment configuration."""
    
    def test_client_id_from_env(self, monkeypatch):
        """Test client ID is read from environment."""
        monkeypatch.setenv('LICHESS_CLIENT_ID', 'my-custom-client')
        
        um = UserManager()
        
        assert um.client_id == 'my-custom-client'
    
    def test_client_id_default(self, monkeypatch):
        """Test default client ID when not set."""
        monkeypatch.delenv('LICHESS_CLIENT_ID', raising=False)
        
        um = UserManager()
        
        assert um.client_id == 'chess-puzzles-personalized'
    
    def test_redirect_uri_from_base_url(self, monkeypatch):
        """Test redirect URI built from BASE_URL."""
        monkeypatch.setenv('BASE_URL', 'https://production.com')
        
        um = UserManager()
        
        assert um.redirect_uri == 'https://production.com/callback'
    
    def test_redirect_uri_default(self, monkeypatch):
        """Test default redirect URI."""
        monkeypatch.delenv('BASE_URL', raising=False)
        
        um = UserManager()
        
        assert um.redirect_uri == 'http://localhost:5000/callback'


if __name__ == '__main__':
    unittest.main()
