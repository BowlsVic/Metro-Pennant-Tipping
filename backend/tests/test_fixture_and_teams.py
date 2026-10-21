"""Iteration 3 tests: real Bowlslink fixture + team CRUD (POST/DELETE /api/teams)."""


EXPECTED_TEAMS = {"Melbourne", "Glenroy", "Port Melbourne", "Heathmont",
                  "Lilydale", "Clayton", "Club Sunbury", "Middle Park"}


# ---------------- Fixture validation ----------------
class TestRealFixture:
    def test_eight_real_clubs(self, api, base_url):
        r = api.get(f"{base_url}/api/teams")
        assert r.status_code == 200
        teams = r.json()
        names = {t["name"] for t in teams}
        # at least the 8 real clubs are present
        missing = EXPECTED_TEAMS - names
        assert not missing, f"missing real clubs: {missing}"

    def test_14_rounds_no_finals_no_results_no_tips(self, api, base_url, user_headers):
        rounds = api.get(f"{base_url}/api/rounds", headers=user_headers).json()
        assert len(rounds) == 14, f"expected 14 rounds, got {len(rounds)}"
        for rr in rounds:
            assert rr["is_final"] is False
            assert rr["match_count"] == 4
            assert rr["decided_count"] == 0, f"round {rr['number']} has results"
            assert rr["tipped_count"] == 0, f"round {rr['number']} has tips"

    def _match_key(self, m, teams_by_id):
        return (teams_by_id[m["home_team_id"]], teams_by_id[m["away_team_id"]], m["kickoff"])

    def test_round1_matches(self, api, base_url, user_headers):
        teams = api.get(f"{base_url}/api/teams").json()
        tn = {t["id"]: t["name"] for t in teams}
        r1 = api.get(f"{base_url}/api/rounds/1", headers=user_headers).json()
        actual = {self._match_key(m, tn) for m in r1["matches"]}
        expected = {
            ("Port Melbourne", "Club Sunbury", "2026-10-23T08:00:00+00:00"),
            ("Clayton", "Lilydale", "2026-10-23T08:00:00+00:00"),
            ("Middle Park", "Glenroy", "2026-10-23T08:00:00+00:00"),
            ("Melbourne", "Heathmont", "2026-10-23T08:00:00+00:00"),
        }
        assert actual == expected, f"R1 mismatch\nactual={actual}\nexpected={expected}"

    def test_round3_kickoffs_split(self, api, base_url, user_headers):
        teams = api.get(f"{base_url}/api/teams").json()
        tn = {t["id"]: t["name"] for t in teams}
        r3 = api.get(f"{base_url}/api/rounds/3", headers=user_headers).json()
        by_pair = {(tn[m["home_team_id"]], tn[m["away_team_id"]]): m["kickoff"] for m in r3["matches"]}
        assert by_pair[("Port Melbourne", "Glenroy")] == "2026-10-30T08:00:00+00:00"
        for pair in [("Melbourne", "Club Sunbury"), ("Clayton", "Heathmont"), ("Middle Park", "Lilydale")]:
            assert by_pair[pair] == "2026-10-31T02:00:00+00:00", f"{pair} wrong kickoff"

    def test_round14_all_same_kickoff(self, api, base_url, user_headers):
        r14 = api.get(f"{base_url}/api/rounds/14", headers=user_headers).json()
        for m in r14["matches"]:
            assert m["kickoff"] == "2027-01-30T02:00:00+00:00"


# ---------------- Team CRUD ----------------
class TestTeamCRUD:
    def test_create_team_requires_admin(self, api, base_url, user_headers):
        r = api.post(f"{base_url}/api/teams", headers=user_headers,
                     json={"name": "TEST Hackers", "short": "hck"})
        assert r.status_code == 403

    def test_create_team_requires_name_and_short(self, api, base_url, admin_headers):
        r = api.post(f"{base_url}/api/teams", headers=admin_headers, json={"name": "", "short": "AB"})
        assert r.status_code == 400
        r = api.post(f"{base_url}/api/teams", headers=admin_headers, json={"name": "TEST Only"})
        assert r.status_code == 400

    def test_create_delete_team_lifecycle(self, api, base_url, admin_headers):
        pre_count = len(api.get(f"{base_url}/api/teams").json())
        r = api.post(f"{base_url}/api/teams", headers=admin_headers,
                     json={"name": "TEST Falcons", "short": "fal", "color": "#123456",
                           "secondary": "#abcdef", "icon": "flash"})
        assert r.status_code == 200, r.text
        t = r.json()
        tid = t["id"]
        try:
            assert t["short"] == "FAL", f"short not uppercased: {t['short']}"
            assert t["name"] == "TEST Falcons"
            assert t["color"] == "#123456"

            # GET verifies persistence
            teams = api.get(f"{base_url}/api/teams").json()
            assert any(x["id"] == tid for x in teams)
            assert len(teams) == pre_count + 1

            # Non-admin cannot delete
            # (skipped - covered by other test)

            # Admin deletes
            d = api.delete(f"{base_url}/api/teams/{tid}", headers=admin_headers)
            assert d.status_code == 200
            assert d.json()["deleted"] is True
            tid = None

            # Verify gone
            teams2 = api.get(f"{base_url}/api/teams").json()
            assert all(x["id"] != tid for x in teams2) if tid else True
            assert len(teams2) == pre_count
        finally:
            if tid:
                api.delete(f"{base_url}/api/teams/{tid}", headers=admin_headers)

    def test_delete_team_in_use_rejected(self, api, base_url, admin_headers):
        teams = api.get(f"{base_url}/api/teams").json()
        in_use = next(t for t in teams if t["name"] == "Melbourne")
        r = api.delete(f"{base_url}/api/teams/{in_use['id']}", headers=admin_headers)
        assert r.status_code == 400
        assert "fixtures" in r.json().get("detail", "").lower()

    def test_delete_team_requires_admin(self, api, base_url, user_headers, admin_headers):
        # Create a disposable team to attempt non-admin delete
        c = api.post(f"{base_url}/api/teams", headers=admin_headers,
                     json={"name": "TEST Nomads", "short": "nmd"}).json()
        tid = c["id"]
        try:
            r = api.delete(f"{base_url}/api/teams/{tid}", headers=user_headers)
            assert r.status_code == 403
        finally:
            api.delete(f"{base_url}/api/teams/{tid}", headers=admin_headers)

    def test_max_16_teams_enforced(self, api, base_url, admin_headers):
        start = len(api.get(f"{base_url}/api/teams").json())
        created = []
        try:
            # Fill up to 16
            for i in range(16 - start):
                r = api.post(f"{base_url}/api/teams", headers=admin_headers,
                             json={"name": f"TEST Extra {i}", "short": f"X{i:02d}"})
                assert r.status_code == 200, f"fill {i}: {r.status_code} {r.text}"
                created.append(r.json()["id"])
            assert len(api.get(f"{base_url}/api/teams").json()) == 16

            # 17th rejected
            r = api.post(f"{base_url}/api/teams", headers=admin_headers,
                         json={"name": "TEST Overflow", "short": "OVR"})
            assert r.status_code == 400
            assert "16" in r.json().get("detail", "") or "maximum" in r.json().get("detail", "").lower()
        finally:
            for tid in created:
                api.delete(f"{base_url}/api/teams/{tid}", headers=admin_headers)
            assert len(api.get(f"{base_url}/api/teams").json()) == start
