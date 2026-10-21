"""Tests for kick-off auto-lock + /rounds/{n}/all-tips (Everyone's tips)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


@pytest.fixture
def fresh_user(api, base_url):
    """Fresh registered user."""
    email = f"TEST_kt_{uuid.uuid4().hex[:8]}@example.com"
    r = api.post(f"{base_url}/api/auth/register",
                 json={"name": f"TEST KT {uuid.uuid4().hex[:4]}", "email": email, "password": "pass1234"})
    assert r.status_code == 200
    tok = r.json()["token"]
    return {"id": r.json()["user"]["id"], "email": email, "name": r.json()["user"]["name"],
            "headers": {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}}


class TestKickoffUpdate:
    """PUT /api/matches/{id} kickoff admin behavior."""

    def test_admin_set_and_clear_kickoff(self, api, base_url, admin_headers):
        matches = api.get(f"{base_url}/api/rounds/13", headers=admin_headers).json()["matches"]
        mid = matches[0]["id"]
        original = matches[0]["kickoff"]
        future = _iso(datetime.now(timezone.utc) + timedelta(days=30))
        r = api.put(f"{base_url}/api/matches/{mid}", headers=admin_headers, json={"kickoff": future})
        assert r.status_code == 200
        assert r.json()["kickoff"].startswith(future[:19])
        # clear
        r = api.put(f"{base_url}/api/matches/{mid}", headers=admin_headers, json={"clear_kickoff": True})
        assert r.status_code == 200
        assert r.json()["kickoff"] is None
        # restore
        if original:
            api.put(f"{base_url}/api/matches/{mid}", headers=admin_headers, json={"kickoff": original})

    def test_invalid_kickoff_rejected(self, api, base_url, admin_headers):
        matches = api.get(f"{base_url}/api/rounds/13", headers=admin_headers).json()["matches"]
        r = api.put(f"{base_url}/api/matches/{matches[0]['id']}", headers=admin_headers,
                    json={"kickoff": "not-a-date"})
        assert r.status_code == 400

    def test_non_admin_cannot_set_kickoff(self, api, base_url, user_headers):
        matches = api.get(f"{base_url}/api/rounds/13", headers=user_headers).json()["matches"]
        future = _iso(datetime.now(timezone.utc) + timedelta(days=5))
        r = api.put(f"{base_url}/api/matches/{matches[0]['id']}", headers=user_headers, json={"kickoff": future})
        assert r.status_code == 403


class TestLockedAndStartedFlags:
    """GET /rounds/{n} - locked = round_locked OR winner OR kickoff<=now; started flag per match."""

    def test_future_kickoff_not_locked_not_started(self, api, base_url, admin_headers, user_headers):
        matches = api.get(f"{base_url}/api/rounds/13", headers=admin_headers).json()["matches"]
        mid = matches[0]["id"]
        original = matches[0]["kickoff"]
        future = _iso(datetime.now(timezone.utc) + timedelta(days=30))
        api.put(f"{base_url}/api/matches/{mid}", headers=admin_headers, json={"kickoff": future})
        try:
            data = api.get(f"{base_url}/api/rounds/13", headers=user_headers).json()
            m = next(x for x in data["matches"] if x["id"] == mid)
            assert m["locked"] is False
            assert m["started"] is False
        finally:
            if original:
                api.put(f"{base_url}/api/matches/{mid}", headers=admin_headers, json={"kickoff": original})

    def test_past_kickoff_locked_and_started(self, api, base_url, admin_headers, user_headers):
        matches = api.get(f"{base_url}/api/rounds/13", headers=admin_headers).json()["matches"]
        mid = matches[0]["id"]
        original = matches[0]["kickoff"]
        past = _iso(datetime.now(timezone.utc) - timedelta(hours=1))
        api.put(f"{base_url}/api/matches/{mid}", headers=admin_headers, json={"kickoff": past})
        try:
            data = api.get(f"{base_url}/api/rounds/13", headers=user_headers).json()
            m = next(x for x in data["matches"] if x["id"] == mid)
            assert m["locked"] is True
            assert m["started"] is True
        finally:
            if original:
                api.put(f"{base_url}/api/matches/{mid}", headers=admin_headers, json={"kickoff": original})

    def test_submit_tips_skips_started_matches(self, api, base_url, admin_headers, fresh_user):
        """Started match tips are skipped, future ones saved."""
        matches = api.get(f"{base_url}/api/rounds/13", headers=admin_headers).json()["matches"]
        orig = {m["id"]: m["kickoff"] for m in matches}
        past = _iso(datetime.now(timezone.utc) - timedelta(hours=1))
        future = _iso(datetime.now(timezone.utc) + timedelta(days=60))
        # match[0] -> past (should skip); match[1] -> future (should save)
        api.put(f"{base_url}/api/matches/{matches[0]['id']}", headers=admin_headers, json={"kickoff": past})
        api.put(f"{base_url}/api/matches/{matches[1]['id']}", headers=admin_headers, json={"kickoff": future})
        try:
            tips = [
                {"match_id": matches[0]["id"], "team_id": matches[0]["home_team_id"]},
                {"match_id": matches[1]["id"], "team_id": matches[1]["home_team_id"]},
            ]
            r = api.post(f"{base_url}/api/rounds/13/tips", headers=fresh_user["headers"], json={"tips": tips})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body == {"saved": 1, "skipped": 1}, body
            # verify my_tip saved only for the future match
            data = api.get(f"{base_url}/api/rounds/13", headers=fresh_user["headers"]).json()
            tips_map = {m["id"]: m["my_tip"] for m in data["matches"]}
            assert tips_map[matches[0]["id"]] is None
            assert tips_map[matches[1]["id"]] == matches[1]["home_team_id"]
        finally:
            for mid, k in orig.items():
                if k:
                    api.put(f"{base_url}/api/matches/{mid}", headers=admin_headers, json={"kickoff": k})


class TestRoundsRevealedCount:
    def test_rounds_summary_has_revealed_count(self, api, base_url, user_headers):
        rounds = api.get(f"{base_url}/api/rounds", headers=user_headers).json()
        assert all("revealed_count" in r for r in rounds)
        assert all(isinstance(r["revealed_count"], int) for r in rounds)


class TestAllTips:
    """GET /api/rounds/{n}/all-tips - reveal gating, counts, admin exclusion."""

    def test_requires_auth(self, api, base_url):
        r = api.get(f"{base_url}/api/rounds/13/all-tips")
        assert r.status_code == 401

    def test_unrevealed_matches_have_zero_counts_and_no_leak(self, api, base_url, admin_headers, fresh_user):
        """Future-kickoff matches: revealed=false; player tips must NOT include them."""
        matches = api.get(f"{base_url}/api/rounds/13", headers=admin_headers).json()["matches"]
        orig = {m["id"]: m["kickoff"] for m in matches}
        # Make ALL matches future (unrevealed)
        future = _iso(datetime.now(timezone.utc) + timedelta(days=60))
        for m in matches:
            api.put(f"{base_url}/api/matches/{m['id']}", headers=admin_headers, json={"kickoff": future})
        try:
            # Player tips all four
            tips = [{"match_id": m["id"], "team_id": m["home_team_id"]} for m in matches]
            r = api.post(f"{base_url}/api/rounds/13/tips", headers=fresh_user["headers"], json={"tips": tips})
            assert r.status_code == 200
            assert r.json()["saved"] == 4

            data = api.get(f"{base_url}/api/rounds/13/all-tips", headers=fresh_user["headers"]).json()
            for m in data["matches"]:
                assert m["revealed"] is False
                assert m["home_count"] == 0
                assert m["away_count"] == 0
            me = next((p for p in data["players"] if p["user_id"] == fresh_user["id"]), None)
            assert me is not None
            # NO tips should leak for unrevealed matches
            assert me["tips"] == {}, f"Leaked tips: {me['tips']}"
            assert me["correct"] == 0
        finally:
            for mid, k in orig.items():
                if k:
                    api.put(f"{base_url}/api/matches/{mid}", headers=admin_headers, json={"kickoff": k})

    def test_revealed_match_counts_and_tips(self, api, base_url, admin_headers, fresh_user):
        """One match past kickoff -> revealed=true with counts; other three stay hidden."""
        matches = api.get(f"{base_url}/api/rounds/13", headers=admin_headers).json()["matches"]
        orig = {m["id"]: m["kickoff"] for m in matches}
        future = _iso(datetime.now(timezone.utc) + timedelta(days=60))
        past = _iso(datetime.now(timezone.utc) - timedelta(hours=1))
        for m in matches:
            api.put(f"{base_url}/api/matches/{m['id']}", headers=admin_headers, json={"kickoff": future})
        try:
            # tip all before locking
            tips = [{"match_id": m["id"], "team_id": m["home_team_id"]} for m in matches]
            r = api.post(f"{base_url}/api/rounds/13/tips", headers=fresh_user["headers"], json={"tips": tips})
            assert r.status_code == 200 and r.json()["saved"] == 4

            # now move match[0] into the past
            api.put(f"{base_url}/api/matches/{matches[0]['id']}", headers=admin_headers, json={"kickoff": past})

            data = api.get(f"{base_url}/api/rounds/13/all-tips", headers=fresh_user["headers"]).json()
            m0 = next(m for m in data["matches"] if m["match_id"] == matches[0]["id"])
            assert m0["revealed"] is True
            assert m0["home_count"] >= 1
            # others still hidden
            for m in data["matches"]:
                if m["match_id"] != matches[0]["id"]:
                    assert m["revealed"] is False
                    assert m["home_count"] == 0 and m["away_count"] == 0

            me = next(p for p in data["players"] if p["user_id"] == fresh_user["id"])
            assert matches[0]["id"] in me["tips"]
            assert me["tips"][matches[0]["id"]] == matches[0]["home_team_id"]
            # un-revealed matches must NOT appear in me["tips"]
            for m in matches[1:]:
                assert m["id"] not in me["tips"]
        finally:
            for mid, k in orig.items():
                if k:
                    api.put(f"{base_url}/api/matches/{mid}", headers=admin_headers, json={"kickoff": k})

    def test_admin_excluded_from_players(self, api, base_url, admin_headers, fresh_user):
        data = api.get(f"{base_url}/api/rounds/13/all-tips", headers=fresh_user["headers"]).json()
        admin_me = api.get(f"{base_url}/api/auth/me", headers=admin_headers).json()
        assert all(p["user_id"] != admin_me["id"] for p in data["players"])
        assert all(p["name"].lower() != "admin" for p in data["players"])
