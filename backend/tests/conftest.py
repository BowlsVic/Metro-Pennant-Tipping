import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://footy-tips-2.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@tipping.com", "password": "Admin@123"})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def user_token(api):
    import uuid
    email = f"TEST_player_{uuid.uuid4().hex[:8]}@example.com"
    r = api.post(f"{BASE_URL}/api/auth/register", json={"name": "TEST Player", "email": email, "password": "pass1234"})
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    return r.json()["token"], email


@pytest.fixture(scope="session")
def user_headers(user_token):
    tok, _ = user_token
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
