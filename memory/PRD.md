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

## Backlog
- P1: Match kick-off times with auto-lock; view other players' tips after lock
- P1: Margin tiebreaker; per-round leaderboard
- P2: Private leagues / invite codes; custom uploaded team logos
