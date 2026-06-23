"""
Tests for the authentication layer:
- The user store (`backend.auth.users.authenticate`)
- JWT issue and verify (`backend.auth.jwt_handler`)
- The `/login` HTTP endpoint
"""

from backend.auth.jwt_handler import create_token, verify_token
from backend.auth.users import DEMO_USERS, authenticate


# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------


class TestAuthenticate:
    def test_valid_credentials_returns_user_dict(self):
        user = authenticate("dr.bijoy", "doctor123")
        assert user is not None
        assert user["username"] == "dr.bijoy"
        assert user["role"] == "doctor"
        assert user["display_name"] == "Dr. Bijoy"

    def test_invalid_password_returns_none(self):
        assert authenticate("dr.bijoy", "wrong-password") is None

    def test_unknown_user_returns_none(self):
        assert authenticate("not.a.user", "doctor123") is None

    def test_authenticate_does_not_leak_password_hash(self):
        user = authenticate("dr.bijoy", "doctor123")
        assert "password_hash" not in user

    def test_all_demo_users_authenticate(self):
        # If this fails, README demo credentials are out of sync with users.py.
        expected = {
            "dr.bijoy": ("doctor123", "doctor"),
            "nurse.priya": ("nurse123", "nurse"),
            "billing.niloy": ("billing123", "billing_executive"),
            "tech.fatima": ("tech123", "technician"),
            "admin.sys": ("admin123", "admin"),
        }
        assert set(DEMO_USERS) == set(expected)
        for username, (password, role) in expected.items():
            user = authenticate(username, password)
            assert user is not None, f"{username} failed to authenticate"
            assert user["role"] == role


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


class TestJWT:
    def test_create_and_verify_round_trip(self):
        token = create_token("dr.bijoy", "doctor")
        payload = verify_token(token)
        assert payload == {"username": "dr.bijoy", "role": "doctor"}

    def test_tampered_token_rejected(self):
        token = create_token("dr.bijoy", "doctor")
        # Flip a character in the signature segment.
        head, payload, signature = token.split(".")
        tampered_sig = (
            "A" + signature[1:] if signature[0] != "A" else "B" + signature[1:]
        )
        tampered = f"{head}.{payload}.{tampered_sig}"
        assert verify_token(tampered) is None

    def test_garbage_token_rejected(self):
        assert verify_token("not-a-token") is None
        assert verify_token("") is None

    def test_role_claim_survives_round_trip_for_each_role(self):
        # Hyphenated/underscored roles (billing_executive) are easy to mangle —
        # this guards against accidental coercion.
        for role in ["doctor", "nurse", "billing_executive", "technician", "admin"]:
            token = create_token("someone", role)
            assert verify_token(token)["role"] == role


# ---------------------------------------------------------------------------
# /login endpoint
# ---------------------------------------------------------------------------


class TestLoginEndpoint:
    def test_valid_login_returns_token_and_role(self, client):
        response = client.post(
            "/login",
            json={"username": "dr.bijoy", "password": "doctor123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "token" in body and body["token"]
        assert body["role"] == "doctor"
        assert body["username"] == "dr.bijoy"
        assert body["display_name"] == "Dr. Bijoy"

    def test_invalid_password_rejected(self, client):
        response = client.post(
            "/login",
            json={"username": "dr.bijoy", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_login_token_is_verifiable(self, client):
        response = client.post(
            "/login",
            json={"username": "nurse.priya", "password": "nurse123"},
        )
        token = response.json()["token"]
        payload = verify_token(token)
        assert payload["username"] == "nurse.priya"
        assert payload["role"] == "nurse"
