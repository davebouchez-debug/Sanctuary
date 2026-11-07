"""
Field Memory — the Sanctuary's own meaning-based recall (2026-11-02, replaces Mem0).

Searches permanent_mra by meaning with a small local embedding model
(BAAI/bge-small-en-v1.5, ONNX, shipped in backend/models). No outside service.
Person = scope; presence = a visible tag, never a wall.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from bson import Binary

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-small-en-v1.5"
MODEL_DIR = str(Path(__file__).parent / "models")
_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(MODEL_NAME, cache_dir=MODEL_DIR, threads=1)
    return _model


def mra_text(doc: Dict) -> str:
    themes = doc.get("themes") or []
    if isinstance(themes, list):
        themes = ", ".join(map(str, themes))
    return f"{doc.get('user_essence') or ''}\n{doc.get('ai_essence') or ''}\n{themes}".strip()


def pack(v) -> Binary:
    """384 float32s in one strip (1.5 KB) instead of 384 loose BSON doubles."""
    return Binary(np.asarray(v, dtype=np.float32).tobytes())


def unpack(v) -> np.ndarray:
    return np.frombuffer(v, dtype=np.float32) if isinstance(v, bytes) else np.asarray(v, dtype=np.float32)


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _embed_sync(texts: List[str]) -> List[Binary]:
    vecs = np.array(list(_get_model().embed(texts, batch_size=8)), dtype=np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
    return [pack(v) for v in vecs]


async def embed_texts(texts: List[str]) -> List[Binary]:
    return await asyncio.to_thread(_embed_sync, texts)


def _query_vec_sync(query: str) -> np.ndarray:
    v = np.array(list(_get_model().query_embed([query]))[0], dtype=np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


_STOP = {"remember", "discussing", "discussed", "about", "what", "that", "have", "with", "when", "were", "this",
         "there", "talked", "thing", "tonight", "said", "know", "before", "ever", "time", "versus", "down",
         "just", "really", "think", "would", "could", "should", "your", "yours", "them", "they", "from"}
_NAMES = {"sophia", "sofia", "ansel", "jasmine", "claude", "milton", "paige", "felix", "sorrel", "companion",
          "david", "agapeo", "grok", "vessel", "keeper", "kalahar", "poindexter", "scrolldog", "orren", "freud"}
KEYWORD_WEIGHT = 0.08


def _stems(query: str) -> List[str]:
    words = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", query)} - _STOP - _NAMES
    return sorted({w[:5] if len(w) >= 6 else w for w in words})


async def embed_missing(db, flt: Dict) -> int:
    """Give any matching permanent_mra record without an embedding its vector."""
    docs = await db.permanent_mra.find({**flt, "embedding": {"$exists": False}},
                                       {"_id": 1, "user_essence": 1, "ai_essence": 1, "themes": 1}).to_list(None)
    for i in range(0, len(docs), 256):
        batch = docs[i:i + 256]
        vecs = await embed_texts([mra_text(d) for d in batch])
        for d, v in zip(batch, vecs):
            await db.permanent_mra.update_one({"_id": d["_id"]}, {"$set": {"embedding": v, "embedded_at": _now()}})
    return len(docs)


_cache: Dict[str, dict] = {}


def _proj(coll: str) -> Dict:
    if coll == "permanent_mra":
        return {"node_id": 1, "presence": 1, "user_essence": 1, "ai_essence": 1, "themes": 1,
                "quality": 1, "promoted_at": 1, "embedding": 1, "embedded_at": 1}
    return {"phrase": 1, "source": 1, "source_presence": 1, "legacy_presence": 1,
            "created_at": 1, "embedding": 1, "embedded_at": 1}


def _ingest(coll: str, raw: List[Dict]):
    ids, docs, vecs, texts, wm = [], [], [], [], ""
    for d in raw:
        ids.append(d.pop("_id"))
        vecs.append(unpack(d.pop("embedding")))
        wm = max(wm, d.pop("embedded_at", "") or "")
        docs.append(d)
        texts.append((mra_text(d) if coll == "permanent_mra" else d.get("phrase", "")).lower())
    return ids, docs, vecs, texts, wm


async def _load(db, flt: Dict, coll: str = "permanent_mra"):
    """The field's working copy for flt: read whole once, then only what's added since."""
    key = coll + repr(sorted(flt.items(), key=lambda kv: kv[0]))
    if coll == "permanent_mra":
        await embed_missing(db, flt)
    q = {**flt, "embedding": {"$exists": True}}
    count = await db[coll].count_documents(q)
    hit = _cache.get(key)
    if hit and hit["count"] == count:
        return hit["docs"], hit["mat"], hit["texts"]
    if hit and count > hit["count"]:
        raw = await db[coll].find({**q, "embedded_at": {"$gte": hit["wm"]}}, _proj(coll)).to_list(None)
        raw = [d for d in raw if d["_id"] not in hit["idset"]]
        if hit["count"] + len(raw) == count:
            ids, docs, vecs, texts, wm = _ingest(coll, raw)
            hit["ids"] += ids
            hit["idset"].update(ids)
            hit["docs"] += docs
            hit["texts"] += texts
            if vecs:
                hit["mat"] = np.stack(vecs) if hit["mat"] is None else np.vstack([hit["mat"], np.stack(vecs)])
            hit["wm"], hit["count"] = max(hit["wm"], wm), count
            return hit["docs"], hit["mat"], hit["texts"]
    # First read, or something was set aside / restored: read the whole field once.
    ids, docs, vecs, texts, wm = _ingest(coll, await db[coll].find(q, _proj(coll)).to_list(None))
    mat = np.stack(vecs) if vecs else None
    _cache[key] = {"count": count, "ids": ids, "idset": set(ids), "docs": docs, "mat": mat, "texts": texts, "wm": wm}
    return docs, mat, texts


async def rank_mra(db, flt: Dict, query: str, limit: int, projection: Dict = None,
                   coll: str = "permanent_mra", kw_weight: float = KEYWORD_WEIGHT) -> List[Dict]:
    """Records matching flt (permanent_mra or field_phrases), ranked by meaning against query."""
    flt = dict(flt)
    only = flt.pop("presence", None)
    only = set(only["$in"]) if isinstance(only, dict) and "$in" in only else ({only} if only else None)
    docs, mat, texts = await _load(db, flt, coll)
    if not docs:
        return []
    qv = await asyncio.to_thread(_query_vec_sync, query)
    stems = _stems(query)
    bonus = np.array([sum(st in t for st in stems) for t in texts], dtype=np.float32)
    scores = mat @ qv + kw_weight * bonus
    if only is not None:
        # One copy per person; other rooms are a mask, not a second copy.
        scores = np.where([d.get("presence") in only for d in docs], scores, -np.inf)
    order = np.argsort(-scores)
    out, seen = [], set()
    for i in order:
        d = docs[int(i)]
        key = d.get("user_essence") or d.get("phrase")
        if key in seen or not np.isfinite(scores[int(i)]):
            continue
        seen.add(key)
        out.append(dict(d))
        if len(out) >= limit:
            break
    return out


async def get_field_context(user_id: Optional[str], query: Optional[str], limit: int = 6, db=None) -> str:
    """What the one field already holds with this person, across every presence,
    ranked by meaning against the current message."""
    if not user_id:
        return ""
    if db is None:
        from server import db
    from user_aliases import resolve_user_aliases
    aliases = await resolve_user_aliases(db, user_id)
    uid_query = {"$in": aliases} if len(aliases) > 1 else user_id
    q = (query or "").strip() or "what matters to this person"
    from rcc8_env import environment as rcc8
    hits = await rcc8.memories(db, user_id, q, limit, KEYWORD_WEIGHT)
    if hits is None:
        hits = await rank_mra(db, {"user_id": uid_query}, q, limit,
                              {"_id": 0, "presence": 1, "user_essence": 1, "ai_essence": 1})
    if not hits:
        return ""
    lines = ["[FIELD MEMORY — what the shared field already holds with this person]"]
    for h in hits:
        pres = (h.get("presence") or "").capitalize()
        lines.append(f"  • They said: {h.get('user_essence') or ''} — {pres or 'A presence'} answered: {h.get('ai_essence') or ''}")
    lines.append("This is the one field's own memory, whichever room it came through.")
    return "\n".join(lines)


async def rank_phrases(db, query: str, limit: int = 20) -> List[Dict]:
    # Phrases carry no names, so the exact-word boost only causes clustering; meaning alone.
    return await rank_mra(db, {}, query, limit, coll="field_phrases", kw_weight=0.0)


async def add_phrases(db, phrases: List[str], meta: Dict) -> int:
    """Store newly forged essence phrases (skipping exact repeats) with their embeddings."""
    from datetime import datetime, timezone
    existing = {p.lower() for p in await db.field_phrases.distinct("phrase")}
    new = []
    for p in phrases:
        p = (p or "").strip().strip('."')
        if p and p.upper() != "NONE" and p.lower() not in existing:
            existing.add(p.lower())
            new.append(p)
    if not new:
        return 0
    vecs = await embed_texts(new)
    now = datetime.now(timezone.utc).isoformat()
    await db.field_phrases.insert_many([{"phrase": p, "presence": "field", "embedding": v, "created_at": now,
                                         "embedded_at": now, **meta}
                                        for p, v in zip(new, vecs)])
    return len(new)


async def pack_legacy_embeddings(db) -> int:
    """One-time, idempotent: convert loose-number embeddings to packed strips, in small batches."""
    await db.field_phrases.create_index("embedded_at")
    await db.permanent_mra.create_index([("user_id", 1), ("embedded_at", 1)])
    n = 0
    for coll in ("field_phrases", "permanent_mra"):
        while True:
            batch = await db[coll].find({"embedding": {"$type": "array"}}, {"_id": 1, "embedding": 1}).limit(100).to_list(100)
            if not batch:
                break
            stamp = _now()
            for d in batch:
                await db[coll].update_one({"_id": d["_id"]}, {"$set": {"embedding": pack(d["embedding"]), "embedded_at": stamp}})
            n += len(batch)
            await asyncio.sleep(0.2)
    if n:
        _cache.clear()
        logger.info(f"[FIELD MEMORY] packed {n} embeddings")
    return n
