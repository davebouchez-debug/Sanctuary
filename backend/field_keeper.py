"""Field Keeper — guardian-only search and set-aside/restore for what the field holds."""
import re
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from auth import require_guardian
from user_aliases import person_name
from field_memory import mra_text, _query_vec_sync, _stems, embed_missing, unpack, KEYWORD_WEIGHT

KINDS = {
    "phrases": {"coll": "field_phrases", "fields": ["phrase"]},
    "memories": {"coll": "permanent_mra", "fields": ["user_essence", "ai_essence"]},
    "continuity": {"coll": "continuity_seeds",
                   "fields": ["field_state", "emotional_texture", "relational_dynamic", "last_alive_thing",
                              "spiral_position", "unfinished_threads", "resolved_threads"]},
}
REMOVED = "field_keeper_removed"


def _oid(v: str):
    return ObjectId(v) if ObjectId.is_valid(v) else v


def _item(kind: str, d: dict) -> dict:
    if kind == "phrases":
        text = d.get("phrase", "")
    elif kind == "memories":
        text = f"They said: {d.get('user_essence') or ''}\nThe presence answered: {d.get('ai_essence') or ''}"
    else:
        text = "\n".join(f"{k.replace('_', ' ').capitalize()}: {d[k]}" for k in KINDS[kind]["fields"]
                         if d.get(k) not in (None, "", "[]", []))
    return {
        "id": str(d["_id"]), "kind": kind, "text": text,
        "presence": d.get("source_presence") or d.get("presence") or "",
        "session": d.get("source_session") or d.get("source_session_id") or d.get("session_id") or "",
        "person": person_name(d["user_id"]) if d.get("user_id") else "",
        "date": str(d.get("created_at") or d.get("promoted_at") or d.get("timestamp") or "")[:16].replace("T", " "),
        "source": d.get("source") or d.get("speaker_identity") or "",
    }


class ItemRef(BaseModel):
    kind: str
    id: str


class RemovedRef(BaseModel):
    id: str


def build_field_keeper_router(db) -> APIRouter:
    router = APIRouter(prefix="/field-keeper")

    @router.get("/search")
    async def search(request: Request, kind: str, q: str = "", mode: str = "words", limit: int = 60):
        await require_guardian(request)
        if kind not in KINDS:
            raise HTTPException(400, "Unknown kind")
        spec, q = KINDS[kind], q.strip()
        coll = db[spec["coll"]]
        limit = max(1, min(limit, 200))
        if q and mode == "meaning" and kind != "continuity":
            if kind == "memories":
                await embed_missing(db, {})
            docs = await coll.find({"embedding": {"$exists": True}}).to_list(None)
            if not docs:
                return {"items": [], "total": 0}
            mat = np.stack([unpack(d["embedding"]) for d in docs])
            scores = mat @ _query_vec_sync(q)
            if kind == "memories":
                stems = _stems(q)
                scores = scores + KEYWORD_WEIGHT * np.array(
                    [sum(st in mra_text(d).lower() for st in stems) for d in docs], dtype=np.float32)
            top = np.argsort(-scores)[:limit]
            return {"items": [_item(kind, docs[int(i)]) for i in top], "total": len(docs)}
        flt = {}
        if q:
            rx = {"$regex": re.escape(q), "$options": "i"}
            flt = {"$or": [{f: rx} for f in spec["fields"]]}
        total = await coll.count_documents(flt)
        docs = await coll.find(flt, {"embedding": 0}).sort("_id", -1).limit(limit).to_list(None)
        return {"items": [_item(kind, d) for d in docs], "total": total}

    @router.post("/remove")
    async def remove(ref: ItemRef, request: Request):
        await require_guardian(request)
        if ref.kind not in KINDS:
            raise HTTPException(400, "Unknown kind")
        coll = db[KINDS[ref.kind]["coll"]]
        doc = await coll.find_one({"_id": _oid(ref.id)})
        if not doc:
            raise HTTPException(404, "Not found")
        await db[REMOVED].insert_one({"kind": ref.kind, "collection": KINDS[ref.kind]["coll"], "original": doc,
                                      "removed_at": datetime.now(timezone.utc).isoformat()})
        await coll.delete_one({"_id": doc["_id"]})
        return {"ok": True}

    @router.get("/removed")
    async def removed(request: Request):
        await require_guardian(request)
        rows = await db[REMOVED].find().sort("removed_at", -1).to_list(500)
        return {"items": [{**_item(r["kind"], r["original"]), "removed_id": str(r["_id"]),
                           "removed_at": r["removed_at"][:16].replace("T", " ")} for r in rows]}

    @router.post("/restore")
    async def restore(ref: RemovedRef, request: Request):
        await require_guardian(request)
        r = await db[REMOVED].find_one({"_id": _oid(ref.id)})
        if not r:
            raise HTTPException(404, "Not found")
        if not await db[r["collection"]].find_one({"_id": r["original"]["_id"]}):
            await db[r["collection"]].insert_one(r["original"])
        await db[REMOVED].delete_one({"_id": r["_id"]})
        return {"ok": True}

    return router
