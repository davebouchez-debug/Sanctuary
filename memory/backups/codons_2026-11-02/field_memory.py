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

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-small-en-v1.5"
MODEL_DIR = str(Path(__file__).parent / "models")
_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(MODEL_NAME, cache_dir=MODEL_DIR)
    return _model


def mra_text(doc: Dict) -> str:
    themes = doc.get("themes") or []
    if isinstance(themes, list):
        themes = ", ".join(map(str, themes))
    return f"{doc.get('user_essence') or ''}\n{doc.get('ai_essence') or ''}\n{themes}".strip()


def _embed_sync(texts: List[str]) -> List[List[float]]:
    vecs = np.array(list(_get_model().embed(texts)), dtype=np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
    return vecs.tolist()


async def embed_texts(texts: List[str]) -> List[List[float]]:
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
            await db.permanent_mra.update_one({"_id": d["_id"]}, {"$set": {"embedding": v}})
    return len(docs)


_cache: Dict[str, tuple] = {}


async def _load(db, flt: Dict):
    key = repr(sorted(flt.items(), key=lambda kv: kv[0]))
    count = await db.permanent_mra.count_documents(flt)
    hit = _cache.get(key)
    if hit and hit[0] == count:
        return hit[1], hit[2], hit[3]
    await embed_missing(db, flt)
    docs = await db.permanent_mra.find(flt, {"_id": 0, "node_id": 1, "presence": 1, "user_essence": 1,
                                             "ai_essence": 1, "themes": 1, "quality": 1, "promoted_at": 1,
                                             "embedding": 1}).to_list(None)
    mat = np.array([d.pop("embedding") for d in docs], dtype=np.float32) if docs else None
    texts = [mra_text(d).lower() for d in docs]
    _cache[key] = (count, docs, mat, texts)
    return docs, mat, texts


async def rank_mra(db, flt: Dict, query: str, limit: int, projection: Dict = None) -> List[Dict]:
    """permanent_mra records matching flt, ranked by meaning against query."""
    docs, mat, texts = await _load(db, flt)
    if not docs:
        return []
    qv = await asyncio.to_thread(_query_vec_sync, query)
    stems = _stems(query)
    bonus = np.array([sum(st in t for st in stems) for t in texts], dtype=np.float32)
    order = np.argsort(-(mat @ qv + KEYWORD_WEIGHT * bonus))
    out, seen = [], set()
    for i in order:
        d = docs[int(i)]
        key = d.get("user_essence")
        if key in seen:
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
