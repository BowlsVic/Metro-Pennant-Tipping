# Tip Masters – Sports Tipping Competition (PRD)

## Original problem statement
Build a mobile app: that is a sports tipping competition. Set up for 14 rounds plus the option of adding additional rounds for finals. Eight teams, with team colours and logos.

## User choices
- Multiple players, leaderboard; email/password (JWT) login
- Admin user enters fixtures/results in the app
- 8 generic placeholder teams with colours + icon logos (editable)
- Scoring: 1 pt per correct tip + 1 bonus pt for all tips correct in a round

## Architecture
- Backend: FastAPI + MongoDB (users, teams, rounds, matches, tips). JWT (bcrypt + PyJWT). Seeds admin, 8 teams, 14 rounds (double round-robin, 4 matches each) on startup.
- Frontend: Expo Router, dark "tactical" theme (Barlow Condensed + DM Sans), tabs: Tips / Ladder / Teams / Profile (NativeTabs on iOS 26+). Admin stack: /admin, /admin/round/[number], /admin/team/[id].

## Implemented (2026-06)
- Auth (register/login/me), Tips screen with round chips + sticky submit, ladder with podium, teams grid, profile stats
- Admin: add/delete finals rounds, lock rounds, add/edit/delete matches, enter results (home/draw/away/TBD), edit team name/code/colours/icon
- Tested: 16/16 backend tests, all frontend flows pass

## Iteration 2 (2026-06)
- Kick-off times per match (ISO UTC); tips auto-lock at kick-off (server + live client tick). Seeded weekly Saturday kick-offs. Admin kick-off modal (day/hour/min steppers, apply to all, clear)
- Everyone's tips screen (/round-tips/[n]): per-match tipping split + player-by-player table, revealed match-by-match once locked (no leaks)
- Tested: 27/27 backend, frontend flows pass

## Iteration 3 (2026-06)
- Real fixture loaded: 2026-27 Metro Pennant Weekend Premier Reserve (Bowlslink competition 649a52f2-…), rounds 1–14, 56 matches, real kick-off times (UTC; Fri 7pm / Sat 1pm Melbourne). Stored in /app/backend/fixture.json and used as the startup seed (so production gets it too)
- Placeholder teams replaced with the 8 real clubs (icon logos + assigned colours, editable). Each match locks at its own kick-off
- Admin can add teams (up to 16) and delete teams not used in fixtures
- Season reset: no tips, results or finals rounds
- Note: club logos from Bowlslink not used (Middle Park's image is access-restricted); could add uploaded logos via object storage later
- Testing caution: backend tests mutate the live season data; always reset rounds/matches/tips after test runs

## Iteration 4 (2026-06)
- Added 2026-27 Metro Pennant Weekend Premier Division (Bowlslink competition ecc00663-…): 8 more clubs (Lalor, Moonee Valley, MCC, Bundoora, Deer Park, Altona, Yarraville Footscray, Essendon) listed first, then Premier Reserve clubs
- Each round now has 8 matches: Premier Division (orders 0–3) then Premier Reserve (4–7); Match.group label shown as section headings on Tips screen
- fixture.json now has "competitions" list; Team.sort controls list order; MAX_TEAMS raised to 24
- Everyone's tips table scrolls horizontally for 8 matches
- Perfect-round bonus now means all 8 matches correct

## Backlog
- P1: Push reminders before kick-off (on request only); per-round ladder
- P1: Margin tiebreaker; per-round leaderboard
- P2: Private leagues / invite codes; custom uploaded team logos
