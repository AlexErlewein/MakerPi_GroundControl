"""Tests for the public member registration endpoints.

Covers GET /register (HTML page) and POST /api/register (JSON API).
Uses the `client` and `members_db` fixtures from conftest.py which wire up
an in-memory SQLite database and skip MQTT/APScheduler entirely.
"""
import pytest


VALID_PAYLOAD = {
    "salutation": "Frau",
    "first_name": "Anna",
    "family_name": "Muster",
    "email": "anna.muster@example.com",
    "date_of_birth": "1990-01-15",
    "mobile_phone": "+491234567890",
    "street": "Musterstraße 1",
    "zip_code": "83022",
    "city": "Rosenheim",
    "country": "Deutschland",
    "payment_amount": 30.0,
    "payment_interval_months": 1,
    "method_of_payment": 0,
    "privacy_accepted": True,
}


class TestRegistrationPage:
    def test_register_page_loads(self, client):
        """GET /register must return 200 and contain registration-related content."""
        resp = client.get("/register")
        assert resp.status_code == 200
        content = resp.text.lower()
        assert "register" in content or "mitglied" in content


class TestRegistrationAPI:
    def test_register_success(self, client, members_db):
        """Happy path: valid payload creates a local inactive member."""
        resp = client.post("/api/register", json=VALID_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

        from backend.members.models import Mitglied
        m = (
            members_db.query(Mitglied)
            .filter(Mitglied.email == "anna.muster@example.com")
            .first()
        )
        assert m is not None
        assert m.status == "inactive"
        assert m.name == "Anna Muster"

    def test_register_success_returns_message(self, client):
        """Response body must include a non-empty message string."""
        payload = {**VALID_PAYLOAD, "email": "msg.test@example.com"}
        resp = client.post("/api/register", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0

    def test_register_duplicate_email(self, client):
        """Second registration with the same email must return 409."""
        client.post("/api/register", json=VALID_PAYLOAD)
        resp = client.post("/api/register", json=VALID_PAYLOAD)
        assert resp.status_code == 409
        assert "registriert" in resp.json()["detail"].lower()

    def test_register_missing_first_name(self, client):
        """Blank first_name must be rejected with 400 or 422."""
        payload = {**VALID_PAYLOAD, "first_name": "", "email": "blank.first@example.com"}
        resp = client.post("/api/register", json=payload)
        assert resp.status_code in (400, 422)

    def test_register_missing_last_name(self, client):
        """Blank family_name must be rejected with 400 or 422."""
        payload = {**VALID_PAYLOAD, "family_name": "", "email": "blank.last@example.com"}
        resp = client.post("/api/register", json=payload)
        assert resp.status_code in (400, 422)

    def test_register_missing_email_field(self, client):
        """Omitting the email field entirely must return 422 (Pydantic validation)."""
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "email"}
        resp = client.post("/api/register", json=payload)
        assert resp.status_code == 422

    def test_register_privacy_not_accepted(self, client):
        """privacy_accepted=False must return 400 mentioning Datenschutz."""
        payload = {**VALID_PAYLOAD, "privacy_accepted": False, "email": "noprivacy@example.com"}
        resp = client.post("/api/register", json=payload)
        assert resp.status_code == 400
        assert "datenschutz" in resp.json()["detail"].lower()

    def test_register_creates_inactive_member(self, client, members_db):
        """Registered member must be stored with status='inactive'."""
        payload = {**VALID_PAYLOAD, "email": "inactive.check@example.com"}
        resp = client.post("/api/register", json=payload)
        assert resp.status_code == 200

        from backend.members.models import Mitglied
        m = (
            members_db.query(Mitglied)
            .filter(Mitglied.email == "inactive.check@example.com")
            .first()
        )
        assert m is not None
        assert m.status == "inactive"

    def test_register_member_id_assigned(self, client, members_db):
        """Every registration must produce a non-empty member_id."""
        payload = {**VALID_PAYLOAD, "email": "memberid.check@example.com"}
        client.post("/api/register", json=payload)

        from backend.members.models import Mitglied
        m = (
            members_db.query(Mitglied)
            .filter(Mitglied.email == "memberid.check@example.com")
            .first()
        )
        assert m is not None
        assert m.member_id
        assert len(m.member_id) > 0

    def test_register_no_api_key_creates_local_record_with_reg_prefix(
        self, client, members_db, monkeypatch
    ):
        """Without an API key the local record should have a REG- prefixed member_id."""
        import backend.config as config_module
        monkeypatch.setattr(config_module, "EASYVEREIN_API_KEY", "")

        payload = {**VALID_PAYLOAD, "email": "nokey@example.com"}
        resp = client.post("/api/register", json=payload)
        assert resp.status_code == 200

        from backend.members.models import Mitglied
        m = (
            members_db.query(Mitglied)
            .filter(Mitglied.email == "nokey@example.com")
            .first()
        )
        assert m is not None
        assert m.member_id.startswith("REG-")

    def test_register_easyverein_api_failure_still_creates_local(
        self, client, members_db, monkeypatch
    ):
        """If the easyVerein API call raises, a local record must still be saved."""
        import backend.config as config_module
        monkeypatch.setattr(config_module, "EASYVEREIN_API_KEY", "fake-key")
        monkeypatch.setattr(config_module, "EASYVEREIN_REGISTRATION_MOCK", False)

        import httpx
        import backend.members.easyverein as ev_module

        async def failing_create(data):
            raise httpx.HTTPStatusError(
                "API error",
                request=httpx.Request("POST", "https://example.com"),
                response=httpx.Response(500),
            )

        monkeypatch.setattr(ev_module, "create_member_application", failing_create)

        payload = {**VALID_PAYLOAD, "email": "failtest@example.com"}
        resp = client.post("/api/register", json=payload)
        assert resp.status_code == 200

        from backend.members.models import Mitglied
        m = (
            members_db.query(Mitglied)
            .filter(Mitglied.email == "failtest@example.com")
            .first()
        )
        assert m is not None
        assert m.member_id.startswith("REG-")

    def test_register_mock_mode_uses_mock_membership_number(
        self, client, members_db, monkeypatch
    ):
        """With EASYVEREIN_API_KEY set and mock mode on, membership_number comes from mock."""
        import backend.config as config_module
        monkeypatch.setattr(config_module, "EASYVEREIN_API_KEY", "mock-key")
        monkeypatch.setattr(config_module, "EASYVEREIN_REGISTRATION_MOCK", True)

        payload = {**VALID_PAYLOAD, "email": "mockmode@example.com"}
        resp = client.post("/api/register", json=payload)
        assert resp.status_code == 200

        from backend.members.models import Mitglied
        m = (
            members_db.query(Mitglied)
            .filter(Mitglied.email == "mockmode@example.com")
            .first()
        )
        assert m is not None
        # Mock returns a unique MOCK-{timestamp} membership number
        assert m.member_id is not None
        assert m.member_id.startswith("MOCK-")

    def test_register_stores_phone(self, client, members_db):
        """mobile_phone from the payload should be stored on the Mitglied record."""
        payload = {**VALID_PAYLOAD, "email": "phone.check@example.com"}
        client.post("/api/register", json=payload)

        from backend.members.models import Mitglied
        m = (
            members_db.query(Mitglied)
            .filter(Mitglied.email == "phone.check@example.com")
            .first()
        )
        assert m is not None
        assert m.phone == "+491234567890"

    def test_register_email_stored_lowercase(self, client, members_db):
        """Email addresses should be normalised to lowercase before storage."""
        payload = {**VALID_PAYLOAD, "email": "UPPER.CASE@Example.COM"}
        resp = client.post("/api/register", json=payload)
        assert resp.status_code == 200

        from backend.members.models import Mitglied
        m = (
            members_db.query(Mitglied)
            .filter(Mitglied.email == "upper.case@example.com")
            .first()
        )
        assert m is not None

    def test_register_duplicate_email_case_insensitive(self, client):
        """Duplicate check should be case-insensitive (email is lowercased on write)."""
        payload_lower = {**VALID_PAYLOAD, "email": "dup@example.com"}
        payload_upper = {**VALID_PAYLOAD, "email": "DUP@EXAMPLE.COM"}
        client.post("/api/register", json=payload_lower)
        resp = client.post("/api/register", json=payload_upper)
        # The second call should hit the 409 because the stored value is lowercased
        assert resp.status_code == 409
