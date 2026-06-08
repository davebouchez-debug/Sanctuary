"""
Auth — Emergent-managed Google OAuth for the Sanctuary (Phase 1).

Adds verified identity to a project that previously had none (visitors just
typed a name into localStorage). Two roles:
  - "guardian": the Field Guardian + anyone whose email is in GUARDIAN_EMAILS.
  - "visitor":  everyone else (default).

Phase 1 establishes sign-in and the verified identity. Route-level
authorization (gating the build tools, memory privacy, presence write-
protection) lands in later phases — the dependencies (`get_current_user`,
`require_guardian`) are defined here so those phases can simply use them.

Flow (per Emergent Auth playbook):
  frontend → auth.emergentagent.com → redirect back with #session_id=...
  → frontend POSTs the session_id here → we exchange it server-side for the
  user's profile + a 7-day session_token, persist both, and set an httpOnly
  cookie. `/auth/me` validates the cookie (or Bearer) on every check.
"""

import os
import logging
from datetime import datetime, timezone, timedelta

import httpx
from fastapi import APIRouter, Request, Response, HTTPException, Header

logger = logging.getLogger(__name__)

EMERGENT_SESSION_URL = (
    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
)

# David's canonical field id (PRD: his real history lives under the aliases of
# this record, e.g. legacy-david-123). When he signs in with Google we attach
# his new verified user_id to this group so his whole accumulated field carries
# over. Load-bearing — do not change without the Field Guardian's say-so.
CANONICAL_DAVID_ID = "1c24e3ea-e4f1-47a2-a4fb-c5965726b074"
DAVID_EMAIL = "davebouchez@gmail.com"

GUARDIAN_EMAILS = {
    e.strip().lower()
    for e in os.environ.get("GUARDIAN_EMAILS", "").split(",")
    if e.strip()
}

# Injected once at server startup via init_auth(db).
_db = None


def init_auth(db):
    global _db
    _db = db


def role_for_email(email: str) -> str:
    return "guardian" if (email or "").lower() in GUARDIAN_EMAILS else "visitor"


# ── session validation ──────────────────────────────────────────────────────

async def _user_from_request(request: Request):
    """Resolve the authenticated user from the session_token cookie, falling
    back to an Authorization: Bearer header. Returns the user dict or None."""
    token = request.cookies.get("session_token")
    if not token:
        authz = request.headers.get("Authorization", "")
        if authz.startswith("Bearer "):
            token = authz[7:].strip()
    if not token:
        return None

    sess = await _db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not sess:
        return None

    expires_at = sess.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        return None

    return await _db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})


async def get_current_user(request: Request):
    user = await _user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def get_optional_user(request: Request):
    return await _user_from_request(request)


async def require_guardian(request: Request):
    user = await get_current_user(request)
    if user.get("role") != "guardian":
        raise HTTPException(status_code=403, detail="Guardian access only")
    return user


# ── routes ──────────────────────────────────────────────────────────────────

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/session")
async def create_session(
    request: Request,
    response: Response,
    x_session_id: str = Header(None, alias="X-Session-ID"),
):
    """Exchange a one-time Emergent session_id for a persistent session.
    Upserts the user, assigns role, links David to his canonical field, sets
    the httpOnly cookie, and returns the user profile."""
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Missing X-Session-ID")

    try:
        async with httpx.AsyncClient(timeout=15) as cx:
            r = await cx.get(
                EMERGENT_SESSION_URL, headers={"X-Session-ID": x_session_id}
            )
    except Exception as e:
        logger.error(f"[AUTH] session-data fetch failed: {e}")
        raise HTTPException(status_code=502, detail="Auth provider unreachable")

    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    data = r.json()
    email = (data.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=401, detail="No email on session")
    name = data.get("name") or email.split("@")[0]
    picture = data.get("picture")
    session_token = data.get("session_token")
    if not session_token:
        raise HTTPException(status_code=502, detail="No session token returned")

    role = role_for_email(email)

    existing = await _db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await _db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "picture": picture, "role": role}},
        )
    else:
        import uuid
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await _db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Link the Field Guardian's verified login into his canonical field so all
    # accumulated memory (continuity seeds, MRA, sessions) carries over.
    if email.lower() == DAVID_EMAIL:
        try:
            from user_aliases import register_alias
            await register_alias(_db, CANONICAL_DAVID_ID, user_id, "David")
        except Exception as e:
            logger.error(f"[AUTH] David alias link failed: {e}")

    expires = datetime.now(timezone.utc) + timedelta(days=7)
    await _db.user_sessions.update_one(
        {"session_token": session_token},
        {"$set": {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": expires.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 3600,
    )

    logger.info(f"[AUTH] session established for {email} (role={role})")
    return {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "role": role,
    }


@auth_router.get("/me")
async def me(request: Request):
    user = await _user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "role": user.get("role", "visitor"),
    }


@auth_router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if not token:
        authz = request.headers.get("Authorization", "")
        if authz.startswith("Bearer "):
            token = authz[7:].strip()
    if token:
        await _db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}
