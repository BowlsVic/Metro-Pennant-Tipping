# Tip Masters: brief for rebuilding as a web app

Paste the prompt below into a new **Full Stack App** project on Emergent.
If you imported this GitHub repo, the new agent can also read `backend/server.py` and `backend/fixture.json` directly.

---

## Prompt to paste

Build a web app called **Tip Masters**: a tipping competition for the 2026-27 Metro Pennant Weekend bowls season (Victoria).

**Login:** email and password only (JWT). One admin account; everyone else is a player. Admin password must be strong and must not be written in any project file. Limit repeated failed logins.

**Season:**
- 2 divisions: **Premier Division** (Lalor, Moonee Valley, MCC, Bundoora, Deer Park, Altona, Yarraville Footscray, Essendon) and **Premier Reserve** (Melbourne, Glenroy, Port Melbourne, Heathmont, Lilydale, Clayton, Club Sunbury, Middle Park). Premier Division is always listed first.
- 14 rounds, 8 matches each (4 per division), with real start times from Bowlslink:
  - Premier Division: https://results.bowlslink.com.au/competition/ecc00663-ab13-4e15-95ae-69b7d00651cf
  - Premier Reserve: https://results.bowlslink.com.au/competition/649a52f2-d060-44a3-a3c8-707c3f4c77a7
  - Data API: `https://api.bowlslink.com.au/results-api/competition/<id>/matches`
  - If this repo was imported, reuse `backend/fixture.json` (teams, rounds, start times, Bowlslink ids).
- Admin can add finals rounds; finals matches are also imported automatically from Bowlslink once both teams are known.

**Tipping:**
- Players pick a winner for each match. Each match locks at its own start time; admin can also lock a whole round.
- Scoring: 1 point per correct tip, plus 1 bonus point for getting every match in a round right.
- "Everyone's tips": once a match locks, show how every player tipped it (never before).
- Filter the tips page by division (All / Premier Division / Premier Reserve).

**Ladder:** overall ranking, top-3 podium, and **round winners** (top scorer of each completed round, ties shared) with a trophy badge and win count.

**Teams:** club colours and real club logos (import from Bowlslink, plus admin upload via object storage). Up to 24 teams; admin can add, edit and delete teams.

**Admin dashboard:**
- Fixtures & results: enter results (home / draw / away / not played), edit start times and fixtures, add and delete matches.
- **Bowlslink auto-sync** every 15 minutes, plus a "Sync now" button. It pulls results, start-time changes and finals matches.
- Players: list all players and remove a player (and their tips).

**Design:** dark, sporty look, works well on phones and desktop browsers.

---

## Notes
- Bring over real players: Mel BV (melanietags@hotmail.com) is the only real player so far. She can simply register again on the new site.
- No tips or results have been entered yet, so nothing else needs migrating.
