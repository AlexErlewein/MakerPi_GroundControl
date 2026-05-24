"""Tests for NFC card security: HMAC signature and Mifare sector key derivation."""

import os

# Set a test secret key before importing modules that read it at import time
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")


from backend.members.signature import (
    generate_card_signature,
    verify_card_signature,
    derive_mifare_sector_key,
)


class TestCardSignature:
    def test_generate_returns_64_char_hex(self):
        sig = generate_card_signature("M001", "04A3B5C2", "Alice Example")
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_verify_accepts_valid_signature(self):
        sig = generate_card_signature("M001", "04A3B5C2", "Alice Example")
        assert verify_card_signature("M001", "04A3B5C2", "Alice Example", sig)

    def test_verify_rejects_wrong_member_id(self):
        sig = generate_card_signature("M001", "04A3B5C2", "Alice Example")
        assert not verify_card_signature("M999", "04A3B5C2", "Alice Example", sig)

    def test_verify_rejects_wrong_uid(self):
        sig = generate_card_signature("M001", "04A3B5C2", "Alice Example")
        assert not verify_card_signature("M001", "DEADBEEF", "Alice Example", sig)

    def test_verify_rejects_wrong_name(self):
        sig = generate_card_signature("M001", "04A3B5C2", "Alice Example")
        assert not verify_card_signature("M001", "04A3B5C2", "Bob Imposter", sig)

    def test_verify_is_case_insensitive_for_uid(self):
        sig = generate_card_signature("M001", "04a3b5c2", "Alice Example")
        # UID normalised to upper in generate; verify should accept either case
        assert verify_card_signature("M001", "04A3B5C2", "Alice Example", sig)

    def test_verify_is_case_insensitive_for_signature(self):
        sig = generate_card_signature("M001", "04A3B5C2", "Alice Example")
        assert verify_card_signature("M001", "04A3B5C2", "Alice Example", sig.upper())

    def test_signature_differs_per_uid(self):
        sig1 = generate_card_signature("M001", "AABBCCDD", "Alice Example")
        sig2 = generate_card_signature("M001", "11223344", "Alice Example")
        assert sig1 != sig2

    def test_verify_rejects_empty_signature(self):
        assert not verify_card_signature("M001", "04A3B5C2", "Alice Example", "")

    def test_verify_rejects_forged_hex_string(self):
        assert not verify_card_signature("M001", "04A3B5C2", "Alice Example", "a" * 64)


class TestMifareSectorKey:
    def test_derive_returns_12_char_hex(self):
        key = derive_mifare_sector_key()
        assert len(key) == 12
        assert all(c in "0123456789abcdef" for c in key)

    def test_derive_is_deterministic(self):
        assert derive_mifare_sector_key() == derive_mifare_sector_key()

    def test_derive_differs_from_secret_key_bytes(self):
        # Key must not be a trivial slice of the secret key
        key = derive_mifare_sector_key()
        secret_bytes = os.environ["SECRET_KEY"].encode().hex()
        assert key not in secret_bytes

    def test_get_returns_derived_key_when_no_override(self):
        # MIFARE_SECTOR_KEY env var not set → should return derived key
        os.environ.pop("MIFARE_SECTOR_KEY", None)
        # Reload config so the empty value is picked up
        import importlib
        import backend.config as cfg

        importlib.reload(cfg)
        import backend.members.signature as sig_mod

        importlib.reload(sig_mod)
        key = sig_mod.get_mifare_sector_key()
        assert len(key) == 12

    def test_get_returns_override_when_set(self):
        custom = "a1b2c3d4e5f6"
        os.environ["MIFARE_SECTOR_KEY"] = custom
        import importlib
        import backend.config as cfg

        importlib.reload(cfg)
        import backend.members.signature as sig_mod

        importlib.reload(sig_mod)
        assert sig_mod.get_mifare_sector_key() == custom
        # Clean up
        del os.environ["MIFARE_SECTOR_KEY"]
        importlib.reload(cfg)
        importlib.reload(sig_mod)
