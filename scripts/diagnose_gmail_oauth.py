#!/usr/bin/env python3
"""Diagnose Gmail OAuth2 authentication issues"""

import asyncio
import json
from pathlib import Path


async def main():
    token_path = Path("config/gmail_oauth_token.json")
    config_path = Path("config/config.json")

    if not token_path.exists():
        print("❌ OAuth token file not found")
        return

    # Load token
    with open(token_path) as f:
        token_data = json.load(f)

    # Load config
    with open(config_path) as f:
        config = json.load(f)

    print("\n" + "=" * 70)
    print("GMAIL OAUTH2 DIAGNOSTIC")
    print("=" * 70)

    print("\n📋 Configuration:")
    print(f"  Gmail OAuth enabled: {config.get('gmail_oauth_enabled', False)}")
    print(f"  From email: {config.get('smtp_from_email', 'Not set')}")
    print(f"  OAuth username: {config.get('gmail_oauth_username', 'Not set')}")
    print(f"  SMTP host: {config.get('smtp_host', 'Not set')}")
    print(f"  SMTP port: {config.get('smtp_port', 'Not set')}")

    print("\n🔑 OAuth Token:")
    print(f"  Client ID: {token_data.get('client_id', 'N/A')[:30]}...")
    print(f"  Scopes: {', '.join(token_data.get('scopes', []))}")
    print(f"  Expiry: {token_data.get('expiry', 'Not set')}")

    print("\n⚠️  CRITICAL CHECK:")
    print("  The OAuth username MUST be your real Google account:")
    print("    ✅ CORRECT: alex@h3cke.de (your personal account)")
    print("    ❌ WRONG:   noreply@h3cke.de (this is just an alias)")
    print()
    print("  The 'From' email can be noreply@h3cke.de (as long as it's configured")
    print("  as an alias in Google Workspace), but OAuth authentication must use")
    print("  your real account.")

    print("\n🔧 Troubleshooting Steps:")
    print("  1. Go to https://myaccount.google.com/permissions")
    print("  2. Find 'H3cke GroundControl OAuth' and remove access")
    print("  3. Run: uv run scripts/generate_gmail_oauth_token.py")
    print("  4. When browser opens:")
    print("     - SIGN IN WITH: alex@h3cke.de ← IMPORTANT!")
    print("     - NOT: noreply@h3cke.de")
    print("  5. Grant permissions and paste the authorization code")

    print("\n📝 Additional Notes:")
    print("  - noreply@h3cke.de must be configured as an email alias for alex@h3cke.de")
    print(
        "  - In Google Workspace Admin: Directory > Users > Your account > Email aliases"
    )
    print("  - The From address can be different from OAuth account if alias exists")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
