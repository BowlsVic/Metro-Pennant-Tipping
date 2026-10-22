"""Round Recap Card feature tests.

Covers:
- GET /api/rounds/{n}/recap (unavailable before results, available after)
- best_pick lowest-share calculation
- rank + prev_rank + won_round + round_top_points
- Regression: /api/leaderboard and /api/round-winners after compute_standings(upto=...)
- Admin has rank==null (admin excluded from ladder)

Live-data safety: creates 3 TEST_recap_* players, sets then clears R1 + R2 winners,
and deletes the test players + their tips before the module exits. No rounds,
teams, matches, or kickoffs are mutated.
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://footy-tips-2.preview.emergentagent.com").rstrip("/")


def _login_admin():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "admin@tipping.com", "password": "Admin@123"}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


def _register(name, email):
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"name": name, "email": email, "password": "pass1234"}, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    body = r.json()
    return body["token"], body["user"]["id"]


def _headers(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def ctx():
    """Build a 3-player sandbox with R1 + R2 winners set.

    Players tip identically on most matches but DIFFER on match[0] (R1) so one
    of them owns the lowest-share correct pick for best_pick validation.
    """
    admin_tok = _login_admin()
    adm_h = _headers(admin_tok)

    # --- Create 3 test players ----------------------------------------------
    tag = uuid.uuid4().hex[:6]
    players = []
    for i in range(3):
        em = f"TEST_recap_{tag}_{i}@example.com"
        tok, uid = _register(f"TEST Recap {tag} {i}", em)
        players.append({"token": tok, "email": em, "id": uid, "headers": _headers(tok)})

    # --- Fetch R1 + R2 matches ----------------------------------------------
    def _round(n):
        rr = requests.get(f"{BASE_URL}/api/rounds/{n}", headers=adm_h, timeout=30)
        assert rr.status_code == 200
        return rr.json()

    r1 = _round(1)
    r2 = _round(2)
    r1_matches = r1["matches"]
    r2_matches = r2["matches"]

    saved_r1 = []  # matches we marked a winner on, to clear later
    saved_r2 = []

    try:
        # --- Submit tips BEFORE setting winners --------------------------------
        # R1: P0 picks ALL home teams (unique on match[0] vs others picking AWAY)
        # P1/P2 pick AWAY on match[0] -> if HOME wins match[0], P0 is the lone
        # backer => share=33% (lowest share).  On every other match in R1 all
        # three pick the same team so share=100%.
        def tips_pattern(matches, uniq_idx, uniq_choice, common_choice):
            """uniq_choice/common_choice: 'home' or 'away'."""
            out = []
            for idx, m in enumerate(matches):
                side = uniq_choice if idx == uniq_idx else common_choice
                tid = m["home_team_id"] if side == "home" else m["away_team_id"]
                out.append({"match_id": m["id"], "team_id": tid})
            return out

        # R1 tips
        p0_r1 = tips_pattern(r1_matches, uniq_idx=0, uniq_choice="home", common_choice="home")
        p1_r1 = tips_pattern(r1_matches, uniq_idx=0, uniq_choice="away", common_choice="home")
        p2_r1 = tips_pattern(r1_matches, uniq_idx=0, uniq_choice="away", common_choice="home")

        for p, tips in [(players[0], p0_r1), (players[1], p1_r1), (players[2], p2_r1)]:
            sr = requests.post(f"{BASE_URL}/api/rounds/1/tips", headers=p["headers"],
                               json={"tips": tips}, timeout=30)
            assert sr.status_code == 200, f"R1 tips save failed: {sr.text}"
            assert sr.json()["saved"] == len(r1_matches)

        # R2 tips: P1 picks ALL home. P0+P2 pick AWAY on match[0], HOME elsewhere.
        # So if HOME wins match[0] in R2 -> P1 is lone correct backer.
        # This means P1 wins R2 outright (8 correct + bonus=9).
        p0_r2 = tips_pattern(r2_matches, uniq_idx=0, uniq_choice="away", common_choice="home")
        p1_r2 = tips_pattern(r2_matches, uniq_idx=0, uniq_choice="home", common_choice="home")
        p2_r2 = tips_pattern(r2_matches, uniq_idx=0, uniq_choice="away", common_choice="home")

        for p, tips in [(players[0], p0_r2), (players[1], p1_r2), (players[2], p2_r2)]:
            sr = requests.post(f"{BASE_URL}/api/rounds/2/tips", headers=p["headers"],
                               json={"tips": tips}, timeout=30)
            assert sr.status_code == 200, f"R2 tips save failed: {sr.text}"
            assert sr.json()["saved"] == len(r2_matches)

        # --- BEFORE results: recap must be available=False ---------------------
        pre = requests.get(f"{BASE_URL}/api/rounds/1/recap", headers=players[0]["headers"], timeout=30)
        assert pre.status_code == 200
        assert pre.json() == {"available": False}

        # --- Set R1 winners: HOME wins everywhere ------------------------------
        for m in r1_matches:
            ur = requests.put(f"{BASE_URL}/api/matches/{m['id']}", headers=adm_h,
                              json={"winner_team_id": m["home_team_id"]}, timeout=30)
            assert ur.status_code == 200, f"set R1 winner failed: {ur.text}"
            saved_r1.append(m["id"])

        # --- Set R2 winners: HOME wins everywhere ------------------------------
        for m in r2_matches:
            ur = requests.put(f"{BASE_URL}/api/matches/{m['id']}", headers=adm_h,
                              json={"winner_team_id": m["home_team_id"]}, timeout=30)
            assert ur.status_code == 200
            saved_r2.append(m["id"])

        yield {
            "admin_headers": adm_h,
            "players": players,
            "r1_matches": r1_matches,
            "r2_matches": r2_matches,
        }

    finally:
        # Clear every result we set
        for mid in saved_r1 + saved_r2:
            requests.put(f"{BASE_URL}/api/matches/{mid}", headers=adm_h,
                         json={"clear_result": True}, timeout=30)
        # Delete each test player (also wipes their tips)
        for p in players:
            requests.delete(f"{BASE_URL}/api/admin/players/{p['id']}", headers=adm_h, timeout=30)


# ---------------- /api/rounds/{n}/recap ----------------
class TestRoundRecapAvailability:
    def test_incomplete_round_returns_available_false(self, ctx):
        # R3 is untouched -> no winners
        p = ctx["players"][0]
        r = requests.get(f"{BASE_URL}/api/rounds/3/recap", headers=p["headers"], timeout=30)
        assert r.status_code == 200
        assert r.json() == {"available": False}

    def test_unknown_round_returns_404(self, ctx):
        p = ctx["players"][0]
        r = requests.get(f"{BASE_URL}/api/rounds/9999/recap", headers=p["headers"], timeout=30)
        assert r.status_code == 404


class TestRoundRecapR1:
    """R1 is the FIRST round -> prev_rank must be None for everyone."""

    def test_shape_and_core_fields(self, ctx):
        p0 = ctx["players"][0]
        r = requests.get(f"{BASE_URL}/api/rounds/1/recap", headers=p0["headers"], timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("available", "number", "name", "correct", "total", "bonus", "points",
                  "tipped", "best_pick", "rank", "prev_rank", "players", "won_round",
                  "round_top_points"):
            assert k in d, f"missing key {k}"
        assert d["available"] is True
        assert d["number"] == 1
        assert d["total"] == len(ctx["r1_matches"])
        assert d["tipped"] == len(ctx["r1_matches"])
        assert d["prev_rank"] is None  # R1 is first round

    def test_p0_perfect_round_scores_8_plus_bonus(self, ctx):
        p0 = ctx["players"][0]
        r = requests.get(f"{BASE_URL}/api/rounds/1/recap", headers=p0["headers"], timeout=30).json()
        assert r["correct"] == 8
        assert r["bonus"] == 1
        assert r["points"] == 9
        assert r["won_round"] is True
        assert r["round_top_points"] == 9

    def test_p1_missed_match0_scores_7_no_bonus(self, ctx):
        p1 = ctx["players"][1]
        r = requests.get(f"{BASE_URL}/api/rounds/1/recap", headers=p1["headers"], timeout=30).json()
        assert r["correct"] == 7
        assert r["bonus"] == 0
        assert r["points"] == 7
        assert r["won_round"] is False

    def test_p0_best_pick_is_lone_backer_match0(self, ctx):
        p0 = ctx["players"][0]
        m0 = ctx["r1_matches"][0]
        r = requests.get(f"{BASE_URL}/api/rounds/1/recap", headers=p0["headers"], timeout=30).json()
        bp = r["best_pick"]
        assert bp is not None
        assert bp["match_id"] == m0["id"]
        assert bp["team_id"] == m0["home_team_id"]
        assert bp["opponent_id"] == m0["away_team_id"]
        # 1 of 3 players tipped HOME on match[0] -> share = 33 (rounded)
        assert bp["backers"] == 1
        assert bp["share"] == 33

    def test_p1_best_pick_share_is_100_on_shared_correct(self, ctx):
        """P1 only has correct picks on matches 1..7 where everyone tipped HOME -> share=100."""
        p1 = ctx["players"][1]
        r = requests.get(f"{BASE_URL}/api/rounds/1/recap", headers=p1["headers"], timeout=30).json()
        bp = r["best_pick"]
        assert bp is not None
        assert bp["share"] == 100
        assert bp["backers"] == 3

    def test_rank_order_p0_above_p1_p2(self, ctx):
        # After R1 only: P0=9pts, P1=P2=7pts (tie) -> P0 rank 1, P1/P2 tied at rank 2
        rp0 = requests.get(f"{BASE_URL}/api/rounds/1/recap",
                           headers=ctx["players"][0]["headers"], timeout=30).json()
        rp1 = requests.get(f"{BASE_URL}/api/rounds/1/recap",
                           headers=ctx["players"][1]["headers"], timeout=30).json()
        rp2 = requests.get(f"{BASE_URL}/api/rounds/1/recap",
                           headers=ctx["players"][2]["headers"], timeout=30).json()
        assert rp0["rank"] == 1
        assert rp1["rank"] == rp2["rank"] == 2
        # 3 test players + Mel BV (0 pts, last)
        assert rp0["players"] >= 3

    def test_admin_rank_is_null(self, ctx):
        r = requests.get(f"{BASE_URL}/api/rounds/1/recap", headers=ctx["admin_headers"], timeout=30).json()
        assert r["available"] is True
        assert r["rank"] is None  # admin excluded from ladder


class TestRoundRecapR2:
    """R2 is the SECOND round -> prev_rank must be populated from R1 standings."""

    def test_prev_rank_reflects_r1_standings(self, ctx):
        # After R1: P0 rank 1, P1/P2 tied rank 2.
        # After R2 (P1 perfect=9, P0=7, P2=7, cumulative):
        #   P0: 9+7=16, P1: 7+9=16, P2: 7+7=14
        #   P0 and P1 tie on 16 points (and same 'correct'=15) -> share rank 1.
        rp0 = requests.get(f"{BASE_URL}/api/rounds/2/recap",
                           headers=ctx["players"][0]["headers"], timeout=30).json()
        rp1 = requests.get(f"{BASE_URL}/api/rounds/2/recap",
                           headers=ctx["players"][1]["headers"], timeout=30).json()
        rp2 = requests.get(f"{BASE_URL}/api/rounds/2/recap",
                           headers=ctx["players"][2]["headers"], timeout=30).json()
        # prev_rank from R1
        assert rp0["prev_rank"] == 1
        assert rp1["prev_rank"] == 2
        assert rp2["prev_rank"] == 2
        # current rank after R2
        assert rp0["rank"] == rp1["rank"] == 1  # tied
        assert rp2["rank"] >= 3

    def test_p1_wins_r2_outright(self, ctx):
        rp1 = requests.get(f"{BASE_URL}/api/rounds/2/recap",
                           headers=ctx["players"][1]["headers"], timeout=30).json()
        assert rp1["correct"] == 8
        assert rp1["bonus"] == 1
        assert rp1["points"] == 9
        assert rp1["won_round"] is True
        assert rp1["round_top_points"] == 9

    def test_p1_best_pick_is_lone_backer_match0(self, ctx):
        p1 = ctx["players"][1]
        m0 = ctx["r2_matches"][0]
        r = requests.get(f"{BASE_URL}/api/rounds/2/recap", headers=p1["headers"], timeout=30).json()
        bp = r["best_pick"]
        assert bp is not None
        assert bp["match_id"] == m0["id"]
        assert bp["team_id"] == m0["home_team_id"]
        assert bp["share"] == 33
        assert bp["backers"] == 1


# ---------------- Regression: leaderboard + round-winners ----------------
class TestLadderRegression:
    def test_leaderboard_reflects_r1_plus_r2(self, ctx):
        r = requests.get(f"{BASE_URL}/api/leaderboard",
                         headers=ctx["players"][0]["headers"], timeout=30)
        assert r.status_code == 200
        rows = r.json()
        by_id = {row["user_id"]: row for row in rows}
        for p in ctx["players"]:
            assert p["id"] in by_id, f"player {p['email']} missing from ladder"
            assert "_id" not in by_id[p["id"]], "mongo _id leaked"
        # P0 and P1 should be tied at 16 points
        assert by_id[ctx["players"][0]["id"]]["points"] == 16
        assert by_id[ctx["players"][1]["id"]]["points"] == 16
        assert by_id[ctx["players"][2]["id"]]["points"] == 14
        # P0 wins R1, P1 wins R2 -> each has 1 round_win
        assert by_id[ctx["players"][0]["id"]]["round_wins"] == 1
        assert by_id[ctx["players"][1]["id"]]["round_wins"] == 1
        assert by_id[ctx["players"][2]["id"]]["round_wins"] == 0

    def test_round_winners_lists_r1_and_r2_latest_first(self, ctx):
        r = requests.get(f"{BASE_URL}/api/round-winners",
                         headers=ctx["players"][0]["headers"], timeout=30)
        assert r.status_code == 200
        rws = r.json()
        nums = [rw["number"] for rw in rws]
        assert 1 in nums and 2 in nums
        # Latest first
        idx1, idx2 = nums.index(1), nums.index(2)
        assert idx2 < idx1
        r1_row = next(rw for rw in rws if rw["number"] == 1)
        r2_row = next(rw for rw in rws if rw["number"] == 2)
        assert r1_row["points"] == 9
        assert r2_row["points"] == 9
        assert len(r1_row["winners"]) == 1
        assert r1_row["winners"][0]["user_id"] == ctx["players"][0]["id"]
        assert r2_row["winners"][0]["user_id"] == ctx["players"][1]["id"]


# ---------------- Auth gate ----------------
class TestRecapAuth:
    def test_unauthenticated_recap_is_401(self):
        r = requests.get(f"{BASE_URL}/api/rounds/1/recap", timeout=30)
        assert r.status_code in (401, 403)
