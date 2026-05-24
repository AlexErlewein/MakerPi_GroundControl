#!/usr/bin/env python3
"""Generate OAuth2 credentials for Gmail OAuth2 authentication.

This script runs once to authorize the application and generate a refresh token.
The refresh token is stored in config/gmail_oauth_token.json for use by email_utils.py.

Usage:
    python scripts/generate_gmail_oauth_token.py

Requirements:
    1. Google Cloud Console project with Gmail API enabled
    2. OAuth client credentials in config/gmail_oauth_client_secrets.json
    3. Access to complete OAuth consent flow in a browser
"""

import json
import sys
import webbrowser
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from google_auth_oauthlib.flow import Flow
    from google.oauth2.credentials import Credentials
except ImportError:
    print("Error: Required packages not installed.")
    print("Run: pip install google-auth google-auth-oauthlib aiosmtplib")
    sys.exit(1)


CLIENT_SECRETS_PATH = Path("config/gmail_oauth_client_secrets.json")
TOKEN_OUTPUT_PATH = Path("config/gmail_oauth_token.json")
# Request all scopes that the app is authorized for to avoid scope mismatch errors
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file",
]
REDIRECT_URI = "http://localhost:8080"


def load_client_secrets() -> dict:
    """Load OAuth client secrets from file."""
    if not CLIENT_SECRETS_PATH.exists():
        print(f"Error: Client secrets file not found: {CLIENT_SECRETS_PATH}")
        print("\nPlease create this file with your Google OAuth client credentials:")
        print(
            json.dumps(
                {
                    "web": {
                        "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
                        "client_secret": "YOUR_CLIENT_SECRET",
                        "redirect_uris": ["http://localhost:8080"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                indent=2,
            )
        )
        sys.exit(1)

    with open(CLIENT_SECRETS_PATH) as f:
        return json.load(f)


def generate_token() -> Credentials:
    """Run OAuth flow and return credentials."""
    client_config = load_client_secrets()

    # Create flow with client secrets
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    # Generate authorization URL
    auth_url, state = flow.authorization_url(
        access_type="offline",  # Critical: enables refresh token
        prompt="consent",  # Force consent to ensure we get refresh token
        include_granted_scopes="true",
    )

    print("\n" + "=" * 70)
    print("GMAIL OAUTH2 AUTHORIZATION")
    print("=" * 70)
    print("\n1. A browser window will open with Google's OAuth consent screen.")
    print("2. Sign in with the Google account that will send emails.")
    print("3. Grant permission to send email on your behalf.")
    print("4. You will be redirected to localhost with an authorization code.")
    print("5. Paste that code (everything after 'code=') below.")
    print("\n" + "=" * 70)

    # Open browser
    print(f"\nOpening browser: {auth_url}")
    if not webbrowser.open(auth_url):
        print("Could not open browser automatically. Please visit:")
        print(auth_url)
        print("\nPress Enter once you've authorized...")
        input()

    # Get authorization code from user
    print("\nPaste the authorization code from the redirect URL:")
    print("(Look for '?code=' in the URL and paste everything after)")
    code = input("Code: ").strip()

    if not code:
        print("Error: No authorization code provided.")
        sys.exit(1)

    # Exchange code for tokens
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        print(f"Error exchanging code for tokens: {e}")
        sys.exit(1)

    credentials = flow.credentials

    if not credentials.refresh_token:
        print("Error: No refresh token received.")
        print("This usually means the user already authorized the app.")
        print("Please revoke the existing authorization and try again:")
        print("https://myaccount.google.com/permissions")
        sys.exit(1)

    return credentials


def save_token(credentials: Credentials) -> None:
    """Save credentials to JSON file."""
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
    }

    TOKEN_OUTPUT_PATH.parent.mkdir(exist_ok=True, parents=True)

    with open(TOKEN_OUTPUT_PATH, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\n✓ OAuth token saved to: {TOKEN_OUTPUT_PATH}")
    print("\nIMPORTANT:")
    print("- Add this file to .gitignore")
    print("- Keep the refresh_token secret")
    print("- The access_token will be refreshed automatically")
    print("- If refresh_token is lost, you must re-run this script")


def main():
    """Main entry point."""
    print("\nGmail OAuth2 Token Generator")
    print("=" * 70)

    if TOKEN_OUTPUT_PATH.exists():
        print(f"\nWarning: Token file already exists: {TOKEN_OUTPUT_PATH}")
        print("Overwrite? (y/N): ", end="")
        if input().strip().lower() != "y":
            print("Cancelled.")
            sys.exit(0)

    credentials = generate_token()
    save_token(credentials)

    print("\n✓ OAuth2 credentials generated successfully!")
    print("\nNext steps:")
    print("1. Add OAuth2 settings to config/config.json:")
    print('   "gmail_oauth_enabled": true,')
    print('   "gmail_oauth_token_file": "config/gmail_oauth_token.json",')
    print('   "smtp_from_email": "noreply@h3cke.de"')
    print("\n2. Test email sending with the existing code")


if __name__ == "__main__":
    main()
