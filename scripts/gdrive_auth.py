#!/usr/bin/env python3
"""One-time Google Drive OAuth2 authorisation.

Run this script once on a machine with a browser to create the token file:

    uv run python scripts/gdrive_auth.py

It reads config/gdrive_client_secrets.json (download from Google Cloud Console
→ APIs & Services → Credentials → your OAuth 2.0 Client ID → Download JSON).

On success it writes config/gdrive_token.json, which the app uses for all
subsequent Drive API calls without any further browser interaction.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import GOOGLE_DRIVE_CLIENT_SECRETS_FILE, GOOGLE_DRIVE_TOKEN_FILE  # noqa: E402

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main() -> None:
    secrets_path = Path(GOOGLE_DRIVE_CLIENT_SECRETS_FILE)
    token_path = Path(GOOGLE_DRIVE_TOKEN_FILE)

    if not secrets_path.exists():
        print(f"ERROR: client secrets file not found: {secrets_path}")
        print()
        print("Steps to create it:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Create a project (or select an existing one)")
        print("  3. Enable the Google Drive API")
        print("  4. Go to APIs & Services → Credentials")
        print("  5. Create an OAuth 2.0 Client ID (type: Desktop app)")
        print("  6. Download the JSON and save it as:", secrets_path)
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
    creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    print(f"Token saved to {token_path}")
    print("Google Drive authorisation complete.")


if __name__ == "__main__":
    main()
