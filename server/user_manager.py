import os
import secrets
import hashlib
import base64
import requests
import urllib.parse
from authlib.integrations.requests_client import OAuth2Session


class GoogleOAuth:
    """Handles Google OAuth 2.0 authentication."""
    
    def __init__(self):
        self.client_id = os.environ.get('GOOGLE_CLIENT_ID')
        self.client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
        self.redirect_uri = f'{base_url}/callback/google'
        
        self.authorization_endpoint = 'https://accounts.google.com/o/oauth2/v2/auth'
        self.token_endpoint = 'https://oauth2.googleapis.com/token'
        self.userinfo_endpoint = 'https://www.googleapis.com/oauth2/v3/userinfo'
    
    def is_configured(self):
        """Check if Google OAuth is properly configured."""
        return bool(self.client_id and self.client_secret)
    
    def get_login_url(self, state):
        """Generate the Google OAuth login URL."""
        if not self.is_configured():
            return None
        
        session = OAuth2Session(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope='openid email profile'
        )
        
        uri, _ = session.create_authorization_url(
            self.authorization_endpoint,
            state=state
        )
        return uri
    
    def handle_callback(self, code):
        """Exchange authorization code for tokens and get user info."""
        if not self.is_configured():
            return None
        
        try:
            session = OAuth2Session(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri
            )
            
            # Exchange code for token
            token = session.fetch_token(
                self.token_endpoint,
                code=code
            )
            
            # Get user info
            resp = session.get(self.userinfo_endpoint)
            if resp.status_code == 200:
                return resp.json()
            
            print(f"Failed to get Google user info: {resp.status_code}")
            return None
            
        except Exception as e:
            print(f"Google OAuth error: {e}")
            return None


class UserManager:
    def __init__(self):
        # For PKCE flow, we only need a client_id (can be any unique string)
        # No client_secret needed!
        self.client_id = os.environ.get('LICHESS_CLIENT_ID', 'chess-puzzles-personalized')
        
        # Determine redirect URI based on environment
        base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
        self.redirect_uri = f'{base_url}/callback'
        
        self.lichess_auth_url = 'https://lichess.org/oauth'
        self.lichess_token_url = 'https://lichess.org/api/token'
        self.lichess_api_url = 'https://lichess.org/api/account'

    def generate_pkce_pair(self):
        """
        Generate a PKCE code verifier and code challenge.
        Returns (code_verifier, code_challenge)
        """
        # Generate a random code verifier (43-128 characters)
        code_verifier = secrets.token_urlsafe(64)
        
        # Create code challenge using S256 method
        code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge

    def get_login_url(self, code_challenge, state, redirect_uri=None):
        """
        Generates the Lichess OAuth login URL with PKCE.
        
        Args:
            code_challenge: The PKCE code challenge (S256 hash of verifier)
            state: Random state string for CSRF protection
        """
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': redirect_uri or self.redirect_uri,
            'scope': 'preference:read',  # Minimal scope - just need to identify user
            'code_challenge_method': 'S256',
            'code_challenge': code_challenge,
            'state': state,
        }
        return f"{self.lichess_auth_url}?{urllib.parse.urlencode(params)}"

    def handle_callback(self, code, code_verifier, redirect_uri=None):
        """
        Exchanges the authorization code for an access token using PKCE.
        
        Args:
            code: The authorization code from Lichess
            code_verifier: The original PKCE code verifier
        """
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri or self.redirect_uri,
            'client_id': self.client_id,
            'code_verifier': code_verifier,
        }
        
        response = requests.post(self.lichess_token_url, data=data)
        if response.status_code == 200:
            return response.json()
        
        # Log error for debugging
        print(f"Token exchange failed: {response.status_code} - {response.text}")
        return None

    def get_user_info(self, access_token):
        """Fetches user profile information using the access token."""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(self.lichess_api_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None

    def revoke_token(self, access_token):
        """Revoke an access token (call on logout)."""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.delete(self.lichess_token_url, headers=headers)
        return response.status_code == 204
