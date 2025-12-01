"""
Entra ID Authentication Module for Streamlit

This module provides OAuth 2.0 Authorization Code Flow with PKCE
authentication for Streamlit applications using Azure Entra ID.
"""

import os
import secrets
import hashlib
import base64
import requests
from typing import Optional, Dict
from urllib.parse import urlencode, parse_qs, urlparse
from dotenv import load_dotenv

load_dotenv()


class EntraIDAuth:
    """Handles Entra ID authentication with OAuth 2.0 + PKCE"""
    
    def __init__(self, 
                 tenant_id: str = None,
                 client_id: str = None,
                 client_secret: str = None,
                 redirect_uri: str = None,
                 scopes: list = None):
        """
        Initialize Entra ID authentication
        
        Args:
            tenant_id: Azure AD Tenant ID (from env if not provided)
            client_id: Application (client) ID (from env if not provided)
            client_secret: Application client secret (from env if not provided)
            redirect_uri: OAuth redirect URI (defaults to http://localhost:8501)
            scopes: List of OAuth scopes (defaults to basic profile scopes)
        """
        self.tenant_id = tenant_id or os.getenv("ENTRA_TENANT_ID")
        self.client_id = client_id or os.getenv("ENTRA_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ENTRA_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("ENTRA_REDIRECT_URI", "http://localhost:8501")
        
        # Default scopes for basic user info (include offline_access for longer-lived sessions)
        default_scopes = [
            "openid",
            "profile",
            "email",
            "offline_access",
            "User.Read",
        ]
        # Optional custom API scope (e.g., api://<client-id>/user_impersonation)
        api_scope = os.getenv("ENTRA_API_SCOPE")
        if api_scope:
            default_scopes.append(api_scope)
        self.scopes = scopes or default_scopes
        
        if not self.tenant_id or not self.client_id:
            raise ValueError(
                "Missing ENTRA_TENANT_ID or ENTRA_CLIENT_ID. "
                "Set these in .env or pass them to __init__"
            )
        
        # OAuth endpoints
        self.authorize_endpoint = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        )
        self.token_endpoint = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        )
    
    @staticmethod
    def generate_random_string(length: int = 32) -> str:
        """Generate a random string for state and code_verifier"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_code_challenge(code_verifier: str) -> str:
        """Generate PKCE code challenge from verifier"""
        code_sha = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(code_sha).decode().rstrip('=')
        return code_challenge
    
    def get_authorization_url(self, state: str, code_challenge: str) -> str:
        """
        Generate the authorization URL for user login
        
        Args:
            state: Random state parameter for CSRF protection
            code_challenge: PKCE code challenge
            
        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "response_mode": "query",
            "scope": " ".join(self.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        
        return f"{self.authorize_endpoint}?{urlencode(params)}"
    
    def exchange_code_for_token(self, 
                                authorization_code: str, 
                                code_verifier: str) -> Optional[Dict]:
        """
        Exchange authorization code for access token
        
        Args:
            authorization_code: Code received from OAuth callback
            code_verifier: PKCE code verifier
            
        Returns:
            Token response dict with access_token, id_token, etc.
        """
        body = {
            "client_id": self.client_id,
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
            "scope": " ".join(self.scopes)
        }
        
        # Add client secret if configured (required for Web platform)
        if self.client_secret:
            body["client_secret"] = self.client_secret
        
        try:
            response = requests.post(
                self.token_endpoint,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Token exchange failed: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            return None
    
    @staticmethod
    def parse_jwt(token: str) -> Optional[Dict]:
        """
        Parse JWT token (without verification - for display only)
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload dict
        """
        try:
            # Split token into parts
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode payload (second part)
            payload = parts[1]
            # Add padding if needed (proper modulo handling)
            payload += '=' * (-len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            
            import json
            return json.loads(decoded)
            
        except Exception as e:
            print(f"JWT parsing error: {e}")
            return None
    
    def get_user_info(self, access_token: str) -> Optional[Dict]:
        """
        Get user information from Microsoft Graph API
        
        Args:
            access_token: Access token from OAuth flow
            
        Returns:
            User info dict with name, email, etc.
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get user info: {e}")
            return None


class StreamlitEntraIDAuth:
    """Streamlit-specific authentication helper"""
    
    def __init__(self, auth: EntraIDAuth):
        """
        Initialize Streamlit auth helper
        
        Args:
            auth: EntraIDAuth instance
        """
        self.auth = auth
    
    def initialize_auth_session(self, session_state):
        """
        Initialize Streamlit session state for authentication
        
        Args:
            session_state: Streamlit session_state object
        """
        if 'authenticated' not in session_state:
            session_state.authenticated = False
        if 'access_token' not in session_state:
            session_state.access_token = None
        if 'user_info' not in session_state:
            session_state.user_info = None
        # Note: auth_state and code_verifier are stored in browser localStorage
        # via query params to survive Streamlit reruns
    
    def start_login(self, session_state) -> str:
        """
        Start OAuth login flow
        
        Args:
            session_state: Streamlit session_state object
            
        Returns:
            Authorization URL to redirect to
        """
        import hashlib
        
        # Generate code verifier
        code_verifier = self.auth.generate_random_string(64)
        code_challenge = self.auth.generate_code_challenge(code_verifier)
        
        # Use a hash of code_verifier as state (deterministic, can be verified)
        # This way we can verify state by re-hashing the code_verifier
        state = hashlib.sha256(code_verifier.encode()).hexdigest()[:32]
        
        # Store code_verifier in a file or cookie-like mechanism
        # For simplicity, we'll encode it in the state itself (not ideal for production)
        # Better: use browser sessionStorage via JavaScript
        
        # Store in session (may be lost on rerun, so we also store in a temp file)
        session_state.code_verifier = code_verifier
        session_state.auth_state = state
        
        # Also persist to a temp file as backup (Streamlit session can be lost)
        self._save_auth_state(state, code_verifier)
        
        # Generate authorization URL
        return self.auth.get_authorization_url(state, code_challenge)
    
    def _save_auth_state(self, state: str, code_verifier: str):
        """Save auth state to temp file for persistence across Streamlit reruns"""
        import json
        import tempfile
        import os
        
        state_file = os.path.join(tempfile.gettempdir(), f"entra_auth_{state[:16]}.json")
        with open(state_file, 'w') as f:
            json.dump({"state": state, "code_verifier": code_verifier}, f)
    
    def _load_auth_state(self, state: str) -> str:
        """Load code_verifier from temp file"""
        import json
        import tempfile
        import os
        
        state_file = os.path.join(tempfile.gettempdir(), f"entra_auth_{state[:16]}.json")
        try:
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    if data.get("state") == state:
                        # Clean up after reading
                        os.remove(state_file)
                        return data.get("code_verifier")
        except Exception as e:
            print(f"Error loading auth state: {e}")
        return None
    
    def handle_callback(self, session_state, query_params: dict) -> bool:
        """
        Handle OAuth callback after user login
        
        Args:
            session_state: Streamlit session_state object
            query_params: Query parameters from URL (st.query_params dict)
            
        Returns:
            True if authentication successful, False otherwise
        """
        # Check for errors
        if 'error' in query_params:
            error = query_params['error']
            error_desc = query_params.get('error_description', 'Unknown error')
            print(f"❌ OAuth error: {error} - {error_desc}")
            return False
        
        # Get code and state (st.query_params returns strings directly, not lists)
        if 'code' not in query_params or 'state' not in query_params:
            return False
        
        code = query_params['code']
        state = query_params['state']
        
        # Try to get code_verifier from session first, then from temp file
        code_verifier = getattr(session_state, 'code_verifier', None)
        
        if not code_verifier:
            # Session was lost (Streamlit rerun), try to recover from temp file
            code_verifier = self._load_auth_state(state)
        
        if not code_verifier:
            print("❌ Could not recover code_verifier - authentication state lost")
            return False
        
        # Exchange code for token
        token_response = self.auth.exchange_code_for_token(
            code, 
            code_verifier
        )
        
        if not token_response:
            return False
        
        # Store tokens
        session_state.access_token = token_response.get('access_token')
        session_state.id_token = token_response.get('id_token')
        
        # Parse user info from ID token
        if session_state.id_token:
            id_payload = self.auth.parse_jwt(session_state.id_token)
            if id_payload:
                session_state.user_info = {
                    "name": id_payload.get("name", "User"),
                    "email": id_payload.get("preferred_username") or id_payload.get("email", ""),
                    "user_id": id_payload.get("oid", ""),  # Object ID from Azure AD
                    "tenant_id": id_payload.get("tid", "")
                }
        
        # Get extended user info from Graph API
        graph_info = self.auth.get_user_info(session_state.access_token)
        if graph_info:
            session_state.user_info.update({
                "display_name": graph_info.get("displayName", session_state.user_info.get("name")),
                "job_title": graph_info.get("jobTitle", ""),
                "department": graph_info.get("department", "")
            })
        
        session_state.authenticated = True
        
        # Clean up auth state
        session_state.auth_state = None
        session_state.code_verifier = None
        
        return True
    
    def logout(self, session_state):
        """
        Logout user and clear session
        
        Args:
            session_state: Streamlit session_state object
        """
        session_state.authenticated = False
        session_state.access_token = None
        session_state.user_info = None
        # Clear any stored verifier
        if hasattr(session_state, 'code_verifier'):
            session_state.code_verifier = None
        if hasattr(session_state, 'auth_state'):
            session_state.auth_state = None


# For CLI-based authentication (non-Streamlit)
class CLIEntraIDAuth:
    """CLI-based authentication using device code flow"""
    
    def __init__(self, auth: EntraIDAuth):
        """
        Initialize CLI auth helper
        
        Args:
            auth: EntraIDAuth instance
        """
        self.auth = auth
        self.device_code_endpoint = (
            f"https://login.microsoftonline.com/{auth.tenant_id}/oauth2/v2.0/devicecode"
        )
    
    def start_device_code_flow(self) -> Optional[Dict]:
        """
        Start device code authentication flow
        
        Returns:
            Dict with device_code, user_code, verification_uri, etc.
        """
        body = {
            "client_id": self.auth.client_id,
            "scope": " ".join(self.auth.scopes)
        }
        
        try:
            response = requests.post(
                self.device_code_endpoint,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Device code flow failed: {e}")
            return None
    
    def poll_for_token(self, device_code: str, interval: int = 5) -> Optional[Dict]:
        """
        Poll for access token after user enters device code
        
        Args:
            device_code: Device code from start_device_code_flow
            interval: Polling interval in seconds
            
        Returns:
            Token response dict
        """
        import time
        
        body = {
            "client_id": self.auth.client_id,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code
        }
        
        max_attempts = 60  # 5 minutes max
        for attempt in range(max_attempts):
            try:
                response = requests.post(
                    self.auth.token_endpoint,
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    return response.json()
                
                error_data = response.json()
                error = error_data.get("error", "")
                
                if error == "authorization_pending":
                    # User hasn't completed sign-in yet
                    time.sleep(interval)
                    continue
                elif error == "slow_down":
                    # Increase interval
                    time.sleep(interval + 5)
                    continue
                else:
                    # Other error
                    print(f"❌ Token polling failed: {error}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Token polling error: {e}")
                return None
        
        print("❌ Timeout waiting for user to sign in")
        return None
    
    def authenticate_interactive(self) -> Optional[Dict]:
        """
        Perform interactive CLI authentication
        
        Returns:
            Dict with access_token and user_info
        """
        print("\n" + "="*70)
        print("🔐 ENTRA ID AUTHENTICATION")
        print("="*70 + "\n")
        
        # Start device code flow
        device_info = self.start_device_code_flow()
        if not device_info:
            return None
        
        user_code = device_info.get("user_code")
        verification_uri = device_info.get("verification_uri")
        device_code = device_info.get("device_code")
        
        print(f"📝 Please visit: {verification_uri}")
        print(f"🔑 Enter code: {user_code}\n")
        print("⏳ Waiting for you to sign in...")
        
        # Poll for token
        token_response = self.poll_for_token(device_code)
        if not token_response:
            return None
        
        access_token = token_response.get("access_token")
        id_token = token_response.get("id_token")
        
        # Parse user info
        user_info = {}
        if id_token:
            id_payload = self.auth.parse_jwt(id_token)
            if id_payload:
                user_info = {
                    "name": id_payload.get("name", "User"),
                    "email": id_payload.get("preferred_username") or id_payload.get("email", ""),
                    "user_id": id_payload.get("oid", ""),
                    "tenant_id": id_payload.get("tid", "")
                }
        
        # Get extended info from Graph
        graph_info = self.auth.get_user_info(access_token)
        if graph_info:
            user_info.update({
                "display_name": graph_info.get("displayName", user_info.get("name")),
                "job_title": graph_info.get("jobTitle", ""),
                "department": graph_info.get("department", "")
            })
        
        print("\n✅ Authentication successful!")
        print(f"👤 Signed in as: {user_info.get('name', 'User')}")
        print(f"📧 Email: {user_info.get('email', 'N/A')}\n")
        
        return {
            "access_token": access_token,
            "user_info": user_info
        }


# Example usage
if __name__ == "__main__":
    # Test CLI authentication
    auth = EntraIDAuth()
    cli_auth = CLIEntraIDAuth(auth)
    
    result = cli_auth.authenticate_interactive()
    if result:
        print(f"Access Token (first 50 chars): {result['access_token'][:50]}...")
        print(f"User Info: {result['user_info']}")
