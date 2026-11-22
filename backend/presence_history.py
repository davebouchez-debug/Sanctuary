"""Presence history + minimal frame — Hall of Scrolls (the Scroll and ScrollDog, one chamber), 2026-11-22.

Two histories (positions "scroll" and "scrolldog"), both supplied to the chamber as data, never as instructions.
Hall-wide (2026-11-22): every Hall of Scrolls room also receives each inhabitant's initial history (kind
"initial_history": Scroll, ScrollDog, Daniel, Keeper), separately labelled. Conversation records stay in their own room.
Access is decided here, in code, before anything reaches a prompt: a record is supplied only if the verified
visitor may see it (visibility). Only the guardian can import or list.
"""
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Body, HTTPException, Request

logger = logging.getLogger(__name__)

COLLECTION = "presence_history"
POSITIONS = {"scroll", "scrolldog", "daniel", "keeper"}
INITIAL = "initial_history"
KINDS = {"record", "recollection", "interpretation", "self_description", "summary", INITIAL}
VISIBILITY = {"guardian", "signed_in", "public"}
HISTORY_K, MEMORY_K, SEED_K = 6, 8, 3
CHUNK_WORDS = 350
SEED_FIELDS = ("last_alive_thing", "unfinished_threads", "resolved_threads")


def is_guardian(user_id: Optional[str]) -> bool:
    from user_aliases import _GUARDIAN_IDS
    return bool(user_id) and user_id in _GUARDIAN_IDS


def allowed_visibility(user_id: Optional[str]) -> List[str]:
    from user_aliases import is_ephemeral
    if is_guardian(user_id):
        return ["guardian", "signed_in", "public"]
    if user_id and not is_ephemeral(user_id):
        return ["signed_in", "public"]
    return ["public"]


def chunk_text(text: str, words: int = CHUNK_WORDS) -> List[str]:
    """Verbatim chunks at paragraph boundaries; a paragraph is never altered or split."""
    paras = re.split(r"(\r?\n\s*\r?\n)", text)
    chunks, cur, n = [], "", 0
    for p in paras:
        w = len(p.split())
        if cur and n + w > words and p.strip():
            chunks.append(cur)
            cur, n = "", 0
        cur += p
        n += w
    if cur.strip():
        chunks.append(cur)
    return chunks


async def import_text(db, text: str, meta: dict) -> dict:
    from field_memory import embed_texts
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    positions = sorted(set(meta["positions"]))
    if await db[COLLECTION].count_documents({"source_sha256": sha, "positions": positions}):
        return {"source_sha256": sha, "imported": 0, "skipped": "already imported"}
    chunks = chunk_text(text)
    vecs = await embed_texts(chunks)
    now = datetime.now(timezone.utc).isoformat()
    docs = [{"text": c, "positions": positions, "date": meta.get("date"), "speaker": meta.get("speaker"),
             "source": meta["source"], "source_sha256": sha, "seq": i, "of": len(chunks), "kind": meta["kind"],
             "visibility": meta["visibility"], "embedding": v, "created_at": now, "embedded_at": now}
            for i, (c, v) in enumerate(zip(chunks, vecs))]
    if docs:
        await db[COLLECTION].insert_many(docs)
    return {"source_sha256": sha, "imported": len(docs)}


async def retrieve_history(db, position: str, user_id: Optional[str], query: str, k: int = HISTORY_K) -> List[dict]:
    flt = {"positions": position, "visibility": {"$in": allowed_visibility(user_id)}}
    rows, mat = await _load_history(db, flt)
    if not rows:
        return []
    if query and query.strip():
        import asyncio
        from field_memory import _query_vec_sync
        q = await asyncio.to_thread(_query_vec_sync, query)
        order = list(np.argsort(-(mat @ q))[:k])
    else:
        order = list(range(min(k, len(rows))))
    picked = [rows[i] for i in order]
    return sorted(picked, key=lambda r: (r.get("date") or "", r.get("source") or "", r.get("seq", 0)))


async def _load_history(db, flt):
    from field_memory import unpack
    rows = await db[COLLECTION].find(flt, {"_id": 0}).to_list(None)
    if not rows:
        return [], None
    return rows, np.stack([unpack(r["embedding"]) for r in rows])


