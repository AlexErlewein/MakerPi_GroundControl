"""Email sending utilities using aiosmtplib"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Union

logger = logging.getLogger(__name__)


async def send_email(
    to: Union[str, list],
    subject: str,
    html_body: str,
    text_body: str = None,
) -> bool:
    """Send an HTML email via SMTP. Returns True on success, False on failure.

    Requires SMTP_HOST and SMTP_FROM_EMAIL to be configured; silently skips
    if they are missing so callers can fire-and-forget without guarding.
    """
    from backend.config import (
        SMTP_FROM_EMAIL,
        SMTP_HOST,
        SMTP_PASSWORD,
        SMTP_PORT,
        SMTP_STARTTLS,
        SMTP_TLS,
        SMTP_USERNAME,
    )

    if not SMTP_HOST or not SMTP_FROM_EMAIL:
        logger.debug("Email not configured (SMTP_HOST/SMTP_FROM_EMAIL missing), skipping send")
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
            await smtp.send_message(msg)
        finally:
            await smtp.quit()

        logger.info("Email sent to %s: %s", ", ".join(to), subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s: %s", ", ".join(to), subject)
        return False
