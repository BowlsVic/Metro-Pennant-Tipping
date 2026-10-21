"""Auth tests for the social sign-in additions (Emergent Google session + Apple)
and regression on existing email/password + JWT /auth/me flow.
Safe for live season: performs no mutations to teams/matches/tips/rounds.
Any ephemeral test player is cleaned up via DELETE /api/admin/players/{id}.
"""
import uuid


# ---------------- POST /api/auth/session (Google via Emergent) ----------------
class TestGoogleSession:
    def test_missing_body_returns_422(self, api, base_url):
        r = api.post(f"{base_url}/api/auth/session", json={})
        assert r.status_code == 422, r.text

    def test_invalid_session_id_returns_401(self, api, base_url):
        r = api.post(f"{base_url}/api/auth/session", json={"session_id": "invalid123"})
        assert r.status_code == 401, r.text
        detail = r.json().get("detail", "")
        assert "google" in detail.lower() or "sign-in" in detail.lower() or "expired" in detail.lower(), detail

    def test_garbage_session_id_returns_401(self, api, base_url):
        r = api.post(f"{base_url}/api/auth/session",
                     json={"session_id": f"garbage-{uuid.uuid4().hex}"})
        assert r.status_code == 401


# ---------------- POST /api/auth/apple ----------------
class TestAppleSignIn:
    def test_missing_body_returns_422(self, api, base_url):
        r = api.post(f"{base_url}/api/auth/apple", json={})
        assert r.status_code == 422

    def test_invalid_identity_token_returns_401(self, api, base_url):
        r = api.post(f"{base_url}/api/auth/apple", json={"identity_token": "not-a-jwt"})
        assert r.status_code == 401
        assert "apple" in r.json().get("detail", "").lower()

    def test_random_jwt_shaped_token_returns_401(self, api, base_url):
        # three dot-separated base64-ish segments – structurally JWT-ish but invalid sig / issuer.
        bogus = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJib2d1cyJ9.AAAA"
        r = api.post(f"{base_url}/api/auth/apple", json={"identity_token": bogus})
        assert r.status_code == 401


# ---------------- Regression: email/password + /auth/me ----------------
class TestEmailPasswordRegression:
    def test_admin_login_and_me(self, api, base_url):
        r = api.post(f"{base_url}/api/auth/login",
                     json={"email": "admin@tipping.com", "password": "Admin@123"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "token" in data and data["token"]
        assert data["user"]["email"] == "admin@tipping.com"
        assert data["user"]["role"] == "admin"
        assert "_id" not in data["user"]

        me = api.get(f"{base_url}/api/auth/me",
                     headers={"Authorization": f"Bearer {data['token']}"})
        assert me.status_code == 200
        body = me.json()
        assert body["email"] == "admin@tipping.com"
        assert body["role"] == "admin"
        assert "_id" not in body

    def test_login_wrong_password_401(self, api, base_url):
        r = api.post(f"{base_url}/api/auth/login",
                     json={"email": "admin@tipping.com", "password": "wrong-pass"})
        assert r.status_code == 401

    def test_me_without_token_401(self, api, base_url):
        r = api.get(f"{base_url}/api/auth/me")
        assert r.status_code == 401

    def test_register_login_me_cleanup(self, api, base_url):
        """Register a disposable player, confirm login + /me, then delete via admin."""
        email = f"TEST_social_{uuid.uuid4().hex[:8]}@example.com"
        reg = api.post(f"{base_url}/api/auth/register",
                       json={"name": "TEST Social", "email": email, "password": "pass1234"})
        assert reg.status_code == 200, reg.text
        rbody = reg.json()
        user_id = rbody["user"]["id"]
        assert rbody["user"]["email"] == email.lower()

        # login path
        lg = api.post(f"{base_url}/api/auth/login",
                      json={"email": email, "password": "pass1234"})
        assert lg.status_code == 200
        token = lg.json()["token"]

        me = api.get(f"{base_url}/api/auth/me",
                     headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == email.lower()

        # cleanup – admin delete
        admin = api.post(f"{base_url}/api/auth/login",
                         json={"email": "admin@tipping.com", "password": "Admin@123"}).json()["token"]
        d = api.delete(f"{base_url}/api/admin/players/{user_id}",
                       headers={"Authorization": f"Bearer {admin}"})
        assert d.status_code in (200, 204), d.text