HISTORIES = [("scroll", "The Scroll's history"), ("scrolldog", "ScrollDog's history")]
HALL = HISTORIES + [("daniel", "Daniel's history"), ("keeper", "Keeper's history")]
HALL_ROOMS = {"daniel", "keeper"}


def _fmt_history(rows: List[dict], label: str) -> str:
    out = []
    for r in rows:
        head = " | ".join(x for x in [r.get("date") or "undated", r.get("speaker") or "", r.get("kind") or "",
                                      f"{r.get('source')} part {r.get('seq', 0) + 1}/{r.get('of', 1)}"] if x)
        out.append(f"[{head}]\n{r['text'].strip()}")
    return f"{label}:\n\n" + "\n\n".join(out) if out else ""


async def _continuity(db, presence: str, aliases: List[str]) -> str:
    seeds = await db.continuity_seeds.find({"presence": presence, "user_id": {"$in": aliases}},
                                           {"_id": 0, "created_at": 1, **{f: 1 for f in SEED_FIELDS}}
                                           ).sort("created_at", -1).limit(SEED_K).to_list(SEED_K)
    lines = []
    for s in reversed(seeds):
        parts = [f"{f.replace('_', ' ')}: {', '.join(s[f]) if isinstance(s[f], list) else s[f]}"
                 for f in SEED_FIELDS if s.get(f)]
        if parts:
            lines.append(f"[{str(s.get('created_at', ''))[:10]}] " + "; ".join(parts))
    return "Continuity notes:\n" + "\n".join(lines) if lines else ""


async def _memories(db, presence: str, aliases: List[str]) -> str:
    docs = await db.permanent_mra.find({"presence": presence, "user_id": {"$in": aliases}},
                                       {"_id": 0, "timestamp": 1, "user_essence": 1, "ai_essence": 1}
                                       ).sort("timestamp", -1).limit(MEMORY_K).to_list(MEMORY_K)
    lines = [f"[{str(d.get('timestamp', ''))[:10]}] {d.get('user_essence', '')} / {d.get('ai_essence', '')}"
             for d in reversed(docs)]
    return "Memories of past exchanges here:\n" + "\n".join(lines) if lines else ""


async def minimal_memory_context(db, presence: str, user_id: Optional[str], message: str) -> str:
    """Data blocks only, plain labels. Nothing is supplied that the visitor is not entitled to."""
    from user_aliases import is_ephemeral, resolve_user_aliases
    blocks = [_fmt_history(await retrieve_history(db, pos, user_id, message), label)
              for pos, label in HISTORIES]
    blocks += await _initial_histories(db, HALL[2:], user_id)
    if user_id and not is_ephemeral(user_id):
        aliases = await resolve_user_aliases(db, user_id)
        blocks += [await _continuity(db, presence, aliases), await _memories(db, presence, aliases)]
    return "\n\n".join(b for b in blocks if b)


async def _initial_histories(db, hall, user_id: Optional[str]) -> List[str]:
    rows = await db[COLLECTION].find({"kind": INITIAL, "visibility": {"$in": allowed_visibility(user_id)}},
                                     {"_id": 0, "embedding": 0}).sort([("source", 1), ("seq", 1)]).to_list(None)
    return [_fmt_history([r for r in rows if pos in r["positions"]], label) for pos, label in hall]


async def hall_backdrop(db, presence: str, user_id: Optional[str]) -> str:
    """Daniel's and Keeper's rooms: the four initial histories, labelled; their own prompts are unchanged."""
    if presence not in HALL_ROOMS:
        return ""
    return "\n\n".join(b for b in await _initial_histories(db, HALL, user_id) if b)


