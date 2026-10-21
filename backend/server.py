from fastapi import FastAPI, APIRouter, Depends, HTTPException, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pymongo import ReturnDocument
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, BeforeValidator, ConfigDict
from typing import List, Optional, Annotated
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALG = "HS256"
REGULAR_ROUNDS = 14

app = FastAPI()


@app.get("/health", include_in_schema=False)
@app.head("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}

api_router = APIRouter(prefix="/api")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------- Models ----------------
PyObjectId = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, ObjectId) else v)]


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    @classmethod
    def from_mongo(cls, doc):
        return cls.model_validate(doc) if doc else None

    def to_mongo(self):
        d = self.model_dump(by_alias=True, exclude={"id"})
        d.pop("_id", None)
        return d


class User(BaseDocument):
    email: str
    name: str
    role: str = "user"
    password_hash: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Team(BaseDocument):
    name: str
    short: str
    color: str
    secondary: str
    icon: str


class Round(BaseDocument):
    number: int
    name: str
    is_final: bool = False
    locked: bool = False


class Match(BaseDocument):
    round_number: int
    order: int = 0
    home_team_id: str
    away_team_id: str
    winner_team_id: Optional[str] = None  # team id or "draw"
    kickoff: Optional[str] = None  # ISO 8601 UTC

    def started(self) -> bool:
        if not self.kickoff:
            return False
        try:
            k = datetime.fromisoformat(self.kickoff.replace("Z", "+00:00"))
        except ValueError:
            return False
        if k.tzinfo is None:
            k = k.replace(tzinfo=timezone.utc)
        return k <= datetime.now(timezone.utc)

    def is_locked(self, round_locked: bool) -> bool:
        return round_locked or self.winner_team_id is not None or self.started()


class Tip(BaseDocument):
    user_id: str
    match_id: str
    round_number: int
    team_id: str


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TipItem(BaseModel):
    match_id: str
    team_id: str


class TipsIn(BaseModel):
    tips: List[TipItem]


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    short: Optional[str] = None
    color: Optional[str] = None
    secondary: Optional[str] = None
    icon: Optional[str] = None


class RoundCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class RoundUpdate(BaseModel):
    name: Optional[str] = None
    locked: Optional[bool] = None


class MatchCreate(BaseModel):
    home_team_id: str
    away_team_id: str


class MatchUpdate(BaseModel):
    home_team_id: Optional[str] = None
    away_team_id: Optional[str] = None
    winner_team_id: Optional[str] = None
    clear_result: bool = False
    kickoff: Optional[str] = None
    clear_kickoff: bool = False


# ---------------- Auth helpers ----------------
def hash_pw(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_pw(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except ValueError:
        return False


def make_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user.id, "role": user.role, "iat": now, "exp": now + timedelta(days=30)},
                      JWT_SECRET, algorithm=JWT_ALG)


def public_user(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role}


