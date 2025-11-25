import unittest
from unittest.mock import patch, MagicMock
from server.user_manager import UserManager

class TestUserManager(unittest.TestCase):
    def setUp(self):
        self.user_manager = UserManager()

    def test_get_login_url(self):
        url = self.user_manager.get_login_url()
        self.assertIn('https://lichess.org/oauth', url)
        self.assertIn('client_id=', url)
        self.assertIn('redirect_uri=', url)

    @patch('server.user_manager.requests.post')
    def test_handle_callback_success(self, mock_post):
        # Mock the response from Lichess
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'fake_token'}
        mock_post.return_value = mock_response

        result = self.user_manager.handle_callback('fake_code')
        self.assertEqual(result, {'access_token': 'fake_token'})

    @patch('server.user_manager.requests.get')
    def test_get_user_info_success(self, mock_get):
        # Mock the response from Lichess
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'username': 'testuser'}
        mock_get.return_value = mock_response

        result = self.user_manager.get_user_info('fake_token')
        self.assertEqual(result, {'username': 'testuser'})

if __name__ == '__main__':
    unittest.main()
