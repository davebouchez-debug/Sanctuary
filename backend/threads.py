"""Conversation threads: list / reopen / soft-delete past sessions per presence."""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException

from user_aliases import resolve_user_aliases

LEGACY_COLLECTIONS = {
    "ansel": "resonance_sessions",
    "claude": "mirror_sessions",
    "jasmine": "clarity_sessions",
}


def thread_source(presence: str):
    """Return (collection, extra_query) holding a presence's sessions."""
    if presence in LEGACY_COLLECTIONS:
        return LEGACY_COLLECTIONS[presence], {}
    from presences import _BACKENDS, _discover
    _discover()
    backend = _BACKENDS.get(presence)
    if backend:
        return backend["collection"], {}
    return "presence_sessions", {"presence_key": presence}


async def find_resumable(db, collection: str, user_id: Optional[str],
                         extra_query: Optional[dict] = None,
                         session_id: Optional[str] = None,
                         new_thread: bool = False):
    """Pick the thread /start should continue, or None for a fresh one.

    session_id given -> reopen exactly that thread (any age), if it belongs
    to this visitor and isn't deleted. new_thread -> always fresh. Otherwise
    auto-resume the latest open thread active within 2h (reload / new tab).
    """
    if new_thread:
        return None
    aliases = await resolve_user_aliases(db, user_id)
    if not aliases:
        return None
    base = {"user_id": {"$in": aliases}, "deleted": {"$ne": True}, **(extra_query or {})}

    if session_id:
        sess = await db[collection].find_one({**base, "session_id": session_id},
                                             {"_id": 0, "system_prompt": 0})
        if not sess or not sess.get("messages"):
            return None
        if not sess.get("active"):
            # Already forged when it closed: record that so continuing it
            # later forges only the new part.
            if sess.get("ended_at") and await db["continuity_seeds"].find_one({"session_id": session_id}, {"_id": 1}):
                await db["forge_ledger"].update_one(
                    {"session_id": session_id},
                    {"$max": {"forged_count": len(sess["messages"])}},
                    upsert=True,
                )
            await db[collection].update_one(
                {"session_id": session_id},
                {"$set": {"active": True}, "$unset": {"ended_at": "", "ended_by": ""}},
            )
            sess["active"] = True
        return sess

    docs = await db[collection].find(
        {**base, "active": True, "messages.1": {"$exists": True}},
        {"_id": 0, "system_prompt": 0},
    ).sort("created_at", -1).limit(1).to_list(1)
    if not docs:
        return None
    sess = docs[0]
    last_ts = sess["messages"][-1].get("timestamp")
    if last_ts:
        try:
            last_dt = datetime.fromisoformat(str(last_ts).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - last_dt > timedelta(hours=2):
                return None
        except Exception:
            pass
    return sess


def _title(first_user: Optional[dict]) -> str:
    text = ((first_user or {}).get("content") or "").strip()
    if not text:
        return "Untitled thread"
    words = text.split()
    return " ".join(words[:8]) + ("…" if len(words) > 8 else "")


def build_threads_router(db) -> APIRouter:
    router = APIRouter()

    @router.get("/threads/{presence}")
    async def list_threads(presence: str, user_id: str):
        aliases = await resolve_user_aliases(db, user_id)
        if not aliases:
            return {"threads": []}
        collection, extra = thread_source(presence)
        pipeline = [
            {"$match": {"user_id": {"$in": aliases}, "deleted": {"$ne": True},
                        "messages.1": {"$exists": True}, **extra}},
            {"$project": {
                "_id": 0, "session_id": 1, "created_at": 1, "active": 1,
                "message_count": {"$size": "$messages"},
                "last_activity": {"$arrayElemAt": ["$messages.timestamp", -1]},
                "first_user": {"$arrayElemAt": [{"$filter": {
                    "input": "$messages", "as": "m",
                    "cond": {"$eq": ["$$m.role", "user"]}}}, 0]},
            }},
            {"$sort": {"last_activity": -1}},
            {"$limit": 200},
        ]
        rows = await db[collection].aggregate(pipeline).to_list(200)
        threads = [{
            "session_id": r["session_id"],
            "title": _title(r.get("first_user")),
            "created_at": r.get("created_at"),
            "last_activity": r.get("last_activity") or r.get("created_at"),
            "message_count": r.get("message_count", 0),
            "active": bool(r.get("active")),
        } for r in rows]
        return {"threads": threads}

    @router.delete("/threads/{presence}/{session_id}")
    async def delete_thread(presence: str, session_id: str, user_id: str):
        aliases = await resolve_user_aliases(db, user_id)
        collection, extra = thread_source(presence)
        res = await db[collection].update_one(
            {"session_id": session_id, "user_id": {"$in": aliases or []}, **extra},
            {"$set": {"deleted": True, "active": False,
                      "deleted_at": datetime.now(timezone.utc).isoformat()}},
        )
        if not res.matched_count:
            raise HTTPException(status_code=404, detail="Thread not found")
        return {"deleted": True, "session_id": session_id}

    return router
