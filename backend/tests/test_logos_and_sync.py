"""Tests for team logo endpoints + Bowlslink sync admin endpoints.

Safe for live-season data: operates on ONE team's logo (then restores via import-logos),
does NOT mutate matches, rounds, or tips.
"""
import io
import os
import struct
import uuid
import zlib

import pytest
import requests

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://footy-tips-2.preview.emergentagent.com").rstrip("/")


def make_png(size: int = 8) -> bytes:
    """Builds a tiny valid PNG in-memory (red square)."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = b""
    for _ in range(size):
        raw += b"\x00" + b"\xff\x00\x00" * size  # filter 0 + red pixels
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": "admin@tipping.com", "password": "Admin@123"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def user_token():
    email = f"TEST_logo_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE}/api/auth/register", json={"name": "TEST L", "email": email, "password": "pass1234"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="module")
def teams():
    r = requests.get(f"{BASE}/api/teams", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 16
    return data


# ---------------- Public logo GET ----------------
class TestLogoGet:
    def test_get_logo_returns_image(self, teams):
        with_logo = next((t for t in teams if t.get("logo_path")), None)
        assert with_logo, "expected at least one team with logo_path"
        r = requests.get(f"{BASE}/api/teams/{with_logo['id']}/logo", timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("image/")
        assert len(r.content) > 100

    def test_get_logo_is_public_no_auth(self, teams):
        # explicit no Authorization header
        with_logo = next(t for t in teams if t.get("logo_path"))
        r = requests.get(f"{BASE}/api/teams/{with_logo['id']}/logo", timeout=30)
        assert r.status_code == 200

    def test_get_logo_404_for_bogus_id(self):
        r = requests.get(f"{BASE}/api/teams/000000000000000000000000/logo", timeout=30)
        assert r.status_code == 404


# ---------------- Admin upload / delete ----------------
class TestLogoAdmin:
    def test_upload_requires_auth(self, teams):
        tid = teams[-1]["id"]
        png = make_png()
        r = requests.post(f"{BASE}/api/teams/{tid}/logo", files={"file": ("x.png", png, "image/png")}, timeout=30)
        assert r.status_code == 401

    def test_upload_requires_admin(self, teams, user_headers):
        tid = teams[-1]["id"]
        png = make_png()
        r = requests.post(f"{BASE}/api/teams/{tid}/logo", headers=user_headers,
                          files={"file": ("x.png", png, "image/png")}, timeout=30)
        assert r.status_code == 403

    def test_upload_rejects_non_image(self, teams, admin_headers):
        tid = teams[-1]["id"]
        r = requests.post(f"{BASE}/api/teams/{tid}/logo", headers=admin_headers,
                          files={"file": ("x.txt", b"hello", "text/plain")}, timeout=30)
        assert r.status_code == 400

    def test_upload_rejects_oversize(self, teams, admin_headers):
        tid = teams[-1]["id"]
        big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (3 * 1024 * 1024 + 10)
        r = requests.post(f"{BASE}/api/teams/{tid}/logo", headers=admin_headers,
                          files={"file": ("big.png", big, "image/png")}, timeout=60)
        assert r.status_code == 400

    def test_upload_delete_cycle_increments_version(self, teams, admin_headers):
        # Operate on the LAST team to minimise user-facing impact; restored via import-logos at end.
        tid = teams[-1]["id"]
        before = requests.get(f"{BASE}/api/teams", timeout=30).json()
        orig = next(t for t in before if t["id"] == tid)
        v0 = orig.get("logo_v", 0)

        # upload
        png = make_png()
        r = requests.post(f"{BASE}/api/teams/{tid}/logo", headers=admin_headers,
                          files={"file": ("logo.png", png, "image/png")}, timeout=60)
        assert r.status_code == 200, r.text
        up = r.json()
        assert up["logo_path"], up
        assert up["logo_v"] == v0 + 1
        assert "_id" not in up

        # delete
        r = requests.delete(f"{BASE}/api/teams/{tid}/logo", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        after = r.json()
        assert after["logo_path"] is None
        assert after["logo_v"] == v0 + 2

        # public GET now 404
        g = requests.get(f"{BASE}/api/teams/{tid}/logo", timeout=30)
        assert g.status_code == 404

    def test_delete_requires_admin(self, teams, user_headers):
        r = requests.delete(f"{BASE}/api/teams/{teams[-1]['id']}/logo", headers=user_headers, timeout=30)
        assert r.status_code == 403


# ---------------- Bowlslink sync admin endpoints ----------------
class TestSync:
    def test_sync_status_requires_admin(self, user_headers):
        r = requests.get(f"{BASE}/api/admin/sync-status", headers=user_headers, timeout=30)
        assert r.status_code == 403

    def test_sync_status_admin(self, admin_headers):
        r = requests.get(f"{BASE}/api/admin/sync-status", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, dict)

    def test_sync_results_requires_admin(self, user_headers):
        r = requests.post(f"{BASE}/api/admin/sync-results", headers=user_headers, timeout=60)
        assert r.status_code == 403

    def test_sync_results_admin_shape(self, admin_headers):
        r = requests.post(f"{BASE}/api/admin/sync-results", headers=admin_headers, timeout=90)
        # Bowlslink may be unreachable from preview env (502) - treat as skip
        if r.status_code == 502:
            pytest.skip(f"Bowlslink unreachable from preview: {r.text}")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("last_sync", "updated", "completed_found", "error"):
            assert k in d
        assert isinstance(d["updated"], int)
        assert isinstance(d["completed_found"], int)
        # No real matches should be completed yet in this live season
        assert d["updated"] == 0


# ---------------- Restore logos at module teardown ----------------
class TestRestore:
    def test_zz_restore_all_logos(self, admin_headers):
        """Runs last (alphabetically zz) to restore the deleted logo on the last team."""
        r = requests.post(f"{BASE}/api/admin/import-logos", headers=admin_headers, timeout=180)
        # If Bowlslink is unreachable the backend returns 502 - we still want to flag it loudly.
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["imported"] >= 1
        assert isinstance(d["failed"], list)

    def test_zzz_all_teams_have_logos_after_restore(self):
        teams = requests.get(f"{BASE}/api/teams", timeout=30).json()
        missing = [t["name"] for t in teams if not t.get("logo_path")]
        assert not missing, f"After restore, teams missing logo: {missing}"

    def test_zzzz_import_logos_requires_admin(self, user_headers):
        r = requests.post(f"{BASE}/api/admin/import-logos", headers=user_headers, timeout=30)
        assert r.status_code == 403
