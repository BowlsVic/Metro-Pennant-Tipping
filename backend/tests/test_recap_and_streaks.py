"""Round Recap + Tip Streak feature tests (LIVE-DATA SAFE).

Approach (per review-request context note):
  * As admin, POST /api/rounds (creates a finals round, number > 14).
  * Add 3 matches to it using 6 distinct teams via POST /api/rounds/{n}/matches.
  * Register 3 TEST_recap_* players.
  * Each player submits tips BEFORE any winners are set (so matches aren't locked).
  * Admin PUTs winners on each match.
  * Verify GET /api/rounds/{n}/recap for each player + admin.
  * Verify GET /api/leaderboard includes streak + best_streak that respect
    kick-off / round / order ordering across decided matches.
  * CLEANUP: DELETE /api/rounds/{n} (removes matches + tips) and
    DELETE /api/admin/players/{id} for each test player.

Rounds 1-14 and real player Mel BV are NEVER touched.

Tip-pattern we build on the finals round (3 matches: m0, m1, m2):
  m0 winner = HOME.  P0 picks HOME (lone backer -> share=33).  P1,P2 pick AWAY.
  m1 winner = HOME.  All three pick HOME.
  m2 winner = HOME.  All three pick HOME.

Expected scores for the finals round:
  P0: 3 correct + perfect-bonus(1) = 4 points   -> won_round=True (sole winner)
  P1: 2 correct, no bonus          = 2 points
  P2: 2 correct, no bonus          = 2 points

Streak expectations (consecutive correct decided tips in kickoff/round/order):
  Rounds 1-14 currently have NO winners live, so the ONLY decided matches in
  the whole database belong to our finals round. Therefore:
    P0 streak = 3 (and best_streak = 3)
    P1 streak = 0 (missed m0 breaks it before any correct), best_streak = 2
    P2 streak = 0, best_streak = 2
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")


# ----------------------- helpers -----------------------
def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


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


# ----------------------- fixture -----------------------
@pytest.fixture(scope="module")
def ctx():
    admin_tok = _login_admin()
    adm_h = _h(admin_tok)

    # Get teams for match creation
    tr = requests.get(f"{BASE_URL}/api/teams", headers=adm_h, timeout=30)
    assert tr.status_code == 200, tr.text
    teams = tr.json()
    assert len(teams) >= 6, "need at least 6 teams to build 3 unique matches"
    team_ids = [t["id"] for t in teams[:6]]

    created_round_num = None
    player_records = []  # list of {token, id, email, headers}
    tag = uuid.uuid4().hex[:6]
    try:
        # ---- Create finals round (number > 14) -----------------------------
        cr = requests.post(f"{BASE_URL}/api/rounds", headers=adm_h,
                           json={"name": f"TEST Final {tag}"}, timeout=30)
        assert cr.status_code == 200, f"create round failed: {cr.text}"
        rd = cr.json()
        created_round_num = rd["number"]
        assert created_round_num > 14, f"expected finals (>14), got {created_round_num}"
        assert rd["is_final"] is True

        # ---- Add 3 matches to the round -----------------------------------
        matches = []
        for i in range(3):
            mr = requests.post(f"{BASE_URL}/api/rounds/{created_round_num}/matches",
                               headers=adm_h,
                               json={"home_team_id": team_ids[2 * i],
                                     "away_team_id": team_ids[2 * i + 1]},
                               timeout=30)
            assert mr.status_code == 200, f"add match {i} failed: {mr.text}"
            matches.append(mr.json())

        # ---- Register 3 players ------------------------------------------
        for i in range(3):
            em = f"TEST_recap_{tag}_{i}@example.com"
            tok, uid = _register(f"TEST Recap {tag} {i}", em)
            player_records.append({"token": tok, "id": uid, "email": em, "headers": _h(tok)})

        # ---- Submit tips BEFORE results ----------------------------------
        # Pattern: P0 picks HOME on all three. P1/P2 pick AWAY on m0, HOME on m1,m2.
        home = [m["home_team_id"] for m in matches]
        away = [m["away_team_id"] for m in matches]

        def _submit(player, tips):
            r = requests.post(f"{BASE_URL}/api/rounds/{created_round_num}/tips",
                              headers=player["headers"], json={"tips": tips}, timeout=30)
            assert r.status_code == 200, f"tip submit failed: {r.text}"
            assert r.json()["saved"] == len(tips), r.json()

        _submit(player_records[0], [
            {"match_id": matches[0]["id"], "team_id": home[0]},
            {"match_id": matches[1]["id"], "team_id": home[1]},
            {"match_id": matches[2]["id"], "team_id": home[2]},
        ])
        _submit(player_records[1], [
            {"match_id": matches[0]["id"], "team_id": away[0]},
            {"match_id": matches[1]["id"], "team_id": home[1]},
            {"match_id": matches[2]["id"], "team_id": home[2]},
        ])
        _submit(player_records[2], [
            {"match_id": matches[0]["id"], "team_id": away[0]},
            {"match_id": matches[1]["id"], "team_id": home[1]},
            {"match_id": matches[2]["id"], "team_id": home[2]},
        ])

        # ---- Recap BEFORE results: unavailable ---------------------------
        pre = requests.get(f"{BASE_URL}/api/rounds/{created_round_num}/recap",
                           headers=player_records[0]["headers"], timeout=30)
        assert pre.status_code == 200
        assert pre.json() == {"available": False}, pre.json()

        # ---- Set winners: HOME wins all three ----------------------------
        for i, m in enumerate(matches):
            ur = requests.put(f"{BASE_URL}/api/matches/{m['id']}", headers=adm_h,
                              json={"winner_team_id": home[i]}, timeout=30)
            assert ur.status_code == 200, f"set winner failed: {ur.text}"

        yield {"round": created_round_num, "matches": matches, "home": home, "away": away,
               "players": player_records, "admin_headers": adm_h}

    finally:
        # ---- Cleanup -----------------------------------------------------
        if created_round_num is not None:
            d = requests.delete(f"{BASE_URL}/api/rounds/{created_round_num}", headers=adm_h, timeout=30)
            # best-effort cleanup, log but don't fail teardown
            if d.status_code != 200:
                print(f"[cleanup] delete round {created_round_num}: {d.status_code} {d.text}")
        for p in player_records:
            d = requests.delete(f"{BASE_URL}/api/admin/players/{p['id']}", headers=adm_h, timeout=30)
            if d.status_code != 200:
                print(f"[cleanup] delete player {p['email']}: {d.status_code} {d.text}")


# ---------------------- Recap: availability ----------------------
def test_unknown_round_returns_404(ctx):
    p = ctx["players"][0]
    r = requests.get(f"{BASE_URL}/api/rounds/9999/recap", headers=p["headers"], timeout=30)
    assert r.status_code == 404

def test_regular_round_without_results_is_unavailable(ctx):
    # R1 live has no winners -> should return {available:false}
    p = ctx["players"][0]
    r = requests.get(f"{BASE_URL}/api/rounds/1/recap", headers=p["headers"], timeout=30)
    assert r.status_code == 200
    assert r.json() == {"available": False}

def test_unauthenticated_recap_is_401(ctx):
    r = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap", timeout=30)
    assert r.status_code in (401, 403)


# ---------------------- Recap: payload shape + fields ----------------------
def test_all_required_keys_present(ctx):
    p0 = ctx["players"][0]
    r = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                     headers=p0["headers"], timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ("available", "number", "name", "correct", "total", "bonus", "points",
              "tipped", "best_pick", "rank", "prev_rank", "players", "won_round",
              "round_top_points"):
        assert k in d, f"missing key: {k}"
    assert d["available"] is True
    assert d["number"] == ctx["round"]
    assert d["name"].startswith("TEST Final")
    assert d["total"] == 3
    assert d["tipped"] == 3
    # 14 live rounds exist before the finals round -> prev_rank should be populated
    assert d["prev_rank"] is not None

def test_no_mongo_id_leak(ctx):
    p0 = ctx["players"][0]
    r = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                     headers=p0["headers"], timeout=30).json()
    assert "_id" not in r
    if r["best_pick"]:
        assert "_id" not in r["best_pick"]


# ---------------------- Recap: scoring, bonus, won_round ----------------------
def test_p0_perfect_round(ctx):
    p0 = ctx["players"][0]
    d = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                     headers=p0["headers"], timeout=30).json()
    assert d["correct"] == 3
    assert d["bonus"] == 1
    assert d["points"] == 4
    assert d["won_round"] is True
    assert d["round_top_points"] == 4

def test_p1_two_correct_no_bonus(ctx):
    p1 = ctx["players"][1]
    d = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                     headers=p1["headers"], timeout=30).json()
    assert d["correct"] == 2
    assert d["bonus"] == 0
    assert d["points"] == 2
    assert d["won_round"] is False

def test_p2_matches_p1(ctx):
    p2 = ctx["players"][2]
    d = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                     headers=p2["headers"], timeout=30).json()
    assert d["correct"] == 2 and d["points"] == 2 and d["won_round"] is False


# ---------------------- Recap: best_pick lowest-share ----------------------
def test_p0_best_pick_is_lone_backer_match0(ctx):
    p0 = ctx["players"][0]
    d = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                     headers=p0["headers"], timeout=30).json()
    bp = d["best_pick"]
    assert bp is not None
    assert bp["match_id"] == ctx["matches"][0]["id"]
    assert bp["team_id"] == ctx["home"][0]
    assert bp["opponent_id"] == ctx["away"][0]
    # 1 of 3 players tipped HOME on m0 -> share = 33, backers = 1
    assert bp["backers"] == 1
    assert bp["share"] == 33

def test_p1_best_pick_is_shared_100(ctx):
    """P1 only has correct picks on m1 + m2 where all 3 picked HOME -> share=100."""
    p1 = ctx["players"][1]
    d = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                     headers=p1["headers"], timeout=30).json()
    bp = d["best_pick"]
    assert bp is not None
    assert bp["backers"] == 3
    assert bp["share"] == 100


# ---------------------- Recap: rank + prev_rank + admin ----------------------
def test_p0_is_rank_one_in_recap(ctx):
    d = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                     headers=ctx["players"][0]["headers"], timeout=30).json()
    # P0 (4 pts) is ahead of P1/P2 (2 pts) and Mel BV (0 pts)
    assert d["rank"] == 1
    assert d["players"] >= 3

def test_p1_p2_tied_below_p0(ctx):
    d1 = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                      headers=ctx["players"][1]["headers"], timeout=30).json()
    d2 = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                      headers=ctx["players"][2]["headers"], timeout=30).json()
    assert d1["rank"] == d2["rank"]
    assert d1["rank"] >= 2

def test_prev_rank_from_zero_point_ladder(ctx):
    # Rounds 1-14 have no results => zero-point ladder, everyone tied rank 1
    for p in ctx["players"]:
        d = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                         headers=p["headers"], timeout=30).json()
        assert d["prev_rank"] == 1, f"expected prev_rank=1 (tied zero-pt ladder), got {d['prev_rank']}"

def test_admin_rank_is_null(ctx):
    d = requests.get(f"{BASE_URL}/api/rounds/{ctx['round']}/recap",
                     headers=ctx["admin_headers"], timeout=30).json()
    assert d["available"] is True
    assert d["rank"] is None  # admin excluded from ladder
    assert d["prev_rank"] is None


# ---------------------- Leaderboard: streak + best_streak ----------------------
def test_leaderboard_rows_include_streak_fields(ctx):
    r = requests.get(f"{BASE_URL}/api/leaderboard",
                     headers=ctx["players"][0]["headers"], timeout=30)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) > 0
    for row in rows:
        assert "streak" in row, f"row missing streak: {row}"
        assert "best_streak" in row, f"row missing best_streak: {row}"
        assert isinstance(row["streak"], int)
        assert isinstance(row["best_streak"], int)
        assert row["best_streak"] >= row["streak"]
        assert "_id" not in row  # no mongo _id leak

def test_streak_values_match_tip_pattern(ctx):
    """P0 went 3/3 across the only decided matches -> streak=3, best_streak=3.
    P1 and P2 missed m0 (first decided match) then got m1+m2 right ->
    streak=2 (the current run), best_streak=2.
    """
    r = requests.get(f"{BASE_URL}/api/leaderboard",
                     headers=ctx["players"][0]["headers"], timeout=30)
    rows = r.json()
    by_id = {row["user_id"]: row for row in rows}
    p0, p1, p2 = ctx["players"]
    assert by_id[p0["id"]]["streak"] == 3
    assert by_id[p0["id"]]["best_streak"] == 3
    assert by_id[p1["id"]]["streak"] == 2
    assert by_id[p1["id"]]["best_streak"] == 2
    assert by_id[p2["id"]]["streak"] == 2
    assert by_id[p2["id"]]["best_streak"] == 2

def test_admin_absent_from_leaderboard(ctx):
    r = requests.get(f"{BASE_URL}/api/leaderboard", headers=ctx["admin_headers"], timeout=30)
    assert r.status_code == 200
    rows = r.json()
    names = [row["name"] for row in rows]
    assert "Admin" not in names  # admin excluded

def test_round_winners_lists_test_final(ctx):
    r = requests.get(f"{BASE_URL}/api/round-winners",
                     headers=ctx["players"][0]["headers"], timeout=30)
    assert r.status_code == 200
    rws = r.json()
    row = next((rw for rw in rws if rw["number"] == ctx["round"]), None)
    assert row is not None, f"test final round not in round-winners: {[rw['number'] for rw in rws]}"
    assert row["points"] == 4
    assert len(row["winners"]) == 1
    assert row["winners"][0]["user_id"] == ctx["players"][0]["id"]