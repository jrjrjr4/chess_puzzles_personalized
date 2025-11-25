import unittest
from unittest.mock import patch, MagicMock
from server.user_manager import UserManager

class TestUserManager(unittest.TestCase):
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

if __name__ == '__main__':
    unittest.main()
