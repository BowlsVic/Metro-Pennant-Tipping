from fastapi import FastAPI, APIRouter, Depends, HTTPException, Header, UploadFile, File, Response
from starlette.concurrency import run_in_threadpool
import asyncio
import uuid
import httpx
import requests
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pymongo import ReturnDocument
import os
import json
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
MAX_TEAMS = 24

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
    apple_sub: Optional[str] = None
    picture: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Team(BaseDocument):
    name: str
    short: str
    color: str
    secondary: str
    icon: str
    sort: int = 0
    logo_path: Optional[str] = None
    logo_v: int = 0
    ext_id: Optional[str] = None  # Bowlslink competitor id


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
    group: Optional[str] = None  # division label, e.g. "Premier Division"
    ext_id: Optional[str] = None  # Bowlslink match id

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


class GoogleSessionIn(BaseModel):
    session_id: str = Field(min_length=1)


class AppleIn(BaseModel):
    identity_token: str = Field(min_length=1)
    name: Optional[str] = None
    email: Optional[str] = None


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
# Real 2026-27 Metro Pennant Weekend draws (Bowlslink): Premier Division first, then Premier Reserve.
FIXTURE = json.loads((ROOT_DIR / "fixture.json").read_text())


async def seed():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("apple_sub", unique=True, partialFilterExpression={"apple_sub": {"$type": "string"}})
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
        teams = [t for c in FIXTURE["competitions"] for t in c["teams"]]
        await db.teams.insert_many([Team(**t, sort=i).to_mongo() for i, t in enumerate(teams)])
    if await db.rounds.count_documents({}) == 0:
        ids = {t["name"]: str(t["_id"]) async for t in db.teams.find()}
        numbers = sorted({r["number"] for c in FIXTURE["competitions"] for r in c["rounds"]})[:REGULAR_ROUNDS]
        for num in numbers:
            await db.rounds.insert_one(Round(number=num, name=f"Round {num}").to_mongo())
            matches = [(c["group"], m) for c in FIXTURE["competitions"] for r in c["rounds"] if r["number"] == num
                       for m in r["matches"]]
            await db.matches.insert_many([Match(round_number=num, order=i, home_team_id=ids[m["home"]],
                                                away_team_id=ids[m["away"]], kickoff=m["kickoff"], group=g,
                                                ext_id=m.get("ext_id")).to_mongo()
                                          for i, (g, m) in enumerate(matches)])


@app.on_event("startup")
async def on_startup():
    await seed()
    try:
        await run_in_threadpool(init_storage)
    except Exception as e:
        logger.warning(f"Object storage init failed: {e}")
    asyncio.create_task(sync_loop())


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


# ---------------- Social sign-in (Emergent Google, Apple) ----------------
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
APPLE_ISSUER = "https://appleid.apple.com"
APPLE_AUDIENCES = [a.strip() for a in os.environ.get("APPLE_AUDIENCES", "").split(",") if a.strip()]
apple_jwks = jwt.PyJWKClient(f"{APPLE_ISSUER}/auth/keys", cache_keys=True)


async def upsert_social_user(email: Optional[str], name: Optional[str], picture: Optional[str] = None,
                             apple_sub: Optional[str] = None) -> User:
    """Links to an existing account (Apple id first, then email) so players keep their tips and role."""
    doc = await db.users.find_one({"apple_sub": apple_sub}) if apple_sub else None
    if not doc and email:
        doc = await db.users.find_one({"email": email})
    if doc:
        upd = {}
        if apple_sub and not doc.get("apple_sub"):
            upd["apple_sub"] = apple_sub
        if picture and not doc.get("picture"):
            upd["picture"] = picture
        if upd:
            await db.users.update_one({"_id": doc["_id"]}, {"$set": upd})
            doc.update(upd)
        return User.from_mongo(doc)
    display = (name or "").strip() or (email.split("@")[0] if email else "Apple player")
    user = User(email=email or f"apple_{apple_sub[:12]}@privaterelay.local", name=display[:40],
                apple_sub=apple_sub, picture=picture)
    res = await db.users.insert_one(user.to_mongo())
    user.id = str(res.inserted_id)
    return user


