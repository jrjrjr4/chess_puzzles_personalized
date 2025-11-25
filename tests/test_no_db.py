import unittest
from unittest.mock import patch
import os
from server.db_manager import DBManager

class TestDBManagerNoCreds(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_init_no_creds(self):
        # Ensure no SUPABASE env vars exist
        if 'SUPABASE_URL' in os.environ: del os.environ['SUPABASE_URL']
        if 'SUPABASE_KEY' in os.environ: del os.environ['SUPABASE_KEY']
        
        db = DBManager()
        self.assertIsNone(db.client)
        
        # Test methods don't crash
        user = db.get_or_create_user({'id': 'foo', 'username': 'bar'})
        self.assertIsNone(user)
        
        # Should just print error/return None, not raise exception
        db.save_puzzle_attempt('uid', 'pid', True)
        
        history = db.get_user_history('uid')
        self.assertEqual(history, [])

if __name__ == '__main__':
    unittest.main()
