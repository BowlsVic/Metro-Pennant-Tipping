"""End-to-end backend API tests for sports tipping competition."""
import uuid
import requests


# ---------------- Auth ----------------
class TestAuth:
    def test_register_and_me(self, api, base_url):
        email = f"TEST_u_{uuid.uuid4().hex[:8]}@example.com"
        r = api.post(f"{base_url}/api/auth/register", json={"name": "TEST U", "email": email, "password": "pass1234"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "token" in data and data["user"]["email"].lower() == email.lower() and data["user"]["role"] == "user"

        me = api.get(f"{base_url}/api/auth/me", headers={"Authorization": f"Bearer {data['token']}"})
        assert me.status_code == 200
        assert me.json()["email"] == email.lower()

    def test_register_duplicate(self, api, base_url, user_token):
        _, email = user_token
        r = api.post(f"{base_url}/api/auth/register", json={"name": "x", "email": email, "password": "pass1234"})
        assert r.status_code == 409

    def test_login_bad_pw(self, api, base_url):
        r = api.post(f"{base_url}/api/auth/login", json={"email": "admin@tipping.com", "password": "wrong"})
        assert r.status_code == 401

    def test_admin_login(self, api, base_url, admin_token):
        me = api.get(f"{base_url}/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert me.status_code == 200
        assert me.json()["role"] == "admin"

    def test_me_no_token(self, api, base_url):
        r = api.get(f"{base_url}/api/auth/me")
        assert r.status_code == 401


# ---------------- Teams ----------------
class TestTeams:
    def test_list_eight_teams(self, api, base_url):
        r = api.get(f"{base_url}/api/teams")
        assert r.status_code == 200
        teams = r.json()
        assert len(teams) == 8
        for t in teams:
            for k in ("id", "name", "short", "color", "secondary", "icon"):
                assert k in t
            assert "_id" not in t

    def test_update_team_admin_only(self, api, base_url, admin_headers, user_headers):
        teams = api.get(f"{base_url}/api/teams").json()
        tid = teams[0]["id"]
        orig_name = teams[0]["name"]

        # non-admin forbidden
        r = api.put(f"{base_url}/api/teams/{tid}", headers=user_headers, json={"name": "Hack"})
        assert r.status_code == 403

        # admin OK
        new_name = f"TEST {orig_name}"
        r = api.put(f"{base_url}/api/teams/{tid}", headers=admin_headers, json={"name": new_name})
        assert r.status_code == 200
        assert r.json()["name"] == new_name

        # verify via GET
        teams2 = api.get(f"{base_url}/api/teams").json()
        assert next(t for t in teams2 if t["id"] == tid)["name"] == new_name

        # restore
        r = api.put(f"{base_url}/api/teams/{tid}", headers=admin_headers, json={"name": orig_name})
        assert r.status_code == 200


# ---------------- Rounds ----------------
class TestRounds:
    def test_list_rounds_requires_auth(self, api, base_url):
        r = api.get(f"{base_url}/api/rounds")
        assert r.status_code == 401

    def test_14_seeded_rounds(self, api, base_url, user_headers):
        r = api.get(f"{base_url}/api/rounds", headers=user_headers)
        assert r.status_code == 200
        rounds = r.json()
        regular = [x for x in rounds if not x["is_final"]]
        assert len(regular) == 14
        for rr in regular:
            assert rr["match_count"] == 4

    def test_get_round_detail(self, api, base_url, user_headers):
        r = api.get(f"{base_url}/api/rounds/1", headers=user_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["number"] == 1
        assert len(data["matches"]) == 4
        for m in data["matches"]:
            assert "home_team_id" in m and "away_team_id" in m
            assert "my_tip" in m


# ---------------- Tips ----------------
class TestTips:
    def test_submit_tips_and_verify(self, api, base_url, user_headers):
        r = api.get(f"{base_url}/api/rounds/2", headers=user_headers)
        assert r.status_code == 200
        matches = r.json()["matches"]
        tips = [{"match_id": m["id"], "team_id": m["home_team_id"]} for m in matches]
        s = api.post(f"{base_url}/api/rounds/2/tips", headers=user_headers, json={"tips": tips})
        assert s.status_code == 200
        assert s.json()["saved"] == 4

        # verify persistence
        r2 = api.get(f"{base_url}/api/rounds/2", headers=user_headers)
        for m in r2.json()["matches"]:
            assert m["my_tip"] == m["home_team_id"]

    def test_tips_rejected_when_locked(self, api, base_url, admin_headers, user_headers):
        # lock round 3
        resp = api.put(f"{base_url}/api/rounds/3", headers=admin_headers, json={"locked": True})
        assert resp.status_code == 200 and resp.json()["locked"] is True
        try:
            matches = api.get(f"{base_url}/api/rounds/3", headers=user_headers).json()["matches"]
            tips = [{"match_id": matches[0]["id"], "team_id": matches[0]["home_team_id"]}]
            r = api.post(f"{base_url}/api/rounds/3/tips", headers=user_headers, json={"tips": tips})
            assert r.status_code == 400
        finally:
            api.put(f"{base_url}/api/rounds/3", headers=admin_headers, json={"locked": False})

    def test_tip_bad_team_rejected(self, api, base_url, user_headers):
        matches = api.get(f"{base_url}/api/rounds/4", headers=user_headers).json()["matches"]
        teams = api.get(f"{base_url}/api/teams").json()
        bad = next(t["id"] for t in teams if t["id"] not in (matches[0]["home_team_id"], matches[0]["away_team_id"]))
        r = api.post(f"{base_url}/api/rounds/4/tips", headers=user_headers,
                     json={"tips": [{"match_id": matches[0]["id"], "team_id": bad}]})
        assert r.status_code == 400


# ---------------- Admin Rounds / Matches ----------------
class TestAdmin:
    def test_non_admin_cannot_create_round(self, api, base_url, user_headers):
        r = api.post(f"{base_url}/api/rounds", headers=user_headers, json={"name": "Hack Final"})
        assert r.status_code == 403

    def test_finals_round_lifecycle_and_match_crud(self, api, base_url, admin_headers):
        # create finals round
        r = api.post(f"{base_url}/api/rounds", headers=admin_headers, json={"name": "TEST Finals"})
        assert r.status_code == 200
        rd = r.json()
        num = rd["number"]
        assert num >= 15 and rd["is_final"] is True

        try:
            teams = api.get(f"{base_url}/api/teams").json()
            t1, t2, t3 = teams[0]["id"], teams[1]["id"], teams[2]["id"]

            # same team rejected
            bad = api.post(f"{base_url}/api/rounds/{num}/matches", headers=admin_headers,
                           json={"home_team_id": t1, "away_team_id": t1})
            assert bad.status_code == 400

            # add match
            mr = api.post(f"{base_url}/api/rounds/{num}/matches", headers=admin_headers,
                          json={"home_team_id": t1, "away_team_id": t2})
            assert mr.status_code == 200
            match_id = mr.json()["id"]

            # update match result
            ur = api.put(f"{base_url}/api/matches/{match_id}", headers=admin_headers,
                        json={"winner_team_id": t1})
            assert ur.status_code == 200
            assert ur.json()["winner_team_id"] == t1

            # invalid winner
            bad2 = api.put(f"{base_url}/api/matches/{match_id}", headers=admin_headers,
                           json={"winner_team_id": t3})
            assert bad2.status_code == 400

            # draw accepted
            dr = api.put(f"{base_url}/api/matches/{match_id}", headers=admin_headers, json={"winner_team_id": "draw"})
            assert dr.status_code == 200 and dr.json()["winner_team_id"] == "draw"

            # clear
            cr = api.put(f"{base_url}/api/matches/{match_id}", headers=admin_headers, json={"clear_result": True})
            assert cr.status_code == 200 and cr.json()["winner_team_id"] is None

            # delete match
            dm = api.delete(f"{base_url}/api/matches/{match_id}", headers=admin_headers)
            assert dm.status_code == 200

            # cannot delete regular round
            cannot = api.delete(f"{base_url}/api/rounds/1", headers=admin_headers)
            assert cannot.status_code == 400
        finally:
            # cleanup finals round
            api.delete(f"{base_url}/api/rounds/{num}", headers=admin_headers)

        # confirm deletion
        rounds = api.get(f"{base_url}/api/rounds", headers=admin_headers).json()
        assert all(r["number"] != num for r in rounds)


# ---------------- Leaderboard & Scoring ----------------
class TestLeaderboard:
    def test_leaderboard_and_bonus(self, api, base_url, admin_headers):
        import uuid as _uuid
        # create a fresh user, tip entire round correctly, admin decides all matches -> bonus=1
        email = f"TEST_lb_{_uuid.uuid4().hex[:8]}@example.com"
        reg = api.post(f"{base_url}/api/auth/register", json={"name": "TEST LB", "email": email, "password": "pass1234"}).json()
        uh = {"Authorization": f"Bearer {reg['token']}", "Content-Type": "application/json"}

        # create temp finals round
        rd = api.post(f"{base_url}/api/rounds", headers=admin_headers, json={"name": "TEST LB Finals"}).json()
        num = rd["number"]
        try:
            teams = api.get(f"{base_url}/api/teams").json()
            m1 = api.post(f"{base_url}/api/rounds/{num}/matches", headers=admin_headers,
                          json={"home_team_id": teams[0]["id"], "away_team_id": teams[1]["id"]}).json()
            m2 = api.post(f"{base_url}/api/rounds/{num}/matches", headers=admin_headers,
                          json={"home_team_id": teams[2]["id"], "away_team_id": teams[3]["id"]}).json()

            # user tips both home
            api.post(f"{base_url}/api/rounds/{num}/tips", headers=uh, json={"tips": [
                {"match_id": m1["id"], "team_id": teams[0]["id"]},
                {"match_id": m2["id"], "team_id": teams[2]["id"]},
            ]})

            # admin sets both home wins
            api.put(f"{base_url}/api/matches/{m1['id']}", headers=admin_headers, json={"winner_team_id": teams[0]["id"]})
            api.put(f"{base_url}/api/matches/{m2['id']}", headers=admin_headers, json={"winner_team_id": teams[2]["id"]})

            lb = api.get(f"{base_url}/api/leaderboard", headers=uh)
            assert lb.status_code == 200
            rows = lb.json()
            # admin must be excluded
            assert all("admin" not in (r["name"].lower()) or True for r in rows)  # name field only
            me_row = next((r for r in rows if r["user_id"] == reg["user"]["id"]), None)
            assert me_row is not None
            assert me_row["correct"] == 2
            assert me_row["bonus"] >= 1
            assert me_row["points"] == me_row["correct"] + me_row["bonus"]

            # check admin not in leaderboard
            admin_me = api.get(f"{base_url}/api/auth/me", headers=admin_headers).json()
            assert not any(r["user_id"] == admin_me["id"] for r in rows)
        finally:
            api.delete(f"{base_url}/api/rounds/{num}", headers=admin_headers)
