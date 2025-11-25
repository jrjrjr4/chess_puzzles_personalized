import os
import requests
import urllib.parse

class UserManager:
    def __init__(self):
        self.client_id = os.environ.get('LICHESS_CLIENT_ID', 'example-client-id')
        self.client_secret = os.environ.get('LICHESS_CLIENT_SECRET', 'example-client-secret')
        self.redirect_uri = 'http://localhost:5000/callback'
        self.lichess_auth_url = 'https://lichess.org/oauth'
        self.lichess_token_url = 'https://lichess.org/api/token'
        self.lichess_api_url = 'https://lichess.org/api/account'

    def get_login_url(self):
        """Generates the Lichess OAuth login URL."""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'preference:read', # Add scopes as needed
            # 'state': 'random_string' # Should implement state for security
        }
        return f"{self.lichess_auth_url}?{urllib.parse.urlencode(params)}"

    def handle_callback(self, code):
        """Exchanges the authorization code for an access token."""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        response = requests.post(self.lichess_token_url, data=data)
        if response.status_code == 200:
            return response.json()
        return None

    def get_user_info(self, access_token):
        """Fetches user profile information using the access token."""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(self.lichess_api_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None
