#!/usr/bin/env python3
"""Test script for Gmail OAuth2 email sending.

Usage:
    python scripts/test_gmail_oauth.py [recipient_email]

If no recipient is provided, it will send to your own OAuth account.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Test OAuth2 email sending."""
    recipient = sys.argv[1] if len(sys.argv) > 1 else None

    print("\n" + "=" * 70)
    print("GMAIL OAUTH2 EMAIL TEST")
    print("=" * 70)

    # Check OAuth token file exists
    token_path = Path("config/gmail_oauth_token.json")
    if not token_path.exists():
        print(f"\n❌ OAuth token file not found: {token_path}")
        print("\nPlease run the token generator first:")
        print("  python scripts/generate_gmail_oauth_token.py")
        return False

    # Load and display token info (without secrets)
    with open(token_path) as f:
        token_data = json.load(f)

    print("\n✓ OAuth token file found")
    print(f"  Client ID: {token_data.get('client_id', 'N/A')[:30]}...")
    print(f"  Scopes: {', '.join(token_data.get('scopes', []))}")
    print(f"  Expiry: {token_data.get('expiry', 'N/A')}")

    # Check config
    config_path = Path("config/config.json")
    if not config_path.exists():
        print(f"\n❌ Config file not found: {config_path}")
        print("\nPlease create config/config.json with OAuth2 settings")
        return False

    with open(config_path) as f:
        config = json.load(f)

    if not config.get("gmail_oauth_enabled"):
        print("\n❌ Gmail OAuth2 not enabled in config")
        print('Set "gmail_oauth_enabled": true in config/config.json')
        return False

    from_email = config.get("smtp_from_email")
    print(f"\n✓ From email: {from_email}")

    if not recipient:
        # Try to extract email from token or prompt user
        print("\nNo recipient specified.")
        recipient = input(
            "Enter recipient email (or press Enter to send to yourself): "
        ).strip()
        if not recipient:
            recipient = from_email

    print(f"\n✓ To: {recipient}")

    # Test email sending
    print("\nSending test email...")

    try:
        from backend.email_utils import send_email

        success = await send_email(
            to=[recipient],
            subject="Gmail OAuth2 Test - H3cke GroundControl",
            html_body="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">✓ Gmail OAuth2 Test Successful!</h2>
                <p>This email was sent from <strong>H3cke GroundControl</strong> using Gmail OAuth2 authentication.</p>
                <p style="background: #e8f4fd; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db;">
                    <strong>Configuration:</strong><br>
                    From: {from_email}<br>
                    To: {to_email}<br>
                    Auth: OAuth2/XOAUTH2
                </p>
                <p>If you received this email, your OAuth2 setup is working correctly!</p>
                <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 30px 0;">
                <p style="font-size: 12px; color: #7f8c8d;">
                    This is an automated test email from H3cke GroundControl.<br>
                    Sender: noreply@h3cke.de
                </p>
            </body>
            </html>
            """.format(from_email=from_email, to_email=recipient),
            text_body=f"""
Gmail OAuth2 Test Successful!

This email was sent from H3cke GroundControl using Gmail OAuth2 authentication.

Configuration:
- From: {from_email}
- To: {recipient}
- Auth: OAuth2/XOAUTH2

If you received this email, your OAuth2 setup is working correctly!
""",
        )

        if success:
            print("\n✅ Email sent successfully!")
            print(f"   Check {recipient}'s inbox (and spam folder)")
            return True
        else:
            print("\n❌ Email sending failed")
            print("   Check logs for detailed error information")
            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(1)
