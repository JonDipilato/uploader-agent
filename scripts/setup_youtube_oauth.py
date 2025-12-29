"""
YouTube OAuth Setup Script
==========================
This script helps set up YouTube OAuth credentials for video uploads.
It supports multiple channels and secure credential management.

Usage:
    python scripts/setup_youtube_oauth.py [--channel-name NAME]

Requirements:
    1. Google Cloud Console project with YouTube Data API v3 enabled
    2. OAuth 2.0 credentials (Desktop application type)
"""
from __future__ import annotations

import json
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRETS_DIR = ROOT / "secrets"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def print_setup_guide():
    """Print step-by-step guide for creating OAuth credentials."""
    print("""
================================================================================
                    YouTube OAuth Setup Guide
================================================================================

STEP 1: Create a Google Cloud Project (if you don't have one)
------------------------------------------------------------
1. Go to: https://console.cloud.google.com/
2. Click "Select a project" > "New Project"
3. Name it (e.g., "Video Uploader") and create

STEP 2: Enable YouTube Data API v3
----------------------------------
1. Go to: https://console.cloud.google.com/apis/library
2. Search for "YouTube Data API v3"
3. Click on it and press "Enable"

STEP 3: Configure OAuth Consent Screen
--------------------------------------
1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Choose "External" user type (or Internal if using Google Workspace)
3. Fill in:
   - App name: "Video Uploader" (or your choice)
   - User support email: your email
   - Developer contact: your email
4. Click "Save and Continue"
5. Add scopes: click "Add or Remove Scopes"
   - Search for and add: ".../auth/youtube.upload"
   - Search for and add: ".../auth/youtube"
6. Save and continue through remaining steps

STEP 4: Create OAuth Credentials
--------------------------------
1. Go to: https://console.cloud.google.com/apis/credentials
2. Click "Create Credentials" > "OAuth client ID"
3. Application type: "Desktop app"
4. Name: "Video Uploader Desktop" (or your choice)
5. Click "Create"
6. Download the JSON file (click the download icon)
7. Save it as: secrets/youtube_client.json

STEP 5: Add Test Users (Required for External apps)
---------------------------------------------------
1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Scroll to "Test users" section
3. Click "Add Users"
4. Add email addresses of:
   - Your own Google account
   - Any friends who will use this app
5. Save changes

NOTE: Until you publish your app, only test users can authenticate.
For production with unlimited users, submit for verification.

================================================================================
""")


def prompt(text: str, default: str = "") -> str:
    """Prompt for user input with optional default."""
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value if value else default


def prompt_bool(text: str, default: bool = True) -> bool:
    """Prompt for yes/no input."""
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        value = input(f"{text}{suffix}: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Enter y or n.")


