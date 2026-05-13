"""Card signature generation and sector key derivation for NFC card security.

Provides HMAC-based signatures to bind a card's UID to a specific member,
preventing card cloning attacks where an attacker copies data to a different card.
Also derives the Mifare Classic sector key used to protect the signed sector.
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

    Accepts both full (64-char) and truncated (48-char) signatures — cards store
    only the first 48 chars due to NTAG/MIFARE block size constraints.

    Args:
        member_id: External member ID
        uid: NFC card UID in hex format
        name: Member name from card
        signature: Signature from card (hex string, 48 or 64 chars)

    Returns:
        True if signature is valid
    """
    if not signature or len(signature) < 16:
        return False
    expected = generate_card_signature(member_id, uid, name)
    sig_len = len(signature)
    return hmac.compare_digest(expected[:sig_len].lower(), signature.lower())


def derive_mifare_sector_key() -> str:
    """Derive a 6-byte Mifare Classic sector key as a hex string from SECRET_KEY.

    The key is deterministic: same SECRET_KEY always yields the same sector key,
    so any Pi running the same installation can authenticate to enrolled cards.
    Returns a 12-character hex string (e.g. "a1b2c3d4e5f6").
    """
    key_bytes = hmac.new(
        SECRET_KEY.encode("utf-8"), b"mifare-sector-key-v1", hashlib.sha256
    ).digest()
    return key_bytes[:6].hex()


def get_mifare_sector_key() -> str:
    """Return the active Mifare sector key.

    Uses MIFARE_SECTOR_KEY from config if explicitly set, otherwise derives it
    from SECRET_KEY. This allows manual override while defaulting to automatic
    derivation tied to the installation secret.
    """
    from backend.config import MIFARE_SECTOR_KEY

    return MIFARE_SECTOR_KEY if MIFARE_SECTOR_KEY else derive_mifare_sector_key()
