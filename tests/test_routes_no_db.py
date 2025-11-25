import sys
import os

# Add server directory to path so imports in main.py work
sys.path.append(os.path.join(os.getcwd(), 'server'))

import unittest
from unittest.mock import patch, MagicMock
from flask import session

# Mock environment variables BEFORE importing main
# We want to ensure SUPABASE vars are missing, but keep others (like PATH)
env_patch = os.environ.copy()
if 'SUPABASE_URL' in env_patch: del env_patch['SUPABASE_URL']
if 'SUPABASE_KEY' in env_patch: del env_patch['SUPABASE_KEY']

with patch.dict(os.environ, env_patch, clear=True):
    from server.main import app

class TestRoutesNoDB(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True
        app.secret_key = 'test_secret'

    @patch('server.main.user_manager')
    @patch('server.main.db_manager')
    def test_callback_flow_no_db(self, mock_db_manager, mock_user_manager):
        # Setup mocks
        mock_user_manager.handle_callback.return_value = {'access_token': 'token'}
        mock_user_manager.get_user_info.return_value = {'id': 'lichess_id', 'username': 'testuser'}
        
        # Simulate DB manager returning None (as it would if no creds)
        mock_db_manager.get_or_create_user.return_value = None

        # Test callback route
        with self.client as c:
            response = c.get('/callback?code=fake_code', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            
            # Check session
            self.assertIn('user', session)
            self.assertEqual(session['user']['username'], 'testuser')
            # db_id should NOT be in user info
            self.assertNotIn('db_id', session['user'])

    def test_record_attempt_no_db_id(self):
        # Simulate logged in user WITHOUT db_id
        with self.client.session_transaction() as sess:
            sess['user'] = {'username': 'testuser'} # No db_id

        response = self.client.post('/api/puzzle/attempt', json={
            'puzzle_id': '123',
            'success': True
        })
        
        # Should return 401 or error because db_id is missing
        # In main.py: if not user or 'db_id' not in user: return ..., 401
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main()