def find_client_json() -> Path | None:
    """Look for OAuth client JSON in common locations."""
    candidates = [
        SECRETS_DIR / "youtube_client.json",
        ROOT / "youtube_client.json",
        Path.home() / "Downloads" / "client_secret*.json",
    ]
    for candidate in candidates:
        if "*" in str(candidate):
            matches = list(candidate.parent.glob(candidate.name))
            if matches:
                return sorted(matches, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        elif candidate.exists():
            return candidate
    return None


def setup_credentials(channel_name: str = "") -> Path:
    """Interactive setup for YouTube OAuth credentials."""
    suffix = f"_{channel_name}" if channel_name else ""
    client_json_path = SECRETS_DIR / f"youtube_client{suffix}.json"
    token_json_path = SECRETS_DIR / f"youtube_token{suffix}.json"

    print(f"\n--- YouTube OAuth Setup{f' for {channel_name}' if channel_name else ''} ---\n")

    # Check for existing client JSON
    existing = find_client_json()
    if existing and existing != client_json_path:
        print(f"Found OAuth client JSON at: {existing}")
        if prompt_bool("Copy this to secrets folder?"):
            SECRETS_DIR.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(existing, client_json_path)
            print(f"Copied to: {client_json_path}")

    if not client_json_path.exists():
        print(f"\nOAuth client JSON not found at: {client_json_path}")
        print("Please download it from Google Cloud Console.")
        if prompt_bool("Open Google Cloud Console in browser?"):
            webbrowser.open("https://console.cloud.google.com/apis/credentials")

        path_input = prompt("Enter path to downloaded JSON (or press Enter to exit)")
        if not path_input:
            print("Setup cancelled.")
            sys.exit(1)

        src = Path(path_input).expanduser()
        if not src.exists():
            print(f"File not found: {src}")
            sys.exit(1)

        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(src, client_json_path)
        print(f"Copied to: {client_json_path}")

    # Verify the JSON structure
    try:
        with open(client_json_path) as f:
            data = json.load(f)
        if "installed" not in data and "web" not in data:
            print("Warning: This doesn't look like an OAuth client JSON.")
            print("Make sure you downloaded 'OAuth client ID' credentials, not a service account.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON file.")
        sys.exit(1)

    # Authenticate
    print("\n--- Authentication ---\n")
    print("Now we'll authenticate with your YouTube channel.")
    print("A browser window will open. Log in with your Google account and authorize access.")
    print()

    if prompt_bool("Ready to authenticate?"):
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow

            creds = None
            if token_json_path.exists():
                creds = Credentials.from_authorized_user_file(str(token_json_path), SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    print("Refreshing expired token...")
                    creds.refresh(Request())
                else:
                    print("Opening browser for authentication...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(client_json_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                token_json_path.write_text(creds.to_json(), encoding="utf-8")
                print(f"Token saved to: {token_json_path}")

            # Test the connection
            from googleapiclient.discovery import build
            youtube = build("youtube", "v3", credentials=creds)
            channels = youtube.channels().list(part="snippet", mine=True).execute()

            if channels.get("items"):
                channel = channels["items"][0]["snippet"]
                print(f"\nAuthenticated successfully!")
                print(f"Channel: {channel.get('title')}")
                print(f"ID: {channels['items'][0]['id']}")
            else:
                print("\nWarning: No channel found for this account.")
                print("Make sure you're logged into an account with a YouTube channel.")

        except ImportError:
            print("Error: Required packages not installed.")
            print("Run: pip install google-auth google-auth-oauthlib google-api-python-client")
            sys.exit(1)
        except Exception as e:
            print(f"Authentication error: {e}")
            sys.exit(1)

    return token_json_path


def list_configured_channels():
    """List all configured YouTube channels/tokens."""
    print("\n--- Configured YouTube Channels ---\n")

    tokens = list(SECRETS_DIR.glob("youtube_token*.json"))
    if not tokens:
        print("No tokens found. Run setup first.")
        return

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        for token_path in tokens:
            name = token_path.stem.replace("youtube_token_", "").replace("youtube_token", "default")
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
                youtube = build("youtube", "v3", credentials=creds)
                channels = youtube.channels().list(part="snippet", mine=True).execute()

                if channels.get("items"):
                    channel = channels["items"][0]["snippet"]
                    print(f"  [{name}] {channel.get('title')}")
                    print(f"           Token: {token_path.name}")
                else:
                    print(f"  [{name}] (no channel found)")
            except Exception as e:
                print(f"  [{name}] Error: {e}")

    except ImportError:
        for token_path in tokens:
            name = token_path.stem.replace("youtube_token_", "").replace("youtube_token", "default")
            print(f"  [{name}] {token_path.name}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="YouTube OAuth Setup")
    parser.add_argument("--channel-name", "-n", help="Name for this channel config (for multiple channels)")
    parser.add_argument("--list", "-l", action="store_true", help="List configured channels")
    parser.add_argument("--guide", "-g", action="store_true", help="Show setup guide only")
    args = parser.parse_args()

    if args.guide:
        print_setup_guide()
        return

    if args.list:
        list_configured_channels()
        return

    print_setup_guide()

    if not prompt_bool("\nHave you completed the steps above?", default=True):
        print("\nPlease complete the setup steps first, then run this script again.")
        return

    setup_credentials(args.channel_name or "")

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Update config.yaml with the credential paths:")
    print("   upload:")
    print("     credentials_json: secrets/youtube_client.json")
    print("     token_json: secrets/youtube_token.json")
    print("\n2. Run a test upload:")
    print("   python -m src.agent --config config.yaml --test --test-minutes 5")
    print()


if __name__ == "__main__":
    main()
