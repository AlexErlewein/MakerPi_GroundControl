"""Email sending utilities using aiosmtplib with OAuth2 support for Gmail"""

import asyncio
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

# Global credentials cache for OAuth2
_oauth_credentials = None


async def get_oauth_token() -> str:
    """Get a valid OAuth2 access token for Gmail, refreshing if needed."""
    from backend.config import (
        GMAIL_OAUTH_ENABLED,
        GMAIL_OAUTH_TOKEN_FILE,
    )

    global _oauth_credentials

    if not GMAIL_OAUTH_ENABLED or not GMAIL_OAUTH_TOKEN_FILE:
        raise RuntimeError("Gmail OAuth2 not configured")

    token_path = Path(GMAIL_OAUTH_TOKEN_FILE)
    if not token_path.exists():
        logger.error(f"OAuth token file not found: {GMAIL_OAUTH_TOKEN_FILE}")
        raise RuntimeError("OAuth token file not found")

    # Load credentials from file
    with open(token_path) as f:
        token_data = json.load(f)

    # Import here to avoid issues when not using OAuth
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        logger.error("google-auth not installed for OAuth2 support")
        raise RuntimeError("google-auth package required for OAuth2")

    # Create credentials object
    credentials = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.send"]),
    )

    # Check if token needs refresh
    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            # Refresh token (sync operation, run in thread)
            try:
                await asyncio.to_thread(credentials.refresh, Request())

                # Update global cache
                _oauth_credentials = credentials

                # Update the token file with new access token
                token_data["token"] = credentials.token
                token_data["expiry"] = (
                    credentials.expiry.isoformat() if credentials.expiry else None
                )

                with open(token_path, "w") as f:
                    json.dump(token_data, f, indent=2)

                logger.info("Gmail OAuth2 token refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh OAuth2 token: {e}")
                raise RuntimeError(f"OAuth2 token refresh failed: {e}")
        else:
            logger.error("OAuth2 credentials invalid and no refresh token available")
            raise RuntimeError("OAuth2 credentials invalid")
    else:
        # Cache valid credentials
        _oauth_credentials = credentials

    return credentials.token


async def send_via_gmail_api(
    msg: MIMEMultipart, to: list[str], token_data: dict, token_file: str
) -> bool:
    """Send email via Gmail API (supports aliases properly)."""
    try:
        import base64

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        logger.error("Google API client libraries not installed")
        return False

    # Create credentials
    credentials = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
    )

    # Refresh token if needed
    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            await asyncio.to_thread(credentials.refresh, Request())

            # Update token file with new access token
            token_path = Path(token_file)
            token_data["token"] = credentials.token
            token_data["expiry"] = (
                credentials.expiry.isoformat() if credentials.expiry else None
            )
            with open(token_path, "w") as f:
                json.dump(token_data, f, indent=2)
            logger.debug("Gmail API token refreshed")

    try:
        # Build Gmail service
        service = await asyncio.to_thread(
            build, "gmail", "v1", credentials=credentials, cache_discovery=False
        )

        # Convert message to Gmail format
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        # Send message
        await asyncio.to_thread(
            service.users().messages().send(userId="me", body={"raw": raw}).execute
        )

        logger.info(
            "Email sent via Gmail API to %s: %s",
            ", ".join(to),
            msg.get("Subject"),
        )
        return True

    except Exception as e:
        logger.error(f"Gmail API send failed: {e}")
        return False


async def send_email(
    to: Union[str, list],
    subject: str,
    html_body: str,
    text_body: str = "",
) -> bool:
    """Send an HTML email via SMTP. Returns True on success, False on failure.

    Supports both traditional SMTP auth and Gmail OAuth2.

    OAuth2 is used when:
    - GMAIL_OAUTH_ENABLED is true
    - GMAIL_OAUTH_TOKEN_FILE points to a valid token file
    - SMTP_HOST is smtp.gmail.com

    Traditional auth is used when:
    - GMAIL_OAUTH_ENABLED is false or missing
    - SMTP_USERNAME and SMTP_PASSWORD are configured

    Silently skips if email is not configured so callers can fire-and-forget
    without guarding.
    """
    from backend.config import (
        GMAIL_OAUTH_ENABLED,
        GMAIL_OAUTH_TOKEN_FILE,
        GMAIL_OAUTH_USERNAME,
        SMTP_FROM_EMAIL,
        SMTP_HOST,
        SMTP_PASSWORD,
        SMTP_PORT,
        SMTP_STARTTLS,
        SMTP_TLS,
        SMTP_USERNAME,
    )

    if not SMTP_HOST or not SMTP_FROM_EMAIL:
        logger.debug(
            "Email not configured (SMTP_HOST/SMTP_FROM_EMAIL missing), skipping send"
        )
        return False

    if isinstance(to, str):
        to = [to]
    to = [addr.strip() for addr in to if addr and addr.strip()]
    if not to:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = ", ".join(to)

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        # OAuth2 authentication for Gmail - try Gmail API first (supports aliases)
        if GMAIL_OAUTH_ENABLED and SMTP_HOST == "smtp.gmail.com":
            # Load token data
            token_path = Path(GMAIL_OAUTH_TOKEN_FILE)
            if token_path.exists():
                with open(token_path) as f:
                    token_data = json.load(f)

                # Try Gmail API first (supports aliases properly)
                logger.debug("Attempting to send via Gmail API")
                if await send_via_gmail_api(
                    msg, to, token_data, GMAIL_OAUTH_TOKEN_FILE
                ):
                    return True

                # Fallback to SMTP XOAUTH2
                logger.debug("Gmail API failed, trying SMTP XOAUTH2")
                import aiosmtplib

                try:
                    await aiosmtplib.send(
                        msg,
                        hostname=SMTP_HOST,
                        port=SMTP_PORT,
                        use_tls=SMTP_TLS,
                        username=GMAIL_OAUTH_USERNAME or SMTP_FROM_EMAIL,
                        oauth_token_generator=get_oauth_token,
                        start_tls=SMTP_STARTTLS and not SMTP_TLS,
                    )
                    logger.debug(
                        "Authenticated and sent email with Gmail OAuth2/XOAUTH2"
                    )
                except Exception as e:
                    logger.error(f"OAuth2 authentication failed: {e}")
                    # Fallback to traditional auth if configured
                    if SMTP_USERNAME and SMTP_PASSWORD:
                        logger.debug("Falling back to traditional SMTP auth")
                        smtp = aiosmtplib.SMTP(
                            hostname=SMTP_HOST,
                            port=SMTP_PORT,
                            use_tls=SMTP_TLS,
                        )
                        await smtp.connect()
                        try:
                            if SMTP_STARTTLS and not SMTP_TLS:
                                await smtp.starttls()
                            await smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
                            await smtp.send_message(msg)
                        finally:
                            await smtp.quit()
                    else:
                        raise
            else:
                logger.error(f"OAuth token file not found: {GMAIL_OAUTH_TOKEN_FILE}")
                return False
        else:
            # Traditional SMTP authentication
            import aiosmtplib

            smtp = aiosmtplib.SMTP(
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                use_tls=SMTP_TLS,
            )
            await smtp.connect()
            try:
                if SMTP_STARTTLS and not SMTP_TLS:
                    await smtp.starttls()
                if SMTP_USERNAME:
                    await smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
                    logger.debug("Authenticated with traditional SMTP auth")
                else:
                    logger.debug("No SMTP authentication configured")
                await smtp.send_message(msg)
            finally:
                await smtp.quit()

        logger.info("Email sent to %s: %s", ", ".join(to), subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s: %s", ", ".join(to), subject)
        return False
