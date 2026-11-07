"""RCC8 environment — the relational eligibility tested on 2026-11-06 (Condition B), made operational.

Candidates by full 384-d meaning; RCC8 relations in an 8-d compression of the same space
(phrases + this person's memories). An item is unreachable only when DC from the conversation.
Active only when RCC8_ENVIRONMENT=on, and only from the person's second message in a session.
Off = the existing retrieval, untouched."""
import asyncio
import contextvars
import hashlib
import logging
import os
import threading
from collections import OrderedDict

import numpy as np

from .relations import path_consistency_violations, table_self_check
from .regions import Cap, relation, cap_from_points, unit

logger = logging.getLogger(__name__)

PDIM = 8
WINDOW = 3
CAND = {"ph": 150, "mr": 80}
ARRANGE = [("NTPPi", "TPPi"), ("EQ",), ("PO",), ("TPP", "NTPP"), ("EC",)]

_TABLE_BAD = table_self_check()
if _TABLE_BAD:
    logger.error(f"[RCC8] composition table failed the converse law; environment stays off: {_TABLE_BAD[:2]}")


def enabled() -> bool:
    return os.environ.get("RCC8_ENVIRONMENT") == "on" and not _TABLE_BAD


# ── The conversation of this request ────────────────────────────────────────
_CONV = contextvars.ContextVar("rcc8_conversation", default=None)


def set_conversation(session: dict, current_text: str) -> None:
    """Called once per message turn. Inactive for the greeting and the first exchange."""
    prior = [m for m in (session or {}).get("messages") or [] if m.get("role") in ("user", "assistant") and m.get("content")]
    if not enabled() or not any(m["role"] == "user" for m in prior) or not (current_text or "").strip():
        _CONV.set(None)
        return
    _CONV.set({"texts": ([m["content"] for m in prior] + [current_text])[-WINDOW:],
               "user_id": (session or {}).get("user_id"), "vecs": None, "log": {}})


def active() -> bool:
    return _CONV.get() is not None


# ── Conversation vectors (each message embedded once, alone, as tested) ─────
_vec_cache: "OrderedDict[str, np.ndarray]" = OrderedDict()
_vec_lock = threading.Lock()


def _embed_window_sync(texts):
    from field_memory import _embed_sync, unpack
    out = []
    for t in texts:
        t = t[:1500]
        k = hashlib.sha1(t.encode()).hexdigest()
        with _vec_lock:
            v = _vec_cache.get(k)
        if v is None:
            v = unpack(_embed_sync([t])[0])
        with _vec_lock:
            _vec_cache[k] = v
            _vec_cache.move_to_end(k)
            while len(_vec_cache) > 512:
                _vec_cache.popitem(last=False)
        out.append(v)
    return out


async def _conv_vecs(st):
    if st["vecs"] is None:
        st["vecs"] = await asyncio.to_thread(_embed_window_sync, st["texts"])
    return st["vecs"]


# ── Geometry: one per person, rebuilt off the request path when the field changes ──
_geo: dict = {}
_building: set = set()


def _half_nn(pm, chunk=256):
    out = np.empty(len(pm), dtype=np.float32)
    for s in range(0, len(pm), chunk):
        a = np.arccos(np.clip(pm[s:s + chunk] @ pm.T, -1, 1))
        a[np.arange(a.shape[0]), np.arange(s, s + a.shape[0])] = 9
        out[s:s + chunk] = a.min(1) / 2
    return out


def _proj(g, m):
    q = (np.atleast_2d(m) - g["mu"]) @ g["V"].T
    q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-9)
    return q if np.ndim(m) == 2 else q[0]


def build_geometry(ph_mat, mr_mat, ph_docs=None, mr_docs=None, ph_texts=None, mr_texts=None, stamp=None):
    allm = ph_mat if mr_mat is None else np.vstack([ph_mat, mr_mat])
    g = {"mu": allm.mean(0), "stamp": stamp}
    # Principal axes from the 384×384 scatter (same axes as the tested SVD; a fraction of its memory).
    a64 = allm.astype(np.float64)
    scatter = a64.T @ a64 - len(a64) * np.outer(a64.mean(0), a64.mean(0))
    del a64
    g["V"] = np.ascontiguousarray(np.linalg.eigh(scatter)[1][:, ::-1][:, :PDIM].T, dtype=np.float32)
    del allm, scatter
    g["ph_mat"], g["ph_docs"], g["ph_texts"] = ph_mat, ph_docs, ph_texts
    g["ph_p"] = _proj(g, ph_mat)
    g["ph_rad"] = _half_nn(g["ph_p"])
    g["mr_mat"], g["mr_docs"], g["mr_texts"] = mr_mat, mr_docs, mr_texts
    if mr_mat is not None:
        g["mr_p"] = _proj(g, mr_mat)
        g["mr_rad"] = _half_nn(g["mr_p"])
    g["floor"] = float(np.median(g["ph_rad"]))
    g["eps"] = 0.1 * g["floor"]
    return g


