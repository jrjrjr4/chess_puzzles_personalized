# OAuth Authentication Guide

This document explains how OAuth authentication works in Chess Puzzles Personalized and how to configure each provider.

## Overview

The app supports two OAuth providers:
- **Lichess** - OAuth 2.0 with PKCE (no client secret needed)
- **Google** - Standard OAuth 2.0 with client credentials

Users can log in with either provider. Each creates a separate user account in the database.

---

## Lichess OAuth (PKCE)

### What is PKCE?

PKCE (Proof Key for Code Exchange) is an OAuth 2.0 extension that allows secure authentication without a client secret. This is ideal for:
- Public clients (mobile apps, SPAs)
- Applications where storing secrets is difficult
- Simpler setup (no secret management)

### How It Works

```
┌─────────────┐                              ┌─────────────┐
│   Browser   │                              │   Lichess   │
└──────┬──────┘                              └──────┬──────┘
       │                                            │
       │  1. User clicks "Login with Lichess"       │
       │─────────────────────────────────────────>  │
       │                                            │
       │  App generates:                            │
       │  - code_verifier (random string)           │
       │  - code_challenge (SHA256 hash)            │
       │  - state (CSRF token)                      │
       │                                            │
       │  2. Redirect to Lichess with challenge     │
       │─────────────────────────────────────────>  │
       │                                            │
       │  3. User authorizes app                    │
       │                                            │
       │  4. Lichess redirects with code + state    │
       │<─────────────────────────────────────────  │
       │                                            │
       │  5. App verifies state                     │
       │  6. App exchanges code + verifier for token│
       │─────────────────────────────────────────>  │
       │                                            │
       │  7. Lichess verifies:                      │
       │     SHA256(verifier) == challenge          │
       │                                            │
       │  8. Returns access token                   │
       │<─────────────────────────────────────────  │
       │                                            │
       │  9. App fetches user info with token       │
       │─────────────────────────────────────────>  │
       │                                            │
       │  10. Returns user profile                  │
       │<─────────────────────────────────────────  │
       │                                            │
       │  11. App creates session                   │
       │                                            │
```

### Setup Instructions

#### 1. Register Your App on Lichess