@api_router.post("/auth/session")
async def google_session(body: GoogleSessionIn):
    """Exchanges the one-time Emergent session_id (from the Google redirect) for an app token."""
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": body.session_id})
    if r.status_code != 200:
        raise HTTPException(401, "Google sign-in failed or expired. Please try again")
    data = r.json()
    email = (data.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(401, "Google account has no email")
    user = await upsert_social_user(email, data.get("name"), data.get("picture"))
    token = make_token(user)
    return {"session_token": token, "token": token, "user": public_user(user)}


@api_router.post("/auth/apple")
async def apple_sign_in(body: AppleIn):
    try:
        key = await run_in_threadpool(apple_jwks.get_signing_key_from_jwt, body.identity_token)
        claims = jwt.decode(body.identity_token, key.key, algorithms=["RS256"], audience=APPLE_AUDIENCES,
                            issuer=APPLE_ISSUER)
    except Exception:
        raise HTTPException(401, "Apple sign-in could not be verified")
    sub = claims["sub"]
    token_email = claims.get("email")
    verified = str(claims.get("email_verified", "false")).lower() == "true"
    email = (token_email if verified else None) or (body.email if not token_email else None)
    user = await upsert_social_user(email.lower().strip() if email else None, body.name, apple_sub=sub)
    token = make_token(user)
    return {"session_token": token, "token": token, "user": public_user(user)}


# ---------------- Teams ----------------
@api_router.get("/teams")
async def list_teams():
    teams = [Team.from_mongo(t).model_dump() async for t in db.teams.find()]
    return sorted(teams, key=lambda t: t["name"].lower())


@api_router.post("/teams")
async def create_team(body: TeamUpdate, _: User = Depends(admin_user)):
    if await db.teams.count_documents({}) >= MAX_TEAMS:
        raise HTTPException(400, f"Maximum of {MAX_TEAMS} teams reached")
    if not body.name or not body.name.strip() or not body.short or not body.short.strip():
        raise HTTPException(400, "Name and short code are required")
    last = await db.teams.find_one(sort=[("sort", -1)])
    t = Team(name=body.name.strip(), short=body.short.strip().upper()[:4], color=body.color or "#0072CE",
             secondary=body.secondary or "#FFFFFF", icon=body.icon or "shield", sort=(last or {}).get("sort", 0) + 1)
    res = await db.teams.insert_one(t.to_mongo())
    t.id = str(res.inserted_id)
    return t.model_dump()


@api_router.delete("/teams/{team_id}")
async def delete_team(team_id: str, _: User = Depends(admin_user)):
    if await db.matches.find_one({"$or": [{"home_team_id": team_id}, {"away_team_id": team_id}]}):
        raise HTTPException(400, "Team is used in fixtures. Remove its matches first")
    res = await db.teams.delete_one({"_id": oid(team_id)})
    if not res.deleted_count:
        raise HTTPException(404, "Team not found")
    return {"deleted": True}


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
async def compute_standings(upto: Optional[int] = None):
    """Season ladder rows plus the top scorer(s) of every completed round (ties share the win).
    `upto` limits the ladder to rounds <= that number (used for ladder movement)."""
    mq = {"round_number": {"$lte": upto}} if upto is not None else {}
    matches = [Match.from_mongo(m) async for m in db.matches.find(mq)]
    by_round = {}
    for m in matches:
        by_round.setdefault(m.round_number, []).append(m)
    complete_rounds = {rn: ms for rn, ms in by_round.items() if all(x.winner_team_id for x in ms)}
    winners = {m.id: m.winner_team_id for m in matches if m.winner_team_id}
    decided_seq = sorted((m for m in matches if m.winner_team_id),
                         key=lambda m: (m.kickoff or "", m.round_number, m.order))
    round_names = {r["number"]: r["name"] async for r in db.rounds.find()}
    users = [User.from_mongo(u) async for u in db.users.find({"role": {"$ne": "admin"}})]
    names = {u.id: u.name for u in users}
    tips_by_user = {}
    async for t in db.tips.find(mq):
        tips_by_user.setdefault(t["user_id"], []).append(Tip.from_mongo(t))
    rows, round_pts = [], {}
    for u in users:
        tips = tips_by_user.get(u.id, [])
        correct_by_round = {}
        for t in tips:
            if winners.get(t.match_id) == t.team_id:
                correct_by_round[t.round_number] = correct_by_round.get(t.round_number, 0) + 1
        bonus = 0
        for rn, ms in complete_rounds.items():
            c = correct_by_round.get(rn, 0)
            perfect = 1 if c == len(ms) else 0
            bonus += perfect
            round_pts.setdefault(rn, {})[u.id] = c + perfect
        correct = sum(correct_by_round.values())
        # Tip streaks: consecutive correct tips across decided matches in kick-off order.
        # A wrong tip, a missed tip or a draw ends the run.
        picks = {t.match_id: t.team_id for t in tips}
        streak = best_streak = 0
        for m in decided_seq:
            if picks.get(m.id) == m.winner_team_id:
                streak += 1
                best_streak = max(best_streak, streak)
            else:
                streak = 0
        rows.append({"user_id": u.id, "name": u.name, "correct": correct, "bonus": bonus,
                     "points": correct + bonus, "tips": len(tips), "round_wins": 0,
                     "streak": streak, "best_streak": best_streak})
    round_winners = []
    for rn in sorted(complete_rounds):
        pts = round_pts.get(rn, {})
        best = max(pts.values(), default=0)
        if best <= 0:
            continue
        ids = sorted((uid for uid, p in pts.items() if p == best), key=lambda x: names[x].lower())
        round_winners.append({"number": rn, "name": round_names.get(rn, f"Round {rn}"), "points": best,
                              "winners": [{"user_id": uid, "name": names[uid]} for uid in ids]})
    wins = {}
    for rw in round_winners:
        for w in rw["winners"]:
            wins[w["user_id"]] = wins.get(w["user_id"], 0) + 1
    for r in rows:
        r["round_wins"] = wins.get(r["user_id"], 0)
    rows.sort(key=lambda r: (-r["points"], -r["correct"], r["name"].lower()))
    for i, r in enumerate(rows):
        r["rank"] = i + 1 if i == 0 or r["points"] != rows[i - 1]["points"] or r["correct"] != rows[i - 1]["correct"] else rows[i - 1]["rank"]
    return rows, round_winners


@api_router.get("/leaderboard")
async def leaderboard(_: User = Depends(current_user)):
    rows, _w = await compute_standings()
    return rows


@api_router.get("/round-winners")
async def round_winners(_: User = Depends(current_user)):
    """Completed rounds, latest first, with the player(s) who scored most that round."""
    _rows, winners = await compute_standings()
    return list(reversed(winners))


@api_router.get("/rounds/{number}/recap")
async def round_recap(number: int, user: User = Depends(current_user)):
    """Personal summary of a completed round: score, boldest correct pick and ladder movement."""
    r = Round.from_mongo(await db.rounds.find_one({"number": number}))
    if not r:
        raise HTTPException(404, "Round not found")
    matches = [Match.from_mongo(m) async for m in db.matches.find({"round_number": number})]
    if not matches or not all(m.winner_team_id for m in matches):
        return {"available": False}
    player_ids = {str(u["_id"]) async for u in db.users.find({"role": {"$ne": "admin"}}, {"_id": 1})}
    all_tips = [Tip.from_mongo(t) async for t in db.tips.find({"round_number": number})]
    all_tips = [t for t in all_tips if t.user_id in player_ids]
    mine = {t.match_id: t.team_id for t in all_tips if t.user_id == user.id}
    by_id = {m.id: m for m in matches}
    correct = sum(1 for mid, tid in mine.items() if by_id.get(mid) and by_id[mid].winner_team_id == tid)
    bonus = 1 if correct == len(matches) else 0
    best = None
    for mid, tid in mine.items():
        m = by_id.get(mid)
        if not m or m.winner_team_id != tid:
            continue
        backers = sum(1 for t in all_tips if t.match_id == mid and t.team_id == tid)
        total = sum(1 for t in all_tips if t.match_id == mid) or 1
        share = round(100 * backers / total)
        if best is None or share < best["share"]:
            best = {"match_id": mid, "team_id": tid, "opponent_id": m.away_team_id if tid == m.home_team_id else m.home_team_id,
                    "share": share, "backers": backers}
    rows_now, winners = await compute_standings(upto=number)
    prev_rounds = [x["number"] async for x in db.rounds.find({"number": {"$lt": number}}, {"number": 1})]
    rows_prev = (await compute_standings(upto=max(prev_rounds)))[0] if prev_rounds else []
    rank_now = next((x["rank"] for x in rows_now if x["user_id"] == user.id), None)
    rank_prev = next((x["rank"] for x in rows_prev if x["user_id"] == user.id), None)
    round_win = next((w for w in winners if w["number"] == number), None)
    return {"available": True, "number": r.number, "name": r.name, "correct": correct, "total": len(matches),
            "bonus": bonus, "points": correct + bonus, "tipped": len(mine), "best_pick": best,
            "rank": rank_now, "prev_rank": rank_prev if prev_rounds else None, "players": len(rows_now),
            "won_round": bool(round_win and any(w["user_id"] == user.id for w in round_win["winners"])),
            "round_top_points": round_win["points"] if round_win else 0}


# ---------------- Object storage (team logos) ----------------
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "tip-masters"
storage_key = None
logo_cache: dict = {}
MAX_LOGO_BYTES = 3 * 1024 * 1024
EXT_BY_TYPE = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg", "image/webp": "webp", "image/gif": "gif"}


def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    global storage_key
    for attempt in range(2):
        key = init_storage()
        resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                            headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
        if resp.status_code == 503 and attempt == 0:
            storage_key = None
            continue
        if resp.status_code == 402:
            raise HTTPException(402, "Storage credits exhausted. Please top up and try again later")
        resp.raise_for_status()
        return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


async def save_team_logo(team: Team, data: bytes, content_type: str) -> dict:
    ext = EXT_BY_TYPE.get(content_type.split(";")[0].lower())
    if not ext:
        raise HTTPException(400, "Logo must be a PNG, JPG, WEBP or GIF image")
    if len(data) > MAX_LOGO_BYTES:
        raise HTTPException(400, "Logo must be under 3 MB")
    res = await run_in_threadpool(put_object, f"{APP_NAME}/logos/{team.id}/{uuid.uuid4()}.{ext}", data, content_type)
    doc = await db.teams.find_one_and_update({"_id": oid(team.id)},
                                             {"$set": {"logo_path": res["path"]}, "$inc": {"logo_v": 1}},
                                             return_document=ReturnDocument.AFTER)
    return Team.from_mongo(doc).model_dump()


@api_router.post("/teams/{team_id}/logo")
async def upload_team_logo(team_id: str, file: UploadFile = File(...), _: User = Depends(admin_user)):
    team = Team.from_mongo(await db.teams.find_one({"_id": oid(team_id)}))
    if not team:
        raise HTTPException(404, "Team not found")
    return await save_team_logo(team, await file.read(), file.content_type or "")


@api_router.delete("/teams/{team_id}/logo")
async def remove_team_logo(team_id: str, _: User = Depends(admin_user)):
    doc = await db.teams.find_one_and_update({"_id": oid(team_id)}, {"$set": {"logo_path": None}, "$inc": {"logo_v": 1}},
                                             return_document=ReturnDocument.AFTER)
    if not doc:
        raise HTTPException(404, "Team not found")
    return Team.from_mongo(doc).model_dump()


@api_router.get("/teams/{team_id}/logo")
async def team_logo(team_id: str):
    """Public: club logos are public branding, served without auth so images render everywhere."""
    team = Team.from_mongo(await db.teams.find_one({"_id": oid(team_id)}))
    if not team or not team.logo_path:
        raise HTTPException(404, "No logo")
    if team.logo_path not in logo_cache:
        try:
            logo_cache[team.logo_path] = await run_in_threadpool(get_object, team.logo_path)
        except Exception:
            raise HTTPException(502, "Logo temporarily unavailable")
    data, ct = logo_cache[team.logo_path]
    return Response(content=data, media_type=ct, headers={"Cache-Control": "public, max-age=604800"})


# ---------------- Bowlslink sync (results + logos) ----------------
BOWLSLINK_API = "https://api.bowlslink.com.au/results-api"
SYNC_INTERVAL_SECONDS = 15 * 60


async def fetch_competition(cid: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{BOWLSLINK_API}/competition/{cid}/matches")
        r.raise_for_status()
        return r.json()


async def sync_fixtures(comp: dict, data: dict, team_by_ext: dict) -> tuple:
    """Adds newly announced finals matches (creating finals rounds by their Bowlslink label)
    and keeps kick-off times of undecided matches in step with Bowlslink."""
    added, moved = 0, 0
    items = sorted([i for i in data.get("include", []) if i.get("type") == "match"],
                   key=lambda m: (m.get("attributes") or {}).get("matchTimeUtc") or 0)
    for inc in items:
        a = inc.get("attributes") or {}
        kick = datetime.fromtimestamp(a["matchTimeUtc"], timezone.utc).isoformat() if a.get("matchTimeUtc") else None
        existing = Match.from_mongo(await db.matches.find_one({"ext_id": inc["id"]}))
        if existing:
            if kick and existing.kickoff != kick and not existing.winner_team_id:
                await db.matches.update_one({"_id": oid(existing.id)}, {"$set": {"kickoff": kick}})
                moved += 1
            continue
        is_final = a.get("isFinalsSeries") or (a.get("round") or 0) > REGULAR_ROUNDS
        if not is_final or a.get("isBye") or a.get("isTBD") or a.get("competitorOneTBD") or a.get("competitorTwoTBD"):
            continue
        refs = inc.get("includes") or {}
        home = team_by_ext.get((refs.get("competitorOne") or {}).get("id"))
        away = team_by_ext.get((refs.get("competitorTwo") or {}).get("id"))
        if not home or not away or home == away:
            continue  # teams not decided yet; picked up on a later sync
        label = (a.get("roundLabel") or f"Finals Round {a.get('round')}").strip()
        rnd = await db.rounds.find_one({"is_final": True, "name": label})
        if rnd:
            num = rnd["number"]
        else:
            last = await db.rounds.find_one(sort=[("number", -1)])
            num = (last["number"] if last else 0) + 1
            await db.rounds.insert_one(Round(number=num, name=label, is_final=True).to_mongo())
        order = await db.matches.count_documents({"round_number": num})
        await db.matches.insert_one(Match(round_number=num, order=order, home_team_id=home, away_team_id=away,
                                          kickoff=kick, group=comp.get("group"), ext_id=inc["id"]).to_mongo())
        added += 1
    return added, moved


sync_lock = asyncio.Lock()


async def sync_results() -> dict:
    """Imports finals + kick-off changes, then copies completed Bowlslink results onto our matches."""
    async with sync_lock:
        return await _sync_results()


async def _sync_results() -> dict:
    team_by_ext = {t["ext_id"]: str(t["_id"]) async for t in db.teams.find({"ext_id": {"$ne": None}})}
    updated, completed, finals_added, kickoffs_updated = 0, 0, 0, 0
    for comp in FIXTURE["competitions"]:
        data = await fetch_competition(comp["id"])
        added, moved = await sync_fixtures(comp, data, team_by_ext)
        finals_added += added
        kickoffs_updated += moved
        for inc in data.get("include", []):
            if inc.get("type") != "multiFormatResult":
                continue
            a = inc.get("attributes") or {}
            mid = ((inc.get("includes") or {}).get("match") or {}).get("id")
            if not mid or not (a.get("isCompleted") or a.get("isFinalized")):
                continue
            m = Match.from_mongo(await db.matches.find_one({"ext_id": mid}))
            if not m:
                continue
            completed += 1
            num = a.get("winnerCompetitorNumber")
            if num == 1:
                winner = m.home_team_id
            elif num == 2:
                winner = m.away_team_id
            elif a.get("winnerId") and team_by_ext.get(a["winnerId"]) in (m.home_team_id, m.away_team_id):
                winner = team_by_ext[a["winnerId"]]
            else:
                winner = "draw"
            if m.winner_team_id != winner:
                await db.matches.update_one({"_id": oid(m.id)}, {"$set": {"winner_team_id": winner}})
                updated += 1
    status = {"last_sync": datetime.now(timezone.utc).isoformat(), "updated": updated,
              "completed_found": completed, "finals_added": finals_added,
              "kickoffs_updated": kickoffs_updated, "error": None}
    await db.meta.update_one({"_id": "sync"}, {"$set": status}, upsert=True)
    return status


async def sync_loop():
    while True:
        try:
            s = await sync_results()
            if s["updated"] or s["finals_added"] or s["kickoffs_updated"]:
                logger.info(f"Bowlslink sync: {s}")
        except Exception as e:
            logger.warning(f"Bowlslink sync failed: {e}")
            await db.meta.update_one({"_id": "sync"}, {"$set": {"error": str(e)[:200],
                                     "last_attempt": datetime.now(timezone.utc).isoformat()}}, upsert=True)
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)


@api_router.get("/admin/sync-status")
async def sync_status(_: User = Depends(admin_user)):
    return await db.meta.find_one({"_id": "sync"}, {"_id": 0}) or {}


@api_router.post("/admin/sync-results")
async def sync_now(_: User = Depends(admin_user)):
    try:
        return await sync_results()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Couldn't reach Bowlslink: {e}")


@api_router.post("/admin/import-logos")
async def import_logos(_: User = Depends(admin_user)):
    """Downloads each club's current logo from Bowlslink and stores it in object storage."""
    logo_by_ext = {}
    try:
        for comp in FIXTURE["competitions"]:
            data = await fetch_competition(comp["id"])
            for inc in data.get("include", []):
                if inc.get("type") == "competitor" and (inc.get("attributes") or {}).get("logoUrl"):
                    logo_by_ext[inc["id"]] = inc["attributes"]["logoUrl"]
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Couldn't reach Bowlslink: {e}")
    imported, failed = 0, []
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        async for t in db.teams.find({"ext_id": {"$ne": None}}):
            team = Team.from_mongo(t)
            url = logo_by_ext.get(team.ext_id)
            if not url:
                continue
            try:
                r = await c.get(url)
                r.raise_for_status()
                await save_team_logo(team, r.content, r.headers.get("Content-Type", ""))
                imported += 1
            except Exception:
                failed.append(team.name)
    return {"imported": imported, "failed": failed}


@api_router.get("/admin/players")
async def list_players(_: User = Depends(admin_user)):
    out = []
    async for u in db.users.find({"role": {"$ne": "admin"}}).sort("created_at", 1):
        user = User.from_mongo(u)
        out.append({"id": user.id, "name": user.name, "email": user.email, "created_at": user.created_at,
                    "tips": await db.tips.count_documents({"user_id": user.id})})
    return out


@api_router.delete("/admin/players/{user_id}")
async def remove_player(user_id: str, _: User = Depends(admin_user)):
    """Removes a player and all their tips. Admin accounts can't be removed here."""
    user = User.from_mongo(await db.users.find_one({"_id": oid(user_id)}))
    if not user:
        raise HTTPException(404, "Player not found")
    if user.role == "admin":
        raise HTTPException(400, "Admin accounts can't be removed")
    await db.tips.delete_many({"user_id": user.id})
    await db.users.delete_one({"_id": oid(user.id)})
    return {"deleted": True}


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
