import os
import requests
from flask import Flask, request, redirect, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for callback handling

# Secure secret key for sessions
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

# Discord OAuth Configuration
CLIENT_ID = os.getenv('DISCORD_CLIENT_ID', 'YOURCLIENTID')
CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET', 'YOURBOTOAUTHSECRET')
REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:3000/callback')

# Discord API endpoints
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_USER_INFO_URL = "https://discord.com/api/v10/users/@me"

@app.route('/')
def index():
    """
    Landing page with login option
    """
    return """
    <h1>Discord OAuth2 Login</h1>
    <a href="/login">Login with Discord</a>
    """

@app.route('/login')
def login():
    """
    Initiate Discord OAuth flow
    """
    # Construct authorization URL with appropriate scopes
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify email guilds.join',  # Request minimal necessary scopes
        'prompt': 'consent'
    }
    
    # URL encode parameters
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    auth_url = f"{DISCORD_OAUTH_URL}?{query_string}"
    
    return redirect(auth_url)

@app.route('/callback')
def oauth2_callback():
    """
    Handle OAuth callback and token exchange
    """
    # Get authorization code from request
    code = request.args.get('code')
    if not code:
        return jsonify({
            'error': 'No authorization code received',
            'description': 'Authorization failed'
        }), 400

    # Prepare token exchange data
    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'identify email guilds.join'
    }

    # Exchange code for access token
    try:
        token_response = requests.post(
            DISCORD_TOKEN_URL, 
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        token_response.raise_for_status()  # Raise exception for bad responses
        
        access_token_data = token_response.json()
        access_token = access_token_data.get('access_token')
        
        if not access_token:
            return jsonify({
                'error': 'Token exchange failed',
                'description': 'No access token received'
            }), 400

        # Fetch user information
        user_response = requests.get(
            DISCORD_USER_INFO_URL,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        user_response.raise_for_status()
        
        user_info = user_response.json()

        # Store user info in session (optional)
        session['user'] = {
            'id': user_info.get('id'),
            'username': user_info.get('username'),
            'email': user_info.get('email')
        }

        # Return user information
        return jsonify({
            'user_id': user_info.get('id'),
            'username': user_info.get('username'),
            'email': user_info.get('email'),
            'access_token': access_token
        })

    except requests.RequestException as e:
        # Comprehensive error handling
        return jsonify({
            'error': 'Request failed',
            'description': str(e)
        }), 500

@app.route('/logout')
def logout():
    """
    Clear user session
    """
    session.pop('user', None)
    return redirect('/')

if __name__ == '__main__':
    # Ensure environment variables are set or use defaults
    os.environ.setdefault('FLASK_ENV', 'development')
    
    # Run the application
    app.run(debug=True, port=3000)