async def _resolve(db, user_id):
    if not user_id:
        return "", None
    from user_aliases import resolve_user_aliases
    aliases = await resolve_user_aliases(db, user_id)
    return "|".join(sorted(aliases)), ({"$in": aliases} if len(aliases) > 1 else user_id)


async def _geometry(db, user_id):
    from field_memory import _load
    key, uid_query = await _resolve(db, user_id)
    ph_docs, ph_mat, ph_texts = await _load(db, {}, "field_phrases")
    if ph_mat is None:
        return None
    mr_docs, mr_mat, mr_texts = ([], None, [])
    if uid_query is not None:
        mr_docs, mr_mat, mr_texts = await _load(db, {"user_id": uid_query})
    stamp = (len(ph_docs), len(mr_docs))
    g = _geo.get(key)
    if g and g["stamp"] == stamp:
        return g
    args = (ph_mat, mr_mat, list(ph_docs), list(mr_docs) if mr_mat is not None else None,
            list(ph_texts), list(mr_texts) if mr_mat is not None else None, stamp)
    if g is None:
        g = _geo[key] = await asyncio.to_thread(build_geometry, *args)
        return g
    if key not in _building:
        _building.add(key)

        async def _rebuild():
            try:
                _geo[key] = await asyncio.to_thread(build_geometry, *args)
            except Exception as e:
                logger.warning(f"[RCC8] geometry rebuild failed: {e}")
            finally:
                _building.discard(key)
        asyncio.create_task(_rebuild())
    return g


# ── Selection: exactly the tested rule ─────────────────────────────────────
def select(g, kind, conv_vecs, limit, bonus=None, dedup=None):
    """Top candidates by full meaning → RCC8 relation to the conversation cap → drop DC → arrange."""
    mat, pm, rad = g[f"{kind}_mat"], g.get(f"{kind}_p"), g.get(f"{kind}_rad")
    if mat is None:
        return [], {}, None
    vecs = np.stack(conv_vecs[-WINDOW:])
    full_c = unit(vecs.mean(0))
    cc = cap_from_points("conversation", _proj(g, vecs), "conversation", pct=100, floor=g["floor"])
    sims = mat @ full_c
    if bonus is not None:
        sims = sims + bonus
    cand = np.argsort(-sims)[:CAND[kind]]
    groups = {grp: [] for grp in ARRANGE}
    rels = {}
    for i in cand:
        r = relation(Cap(str(i), pm[i], rad[i], "item"), cc, g["eps"])
        rels[int(i)] = r
        for grp in ARRANGE:
            if r in grp:
                groups[grp].append(int(i))
    picked = [i for grp in ARRANGE for i in groups[grp]]
    if dedup:
        seen, kept = set(), []
        for i in picked:
            k = dedup(i)
            if k not in seen:
                seen.add(k)
                kept.append(i)
        picked = kept
    return picked[:limit], rels, cc


def _consistency(g, kind, cc, picked):
    caps = [cc] + [Cap(f"{kind}:{i}", g[f"{kind}_p"][i], g[f"{kind}_rad"][i], "item") for i in picked[:8]]
    names = [c.name for c in caps]
    rel = {(a.name, b.name): relation(a, b, g["eps"]) for a in caps for b in caps if a is not b}
    v = path_consistency_violations(names, rel)
    if v:
        logger.warning(f"[RCC8] path-consistency violations: {len(v)} e.g. {v[:1]}")
    return len(v)


async def phrases(db, limit: int):
    """Field phrases for this turn, or None when the environment isn't active (caller uses existing path)."""
    st = _CONV.get()
    if st is None:
        return None
    g = await _geometry(db, st["user_id"])
    if g is None:
        return None
    picked, rels, cc = select(g, "ph", await _conv_vecs(st), limit)
    viol = _consistency(g, "ph", cc, picked)
    docs = [dict(g["ph_docs"][i], _rcc8=rels[i]) for i in picked]
    meta = {"reachable": sum(r != "DC" for r in rels.values()), "candidates": len(rels),
            "eps": round(g["eps"], 5), "floor": round(g["floor"], 5), "consistency_violations": viol,
            "memory_relations": st["log"].get("memory_relations")}
    return docs, meta


async def memories(db, user_id, query: str, limit: int, kw_weight: float):
    """Field memory for this turn, or None when not active. Keeps today's word bonus and duplicate removal."""
    st = _CONV.get()
    if st is None or not user_id:
        return None
    g = await _geometry(db, user_id)
    if g is None or g["mr_mat"] is None:
        return [] if g is not None else None
    from field_memory import _stems
    stems = _stems(query)
    bonus = kw_weight * np.array([sum(s in t for s in stems) for t in g["mr_texts"]], dtype=np.float32)
    picked, rels, _ = select(g, "mr", await _conv_vecs(st), limit, bonus=bonus,
                             dedup=lambda i: g["mr_docs"][i].get("user_essence"))
    st["log"]["memory_relations"] = [rels[i] for i in picked]
    return [dict(g["mr_docs"][i]) for i in picked]


def status() -> dict:
    return {"enabled": enabled(), "table_ok": not _TABLE_BAD, "geometries": len(_geo),
            "conversation_vectors_cached": len(_vec_cache)}