1. Go to [lichess.org/account/oauth/app](https://lichess.org/account/oauth/app)
2. Click **Register a new app**
3. Fill in the form:

| Field | Value |
|-------|-------|
| App name | Chess Puzzles Personalized |
| App description | Personal chess puzzle trainer |
| Redirect URI | `http://localhost:5000/callback` |

4. Click **Create**
5. Copy the **Client ID**

#### 2. Configure Environment

Add to your `.env` file:

```env
LICHESS_CLIENT_ID=your-client-id-here
```

That's it! No client secret needed.

#### 3. Production Setup

For production, update the redirect URI in Lichess:
1. Edit your app at [lichess.org/account/oauth/app](https://lichess.org/account/oauth/app)
2. Change redirect URI to `https://your-domain.com/callback`
3. Update `BASE_URL` in your `.env`:
   ```env
   BASE_URL=https://your-domain.com
   ```

### Code Implementation

The PKCE flow is implemented in `server/user_manager.py`:

```python
def generate_pkce_pair(self):
    """Generate code_verifier and code_challenge."""
    # Random 64-byte string, URL-safe base64 encoded
    code_verifier = secrets.token_urlsafe(64)
    
    # SHA256 hash, URL-safe base64 encoded (no padding)
    code_challenge = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode().rstrip('=')
    
    return code_verifier, code_challenge
```

### Scopes

The app requests minimal scopes:
- `preference:read` - Just enough to identify the user

You can add more scopes if needed:
- `email:read` - Access user's email
- `challenge:read` - Read challenges
- `puzzle:read` - Read puzzle activity

---

## Google OAuth

### How It Works

Google uses standard OAuth 2.0 with client credentials:

```
┌─────────────┐                              ┌─────────────┐
│   Browser   │                              │   Google    │
└──────┬──────┘                              └──────┬──────┘
       │                                            │
       │  1. User clicks "Login with Google"        │
       │─────────────────────────────────────────>  │
       │                                            │
       │  App generates state (CSRF token)          │
       │                                            │
       │  2. Redirect to Google                     │
       │─────────────────────────────────────────>  │
       │                                            │
       │  3. User authorizes app                    │
       │                                            │
       │  4. Google redirects with code + state     │
       │<─────────────────────────────────────────  │
       │                                            │
       │  5. App verifies state                     │
       │  6. App exchanges code for token           │
       │     (includes client_id + client_secret)   │
       │─────────────────────────────────────────>  │
       │                                            │
       │  7. Returns access token                   │
       │<─────────────────────────────────────────  │
       │                                            │
       │  8. App fetches user info with token       │
       │─────────────────────────────────────────>  │
       │                                            │
       │  9. Returns user profile                   │
       │<─────────────────────────────────────────  │
       │                                            │
       │  10. App creates session                   │
       │                                            │
```

### Setup Instructions

#### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown → **New Project**
3. Enter a project name → **Create**

#### 2. Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** → **Create**
3. Fill in required fields:

| Field | Value |
|-------|-------|
| App name | Chess Puzzles Personalized |
| User support email | your@email.com |
| Developer contact | your@email.com |

4. Click **Save and Continue**
5. Add scopes:
   - `email`
   - `profile`
   - `openid`
6. Click **Save and Continue**
7. Add test users (if in testing mode)
8. Click **Save and Continue**

#### 3. Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Web application**
4. Configure:

| Field | Value |
|-------|-------|
| Name | Chess Puzzles Web Client |
| Authorized redirect URIs | `http://localhost:5000/callback/google` |

5. Click **Create**
6. Copy **Client ID** and **Client Secret**

#### 4. Configure Environment

Add to your `.env` file:

```env
GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxx
```

#### 5. Production Setup

For production:

1. Edit your OAuth client in Google Cloud Console
2. Add production redirect URI: `https://your-domain.com/callback/google`
3. Update `BASE_URL`:
   ```env
   BASE_URL=https://your-domain.com
   ```
4. Publish your OAuth consent screen (move out of testing mode)

### Code Implementation

Google OAuth is implemented in `server/user_manager.py` using Authlib:

```python
class GoogleOAuth:
    def __init__(self):
        self.client_id = os.environ.get('GOOGLE_CLIENT_ID')
        self.client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = f'{base_url}/callback/google'
        
    def get_login_url(self, state):
        session = OAuth2Session(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope='openid email profile'
        )
        uri, _ = session.create_authorization_url(
            'https://accounts.google.com/o/oauth2/v2/auth',
            state=state
        )
        return uri
```

### Scopes

The app requests:
- `openid` - OpenID Connect (required)
- `email` - User's email address
- `profile` - User's name and profile picture

### User Data from Google

```json
{
  "sub": "123456789",           // Unique Google user ID
  "email": "user@gmail.com",
  "email_verified": true,
  "name": "John Doe",
  "picture": "https://lh3.googleusercontent.com/..."
}
```

---

## Session Management

### Session Cookie Settings

```python
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'   # Allow OAuth redirects
app.config['SESSION_COOKIE_SECURE'] = False      # Set True for HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True     # Prevent XSS
```

### Session Data Structure

After login, the session contains:

**Lichess User:**
```python
{
    'id': 'lichess_username',
    'username': 'LichessUsername',
    'db_id': 'uuid-from-database',
    'access_token': 'lip_xxxxx',
    'provider': 'lichess'
}
```

**Google User:**
```python
{
    'id': 'google-sub-id',
    'username': 'Display Name',
    'email': 'user@gmail.com',
    'picture': 'https://...',
    'db_id': 'uuid-from-database',
    'provider': 'google'
}
```

---

## Security Considerations

### CSRF Protection

Both OAuth flows use a `state` parameter:
1. App generates random state before redirect
2. State is stored in session
3. On callback, state is verified against session
4. Mismatch = possible CSRF attack

### Token Storage

- **Lichess tokens** are stored in the session for potential API calls and logout
- **Google tokens** are not stored (only used once to fetch user info)

### Token Revocation

On logout:
- Lichess tokens are revoked via API call
- Google tokens are not revoked (not necessary for this app)

### Secure Cookies in Production

Always enable secure cookies in production:

```python
app.config['SESSION_COOKIE_SECURE'] = True  # Requires HTTPS
```

---

## Troubleshooting

### "Session expired or cookies blocked"

**Cause**: Session cookie wasn't set or was cleared

**Solutions**:
1. Enable cookies in browser
2. Clear cookies and try again
3. Check `SESSION_COOKIE_SAMESITE` is `'Lax'`
4. Try incognito/private window

### "Invalid state parameter"

**Cause**: State mismatch between request and session

**Solutions**:
1. Don't use back button during OAuth
2. Clear cookies and try again
3. Check for session timeout issues

### "redirect_uri_mismatch" (Google)

**Cause**: Redirect URI doesn't match Google Console config

**Solutions**:
1. Check exact URI in Google Console (including trailing slash)
2. Ensure `BASE_URL` matches
3. Wait a few minutes after changes (Google caches)

### "invalid_client" (Google)

**Cause**: Wrong client ID or secret

**Solutions**:
1. Verify credentials in `.env`
2. Check for extra whitespace
3. Regenerate secret if needed

### "Google login is not configured"

**Cause**: Missing Google credentials

**Solution**: Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env`

---

## Testing OAuth

### Manual Testing

1. Clear all cookies for localhost
2. Click login button
3. Authorize on provider
4. Verify redirect back to app
5. Check session is created
6. Test logout

### Automated Testing

See `tests/test_user_manager.py` for OAuth unit tests:

```python
def test_get_login_url(self):
    """Test that login URL contains required parameters."""
    verifier, challenge = self.user_manager.generate_pkce_pair()
    url = self.user_manager.get_login_url(challenge, 'state')
    
    assert 'client_id=' in url
    assert 'code_challenge=' in url
    assert 'state=' in url
```

### Mock OAuth for Development

If you want to test without real OAuth:

```python
# In test environment, bypass OAuth
@app.route('/dev-login')
def dev_login():
    session['user'] = {
        'id': 'dev-user',
        'username': 'Developer',
        'db_id': 'test-uuid',
        'provider': 'dev'
    }
    return redirect('/')
```

**Warning**: Never enable this in production!