async def current_user(authorization: Optional[str] = Header(None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Not authenticated")
    try:
        claims = jwt.decode(authorization[7:], JWT_SECRET, algorithms=[JWT_ALG])
        user = User.from_mongo(await db.users.find_one({"_id": ObjectId(claims["sub"])}))
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    return user


async def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin role required")
    return user


def oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except Exception:
        raise HTTPException(404, "Not found")


# ---------------- Seeding ----------------
DEFAULT_TEAMS = [
    ("Northside Lions", "NSL", "#C8102E", "#FFD100", "paw"),
    ("Harbour Sharks", "HBS", "#0072CE", "#FFFFFF", "fish"),
    ("Valley Eagles", "VLE", "#1B5E20", "#FFC72C", "shield"),
    ("Coastal Thunder", "CST", "#F2A900", "#1A1A1A", "flash"),
    ("Metro Wolves", "MTW", "#5B6770", "#E35205", "moon"),
    ("Ridge Rockets", "RDR", "#E35205", "#FFFFFF", "rocket"),
    ("Riverside Royals", "RVR", "#6A1B9A", "#FFD100", "diamond"),
    ("Summit Stallions", "SMS", "#00843D", "#FFFFFF", "trophy"),
]


def round_robin(ids: List[str]) -> List[List[tuple]]:
    n = len(ids)
    arr = ids[:]
    rounds = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a, b = arr[i], arr[n - 1 - i]
            pairs.append((a, b) if (r + i) % 2 == 0 else (b, a))
        rounds.append(pairs)
        arr = [arr[0]] + [arr[-1]] + arr[1:-1]
    return rounds


async def seed():
    await db.users.create_index("email", unique=True)
    await db.tips.create_index([("user_id", 1), ("match_id", 1)], unique=True)
    await db.rounds.create_index("number", unique=True)
    email = os.environ['ADMIN_EMAIL'].lower()
    existing = await db.users.find_one({"email": email})
    if not existing:
        await db.users.insert_one(User(email=email, name="Admin", role="admin",
                                       password_hash=hash_pw(os.environ['ADMIN_PASSWORD'])).to_mongo())
    elif not verify_pw(os.environ['ADMIN_PASSWORD'], existing["password_hash"]):
        await db.users.update_one({"_id": existing["_id"]},
                                  {"$set": {"password_hash": hash_pw(os.environ['ADMIN_PASSWORD']), "role": "admin"}})
    if await db.teams.count_documents({}) == 0:
        await db.teams.insert_many([Team(name=n, short=s, color=c, secondary=s2, icon=i).to_mongo()
                                    for n, s, c, s2, i in DEFAULT_TEAMS])
    if await db.rounds.count_documents({}) == 0:
        team_ids = [str(t["_id"]) async for t in db.teams.find().sort("_id", 1)]
        rr = round_robin(team_ids)
        now = datetime.now(timezone.utc)
        first_sat = (now + timedelta(days=(5 - now.weekday()) % 7 or 7)).replace(hour=5, minute=0, second=0, microsecond=0)
        for r in range(REGULAR_ROUNDS):
            num = r + 1
            await db.rounds.insert_one(Round(number=num, name=f"Round {num}").to_mongo())
            pairs = rr[r % len(rr)]
            if r >= len(rr):
                pairs = [(b, a) for a, b in pairs]
            day = first_sat + timedelta(weeks=r)
            await db.matches.insert_many([Match(round_number=num, order=i, home_team_id=a, away_team_id=b,
                                                kickoff=(day + timedelta(hours=2 * i)).isoformat()).to_mongo()
                                          for i, (a, b) in enumerate(pairs)])


@app.on_event("startup")
async def on_startup():
    await seed()


# ---------------- Auth routes ----------------
@api_router.post("/auth/register")
async def register(body: RegisterIn):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "Email already registered")
    user = User(email=email, name=body.name.strip(), password_hash=hash_pw(body.password))
    res = await db.users.insert_one(user.to_mongo())
    user.id = str(res.inserted_id)
    return {"token": make_token(user), "user": public_user(user)}


@api_router.post("/auth/login")
async def login(body: LoginIn):
    user = User.from_mongo(await db.users.find_one({"email": body.email.lower()}))
    if not user or not verify_pw(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return {"token": make_token(user), "user": public_user(user)}


@api_router.get("/auth/me")
async def me(user: User = Depends(current_user)):
    return public_user(user)


# ---------------- Teams ----------------
@api_router.get("/teams")
async def list_teams():
    return [Team.from_mongo(t).model_dump() async for t in db.teams.find().sort("_id", 1)]


@api_router.put("/teams/{team_id}")
async def update_team(team_id: str, body: TeamUpdate, _: User = Depends(admin_user)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    doc = await db.teams.find_one_and_update({"_id": oid(team_id)}, {"$set": upd}, return_document=ReturnDocument.AFTER)
    if not doc:
        raise HTTPException(404, "Team not found")
    return Team.from_mongo(doc).model_dump()


# ---------------- Rounds ----------------
async def round_summaries(user_id: Optional[str] = None):
    rounds = [Round.from_mongo(r) async for r in db.rounds.find().sort("number", 1)]
    out = []
    for r in rounds:
        matches = [Match.from_mongo(m) async for m in db.matches.find({"round_number": r.number})]
        decided = sum(1 for m in matches if m.winner_team_id)
        revealed = sum(1 for m in matches if m.is_locked(r.locked))
        tipped = await db.tips.count_documents({"user_id": user_id, "round_number": r.number}) if user_id else 0
        out.append({**r.model_dump(), "match_count": len(matches), "decided_count": decided,
                    "revealed_count": revealed,
                    "tipped_count": tipped, "complete": len(matches) > 0 and decided == len(matches)})
    return out


@api_router.get("/rounds")
async def list_rounds(user: User = Depends(current_user)):
    return await round_summaries(user.id)


@api_router.get("/rounds/{number}")
async def get_round(number: int, user: User = Depends(current_user)):
    r = Round.from_mongo(await db.rounds.find_one({"number": number}))
    if not r:
        raise HTTPException(404, "Round not found")
    matches = [Match.from_mongo(m) async for m in db.matches.find({"round_number": number}).sort("order", 1)]
    tips = {t["match_id"]: t["team_id"] async for t in db.tips.find({"user_id": user.id, "round_number": number})}
    out = []
    correct = 0
    for m in matches:
        my = tips.get(m.id)
        is_correct = bool(m.winner_team_id and my and my == m.winner_team_id)
        correct += int(is_correct)
        out.append({**m.model_dump(), "my_tip": my, "locked": m.is_locked(r.locked), "started": m.started(),
                    "correct": is_correct if m.winner_team_id else None})
    complete = len(matches) > 0 and all(m.winner_team_id for m in matches)
    bonus = 1 if complete and correct == len(matches) else 0
    return {**r.model_dump(), "matches": out, "my_correct": correct, "my_bonus": bonus,
            "my_points": correct + bonus, "complete": complete}


@api_router.post("/rounds/{number}/tips")
async def submit_tips(number: int, body: TipsIn, user: User = Depends(current_user)):
    r = Round.from_mongo(await db.rounds.find_one({"number": number}))
    if not r:
        raise HTTPException(404, "Round not found")
    if r.locked:
        raise HTTPException(400, "This round is locked")
    saved = 0
    skipped = 0
    for t in body.tips:
        m = Match.from_mongo(await db.matches.find_one({"_id": oid(t.match_id), "round_number": number}))
        if not m:
            raise HTTPException(404, "Match not found")
        if m.is_locked(False):
            skipped += 1
            continue
        if t.team_id not in (m.home_team_id, m.away_team_id):
            raise HTTPException(400, "Team not in match")
        tip = Tip(user_id=user.id, match_id=m.id, round_number=number, team_id=t.team_id)
        await db.tips.update_one({"user_id": user.id, "match_id": m.id}, {"$set": tip.to_mongo()}, upsert=True)
        saved += 1
    return {"saved": saved, "skipped": skipped}


@api_router.get("/rounds/{number}/all-tips")
async def round_all_tips(number: int, _: User = Depends(current_user)):
    """Everyone's tips, revealed per match once that match is locked (kick-off, result, or round lock)."""
    r = Round.from_mongo(await db.rounds.find_one({"number": number}))
    if not r:
        raise HTTPException(404, "Round not found")
    matches = [Match.from_mongo(m) async for m in db.matches.find({"round_number": number}).sort("order", 1)]
    revealed = {m.id for m in matches if m.is_locked(r.locked)}
    users = {str(u["_id"]): User.from_mongo(u) async for u in db.users.find({"role": {"$ne": "admin"}})}
    picks: dict = {}
    async for t in db.tips.find({"round_number": number, "match_id": {"$in": list(revealed)}}):
        tip = Tip.from_mongo(t)
        if tip.user_id in users:
            picks.setdefault(tip.user_id, {})[tip.match_id] = tip.team_id
    winners = {m.id: m.winner_team_id for m in matches}
    out_matches = []
    for m in matches:
        home = sum(1 for p in picks.values() if p.get(m.id) == m.home_team_id)
        away = sum(1 for p in picks.values() if p.get(m.id) == m.away_team_id)
        out_matches.append({"match_id": m.id, "order": m.order, "home_team_id": m.home_team_id,
                            "away_team_id": m.away_team_id, "winner_team_id": m.winner_team_id,
                            "kickoff": m.kickoff, "revealed": m.id in revealed,
                            "home_count": home, "away_count": away})
    players = []
    for uid, u in users.items():
        p = picks.get(uid, {})
        correct = sum(1 for mid, tid in p.items() if winners.get(mid) == tid)
        players.append({"user_id": uid, "name": u.name, "tips": p, "correct": correct})
    players.sort(key=lambda x: (-x["correct"], x["name"].lower()))
    return {"number": r.number, "name": r.name, "matches": out_matches, "players": players}


@api_router.post("/rounds")
async def create_round(body: RoundCreate, _: User = Depends(admin_user)):
    last = await db.rounds.find_one(sort=[("number", -1)])
    num = (last["number"] if last else 0) + 1
    r = Round(number=num, name=body.name.strip(), is_final=num > REGULAR_ROUNDS)
    res = await db.rounds.insert_one(r.to_mongo())
    r.id = str(res.inserted_id)
    return r.model_dump()


@api_router.put("/rounds/{number}")
async def update_round(number: int, body: RoundUpdate, _: User = Depends(admin_user)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    doc = await db.rounds.find_one_and_update({"number": number}, {"$set": upd}, return_document=ReturnDocument.AFTER)
    if not doc:
        raise HTTPException(404, "Round not found")
    return Round.from_mongo(doc).model_dump()


@api_router.delete("/rounds/{number}")
async def delete_round(number: int, _: User = Depends(admin_user)):
    r = Round.from_mongo(await db.rounds.find_one({"number": number}))
    if not r:
        raise HTTPException(404, "Round not found")
    if not r.is_final:
        raise HTTPException(400, "Only finals rounds can be deleted")
    last = await db.rounds.find_one(sort=[("number", -1)])
    if last["number"] != number:
        raise HTTPException(400, "Only the last finals round can be deleted")
    await db.rounds.delete_one({"number": number})
    await db.matches.delete_many({"round_number": number})
    await db.tips.delete_many({"round_number": number})
    return {"deleted": True}


# ---------------- Matches ----------------
async def team_exists(tid: str):
    if not await db.teams.find_one({"_id": oid(tid)}):
        raise HTTPException(400, "Team not found")


@api_router.post("/rounds/{number}/matches")
async def add_match(number: int, body: MatchCreate, _: User = Depends(admin_user)):
    if not await db.rounds.find_one({"number": number}):
        raise HTTPException(404, "Round not found")
    if body.home_team_id == body.away_team_id:
        raise HTTPException(400, "A team cannot play itself")
    await team_exists(body.home_team_id)
    await team_exists(body.away_team_id)
    count = await db.matches.count_documents({"round_number": number})
    m = Match(round_number=number, order=count, home_team_id=body.home_team_id, away_team_id=body.away_team_id)
    res = await db.matches.insert_one(m.to_mongo())
    m.id = str(res.inserted_id)
    return m.model_dump()


@api_router.put("/matches/{match_id}")
async def update_match(match_id: str, body: MatchUpdate, _: User = Depends(admin_user)):
    m = Match.from_mongo(await db.matches.find_one({"_id": oid(match_id)}))
    if not m:
        raise HTTPException(404, "Match not found")
    home = body.home_team_id or m.home_team_id
    away = body.away_team_id or m.away_team_id
    if home == away:
        raise HTTPException(400, "A team cannot play itself")
    upd = {}
    if home != m.home_team_id or away != m.away_team_id:
        await team_exists(home)
        await team_exists(away)
        upd.update(home_team_id=home, away_team_id=away, winner_team_id=None)
        await db.tips.delete_many({"match_id": m.id})
    if body.clear_kickoff:
        upd["kickoff"] = None
    elif body.kickoff is not None:
        try:
            k = datetime.fromisoformat(body.kickoff.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, "Invalid kick-off time")
        if k.tzinfo is None:
            k = k.replace(tzinfo=timezone.utc)
        upd["kickoff"] = k.astimezone(timezone.utc).isoformat()
    if body.clear_result:
        upd["winner_team_id"] = None
    elif body.winner_team_id is not None:
        if body.winner_team_id not in (home, away, "draw"):
            raise HTTPException(400, "Winner must be a team in this match or 'draw'")
        upd["winner_team_id"] = body.winner_team_id
    if upd:
        doc = await db.matches.find_one_and_update({"_id": oid(m.id)}, {"$set": upd}, return_document=ReturnDocument.AFTER)
    else:
        doc = await db.matches.find_one({"_id": oid(m.id)})
    return Match.from_mongo(doc).model_dump()


@api_router.delete("/matches/{match_id}")
async def delete_match(match_id: str, _: User = Depends(admin_user)):
    res = await db.matches.delete_one({"_id": oid(match_id)})
    if not res.deleted_count:
        raise HTTPException(404, "Match not found")
    await db.tips.delete_many({"match_id": match_id})
    return {"deleted": True}


# ---------------- Leaderboard ----------------
@api_router.get("/leaderboard")
async def leaderboard(_: User = Depends(current_user)):
    matches = [Match.from_mongo(m) async for m in db.matches.find()]
    by_round = {}
    for m in matches:
        by_round.setdefault(m.round_number, []).append(m)
    complete_rounds = {rn: ms for rn, ms in by_round.items() if all(x.winner_team_id for x in ms)}
    winners = {m.id: m.winner_team_id for m in matches if m.winner_team_id}
    users = [User.from_mongo(u) async for u in db.users.find({"role": {"$ne": "admin"}})]
    tips_by_user = {}
    async for t in db.tips.find():
        tips_by_user.setdefault(t["user_id"], []).append(Tip.from_mongo(t))
    rows = []
    for u in users:
        tips = tips_by_user.get(u.id, [])
        correct_by_round = {}
        for t in tips:
            if winners.get(t.match_id) == t.team_id:
                correct_by_round[t.round_number] = correct_by_round.get(t.round_number, 0) + 1
        correct = sum(correct_by_round.values())
        bonus = sum(1 for rn, ms in complete_rounds.items() if correct_by_round.get(rn, 0) == len(ms))
        rows.append({"user_id": u.id, "name": u.name, "correct": correct, "bonus": bonus,
                     "points": correct + bonus, "tips": len(tips)})
    rows.sort(key=lambda r: (-r["points"], -r["correct"], r["name"].lower()))
    for i, r in enumerate(rows):
        r["rank"] = i + 1 if i == 0 or r["points"] != rows[i - 1]["points"] or r["correct"] != rows[i - 1]["correct"] else rows[i - 1]["rank"]
    return rows


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
