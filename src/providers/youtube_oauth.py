"""
YouTube OAuth Helper for Streamlit
===================================
Provides a simple "Login with Google" button for YouTube API access.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Google OAuth endpoints
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REFRESH_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# YouTube API scopes
YOUTUBE_SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube"


def get_oauth_credentials() -> tuple[str | None, str | None]:
    """
    Get OAuth credentials from environment or Streamlit secrets.

    Returns:
        Tuple of (client_id, client_secret) or (None, None) if not found.
    """
    # Try environment variables first
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if client_id and client_secret:
        return client_id, client_secret

    # Try Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            client_id = st.secrets.get("GOOGLE_CLIENT_ID")
            client_secret = st.secrets.get("GOOGLE_CLIENT_SECRET")
            if client_id and client_secret:
                return client_id, client_secret
    except Exception:
        pass

    # Try .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if client_id and client_secret:
            return client_id, client_secret
    except ImportError:
        pass

    return None, None


def credentials_configured() -> bool:
    """Check if OAuth credentials are configured."""
    client_id, client_secret = get_oauth_credentials()
    return bool(client_id and client_secret)


def get_channel_info(token: dict[str, Any]) -> dict[str, Any] | None:
    """
    Get YouTube channel info using the access token.

    Args:
        token: OAuth token dictionary with 'access_token' key.

    Returns:
        Channel info dict with 'title' and 'id' keys, or None on error.
    """
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            token_uri=GOOGLE_TOKEN_URL,
        )

        youtube = build("youtube", "v3", credentials=creds)
        response = youtube.channels().list(part="snippet", mine=True).execute()

        if response.get("items"):
            item = response["items"][0]
            return {
                "id": item["id"],
                "title": item["snippet"]["title"],
                "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
            }
    except Exception as e:
        print(f"Error getting channel info: {e}")

    return None


def save_token_to_file(token: dict[str, Any], path: Path) -> None:
    """Save OAuth token to a JSON file compatible with google-auth."""
    # Convert to google-auth format
    token_data = {
        "token": token.get("access_token"),
        "refresh_token": token.get("refresh_token"),
        "token_uri": GOOGLE_TOKEN_URL,
        "client_id": get_oauth_credentials()[0],
        "client_secret": get_oauth_credentials()[1],
        "scopes": YOUTUBE_SCOPES.split(),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")


def get_redirect_uri() -> str:
    """
    Auto-detect the correct redirect URI based on environment.

    Returns:
        The redirect URI to use for OAuth.
    """
    import streamlit as st

    # Check for custom redirect URI in secrets/env
    custom_uri = os.getenv("OAUTH_REDIRECT_URI")
    if custom_uri:
        return custom_uri

    try:
        if hasattr(st, "secrets") and "OAUTH_REDIRECT_URI" in st.secrets:
            return st.secrets["OAUTH_REDIRECT_URI"]
    except Exception:
        pass

    # Try to detect Streamlit Cloud
    # Streamlit Cloud sets specific environment variables
    if os.getenv("STREAMLIT_SHARING_MODE") or os.getenv("IS_STREAMLIT_CLOUD"):
        # Running on Streamlit Cloud - need the app URL from secrets
        try:
            if hasattr(st, "secrets") and "APP_URL" in st.secrets:
                return st.secrets["APP_URL"]
        except Exception:
            pass

    # Check if we have query params that indicate the host
    try:
        # In newer Streamlit versions
        query_params = st.query_params
        if query_params:
            # We're probably on a deployed instance
            pass
    except Exception:
        pass

    # Default to localhost for development
    return "http://localhost:8501"


def render_youtube_login(redirect_uri: str | None = None) -> dict[str, Any] | None:
    """
    Render the YouTube login button and handle OAuth flow.

    Args:
        redirect_uri: Optional override for redirect URI. Auto-detected if not provided.

    Returns:
        Token dict if authenticated, None otherwise.
    """
    import streamlit as st

    # Auto-detect redirect URI if not provided
    if redirect_uri is None:
        redirect_uri = get_redirect_uri()

    client_id, client_secret = get_oauth_credentials()

    if not client_id or not client_secret:
        st.warning("YouTube OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file.")
        with st.expander("Setup Instructions"):
            st.markdown("""
            1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
            2. Create OAuth 2.0 Client ID (Web application type)
            3. Add authorized redirect URI: `http://localhost:8501`
            4. Copy Client ID and Client Secret
            5. Create `.env` file with:
            ```
            GOOGLE_CLIENT_ID=your-client-id
            GOOGLE_CLIENT_SECRET=your-client-secret
            ```
            6. Restart the app
            """)
        return None

    try:
        from streamlit_oauth import OAuth2Component

        oauth2 = OAuth2Component(
            client_id=client_id,
            client_secret=client_secret,
            authorize_endpoint=GOOGLE_AUTHORIZE_URL,
            token_endpoint=GOOGLE_TOKEN_URL,
            refresh_token_endpoint=GOOGLE_REFRESH_URL,
            revoke_token_endpoint=GOOGLE_REVOKE_URL,
        )

        # Check for existing token in session
        if "youtube_token" in st.session_state and st.session_state.youtube_token:
            token = st.session_state.youtube_token
            channel = get_channel_info(token)

            if channel:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.success(f"Connected to: **{channel['title']}**")
                with col2:
                    if st.button("Logout", use_container_width=True):
                        st.session_state.youtube_token = None
                        st.rerun()
                return token
            else:
                # Token might be expired, clear it
                st.session_state.youtube_token = None

        # Show login button
        result = oauth2.authorize_button(
            name="Login with Google",
            redirect_uri=redirect_uri,
            scope=YOUTUBE_SCOPES,
            extras_params={"access_type": "offline", "prompt": "consent"},
            use_container_width=True,
            icon="https://www.google.com/favicon.ico",
        )

        if result and "token" in result:
            st.session_state.youtube_token = result["token"]
            st.rerun()

        return None

    except ImportError:
        st.error("streamlit-oauth not installed. Run: `pip install streamlit-oauth`")
        return None
    except Exception as e:
        st.error(f"OAuth error: {e}")
        return None
