"""Card signature generation for NFC card binding.

Provides HMAC-based signatures to bind a card's UID to a specific member,
preventing card cloning attacks where an attacker copies data to a different card.
"""

import hmac
import hashlib
from backend.config import SECRET_KEY


def generate_card_signature(member_id: str, uid: str, name: str) -> str:
    """Generate HMAC signature binding UID to member data.

    The signature is computed over member_id, uid, and name using the
    server's SECRET_KEY. This ensures that:
    1. The card was issued by this GroundControl instance
    2. The UID matches the member record
    3. Data on card hasn't been tampered with

    Args:
        member_id: External member ID (e.g., from easyVerein)
        uid: NFC card UID in hex format (e.g., "04A3B5C2")
        name: Member name

    Returns:
        Hex-encoded HMAC-SHA256 signature (64 characters)
    """
    # Normalize inputs
    uid_normalized = uid.upper().replace(":", "").replace("-", "")
    message = f"{member_id}:{uid_normalized}:{name}"

    signature = hmac.new(
        SECRET_KEY.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return signature


def verify_card_signature(member_id: str, uid: str, name: str, signature: str) -> bool:
    """Verify that a signature matches the expected value.

    Args:
        member_id: External member ID
        uid: NFC card UID in hex format
        name: Member name from card
        signature: Signature from card (hex string)

    Returns:
        True if signature is valid
    """
    expected = generate_card_signature(member_id, uid, name)
    return hmac.compare_digest(expected.lower(), signature.lower())