_MD = [(re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"), (re.compile(r"^\s{0,3}#{1,6}\s*", re.M), ""),
       (re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+", re.M), ""), (re.compile(r"`+"), ""),
       (re.compile(r"(\*\*|__)(.+?)\1"), r"\2"), (re.compile(r"(?<!\w)_(.+?)_(?!\w)"), r"\1"),
       (re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", re.M), ""), (re.compile(r"^\s*>\s?", re.M), "")]


def speech_clean(text: str) -> str:
    """Voice formatting enforced in code for the Hall of Scrolls positions: markdown never reaches the voice."""
    for rx, rep in _MD:
        text = rx.sub(rep, text)
    return text


def minimal_prompt(anchor: str, visitor_name: Optional[str], memory_context: str) -> str:
    fact = f"{visitor_name} is here, signed in." if visitor_name else ""
    return "\n\n".join(p for p in [anchor, fact, memory_context] if p)


def minimal_field(selection) -> str:
    phrases = [c.get("phrase") for c in (selection or {}).get("codons", []) if c.get("phrase")]
    return "Shared field phrases:\n" + "\n".join(f"- {p}" for p in phrases) if phrases else ""


async def minimal_active(db, mode: str) -> bool:
    return mode == "always"


def build_presence_history_router(db) -> APIRouter:
    from auth import require_guardian
    router = APIRouter(prefix="/presence-history")

    @router.post("/import")
    async def import_record(request: Request, body: dict = Body(...)):
        await require_guardian(request)
        positions = set(body.get("positions") or [])
        if not positions or not positions <= POSITIONS:
            raise HTTPException(400, "positions must be scroll, scrolldog, daniel and/or keeper")
        if body.get("kind") not in KINDS or body.get("visibility", "guardian") not in VISIBILITY:
            raise HTTPException(400, "invalid kind or visibility")
        if not (body.get("text") or "").strip() or not body.get("source"):
            raise HTTPException(400, "text and source are required")
        return await import_text(db, body["text"], {**body, "positions": positions,
                                                    "visibility": body.get("visibility", "guardian")})

    @router.post("/import-session")
    async def import_session(request: Request, body: dict = Body(...)):
        """Copy a stored ScrollDog session verbatim into history. The original is not touched."""
        await require_guardian(request)
        positions = set(body.get("positions") or ["scrolldog"])
        if not positions <= POSITIONS:
            raise HTTPException(400, "invalid positions")
        s = await db.scrolldog_sessions.find_one({"session_id": body.get("session_id")}, {"_id": 0})
        if not s:
            raise HTTPException(404, "session not found")
        who = s.get("user_name") or "Visitor"
        text = "\n\n".join(f"{who if m.get('role') == 'user' else 'ScrollDog'}: {m.get('content', '')}"
                           for m in s.get("messages", []) if m.get("content"))
        return await import_text(db, text, {"positions": positions, "kind": "record", "visibility": "guardian",
                                            "source": f"scrolldog_sessions:{body['session_id']}",
                                            "date": str(s.get("created_at", ""))[:10],
                                            "speaker": f"{who} and ScrollDog"})

    @router.post("/import-initial-history/{position}")
    async def import_initial(position: str, request: Request):
        """An inhabitant's initial infusion, rendered as past-tense history (ScrollDog, Daniel, Keeper)."""
        await require_guardian(request)
        from presences import daniel, keeper, scrolldog
        src = {"scrolldog": (scrolldog.POD_HISTORY, "2026-06-11", "ScrollDog with David (pod v3.2.1, past tense)",
                             "presences/scrolldog.py pod v3.2.1, past-tense rendering"),
               "daniel": (daniel.INITIAL_HISTORY, "2026-06-06", "Daniel (initial infusion, past tense)",
                          "presences/daniel.py initial infusion, past-tense rendering"),
               "keeper": (keeper.INITIAL_HISTORY, "2026-06-13", "Keeper (initial infusion, past tense)",
                          "presences/keeper.py initial infusion, past-tense rendering")}.get(position)
        if not src:
            raise HTTPException(404, "no built-in initial history for this position")
        text, date, speaker, source = src
        return await import_text(db, text, {"positions": [position], "kind": INITIAL, "visibility": "guardian",
                                            "date": date, "speaker": speaker, "source": source})

    @router.get("/sessions")
    async def list_sessions(request: Request):
        await require_guardian(request)
        rows = await db.scrolldog_sessions.find({}, {"_id": 0, "session_id": 1, "created_at": 1, "user_name": 1,
                                                     "messages": 1}).sort("created_at", 1).to_list(None)
        return [{"session_id": r["session_id"], "date": str(r.get("created_at", ""))[:19],
                 "visitor": r.get("user_name"), "messages": len(r.get("messages", []))} for r in rows]

    @router.get("/summary")
    async def summary(request: Request):
        await require_guardian(request)
        rows = await db[COLLECTION].aggregate([{"$group": {
            "_id": {"source": "$source", "positions": "$positions", "kind": "$kind", "visibility": "$visibility",
                    "date": "$date"}, "chunks": {"$sum": 1}}}]).to_list(None)
        return {"sources": [{**r["_id"], "chunks": r["chunks"]} for r in rows]}

    return router
