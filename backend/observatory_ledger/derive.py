"""Observatory ledger derivation: read-only over Sanctuary records, append-only ledger.

Never imports Sanctuary prompt/memory/model modules and never calls retrieval
functions (they write access traces). All Sanctuary reads are plain find().
"""
import asyncio
import json
import logging
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from pymongo.errors import DuplicateKeyError

from . import DERIVATION_VERSION, NORM_VERSION, ENUM_CAP, PROFILES, PRODUCTION_VERSIONS
from .measure import enumerate_resolutions, per_type, text_layer, transform
from .recover import canonical_hash, h, norm, recover

logger = logging.getLogger("observatory_ledger")

SETTLE_AFTER = timedelta(hours=24)
LOCK_TTL = timedelta(minutes=15)
UNAVAILABLE_EVIDENCE = [
    "model inputs before the first provenance record (2026-08-21)",
    "context of assistant turns without provenance (counted, not inspected)",
    "record identity for Mem0 / session cache / council / bio / field pointer (text-only)",
    "historical versions of stored records (drift detectable, prior states unrecoverable)",
    "same-visitor linkage across browsers for visitors without aliases",
    "what the model attended to",
]


class Ledger:
    def __init__(self, db, prefix: str = "obs_ledger_"):
        self.db = db
        self.runs = db[f"{prefix}runs"]
        self.entries = db[f"{prefix}engagements"]
        self.state = db[f"{prefix}state"]

    async def ensure_indexes(self):
        await self.entries.create_index([("derivation_version", 1), ("source.provenance_oid", 1)], unique=True)
        await self.entries.create_index("entry_id", unique=True)
        chain_key = [("derivation_version", 1), ("chronology.presence", 1), ("chronology.ordinal", 1)]
        for name, i in (await self.entries.index_information()).items():
            if i["key"] == chain_key and not i.get("unique"):
                await self.entries.drop_index(name)  # upgrade: one chain position per (version, presence)
        await self.entries.create_index(chain_key, unique=True)


def parse_ts(v) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _code_commit() -> str:
    try:
        return subprocess.run(["git", "-C", "/app", "rev-parse", "HEAD"], capture_output=True,
                              text=True, timeout=5).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------- indexes
async def build_indexes(db) -> dict:
    seed_by, seed_fp, seed_meta = {}, {}, {}
    async for s in db.continuity_seeds.find({}, {"field_state": 1, "session_id": 1, "created_at": 1, "presence": 1}):
        sid = str(s["_id"])
        fs = norm(s.get("field_state"))
        if fs:
            seed_by.setdefault(fs, []).append(sid)
        seed_fp[sid] = canonical_hash({k: s.get(k) for k in ("field_state", "session_id", "created_at", "presence")})
        seed_meta[sid] = {"source_session_id": s.get("session_id"), "created_at": str(s.get("created_at"))}
    mra_by, mra_fp, mra_meta = {}, {}, {}
    async for m in db.permanent_mra.find({}, {"node_id": 1, "user_essence": 1, "ai_essence": 1, "quality": 1,
                                              "promoted_at": 1, "source_session_id": 1}):
        nid = m.get("node_id")
        if not nid:
            continue
        mra_by.setdefault((norm(m.get("user_essence")), norm(m.get("ai_essence"))), []).append(nid)
        mra_fp[nid] = canonical_hash({k: m.get(k) for k in ("user_essence", "ai_essence", "quality", "promoted_at", "source_session_id")})
        mra_meta[nid] = {"source_session_id": m.get("source_session_id"), "created_at": str(m.get("promoted_at"))}
    codon_by = {}
    async for c in db.living_codons.find({}, {"name": 1, "core_move": 1, "target_angle": 1, "triadic_zone": 1,
                                              "angle_backfilled_at": 1, "presence": 1}):
        codon_by.setdefault(c.get("name"), []).append({
            "id": str(c["_id"]), "target_angle": c.get("target_angle"), "presence": c.get("presence"),
            "fp": canonical_hash({k: c.get(k) for k in ("name", "core_move", "target_angle", "triadic_zone", "angle_backfilled_at")}),
        })
    aliases = {}
    async for a in db.user_aliases.find({}, {"canonical_id": 1, "aliases": 1}):
        for x in (a.get("aliases") or []) + [a.get("canonical_id")]:
            if x:
                aliases[x] = a["canonical_id"]
    return {"seed_by_field_state": seed_by, "seed_fp": seed_fp, "seed_meta": seed_meta,
            "mra_by_pair": mra_by, "mra_fp": mra_fp, "mra_meta": mra_meta,
            "codon_by_name": codon_by, "aliases": aliases}


async def current_fingerprint(db, element: str) -> Optional[str]:
    typ, key = element.split(":", 1)
    if typ == "seed":
        from bson import ObjectId
        s = await db.continuity_seeds.find_one({"_id": ObjectId(key)}, {"field_state": 1, "session_id": 1, "created_at": 1, "presence": 1})
        return canonical_hash({k: s.get(k) for k in ("field_state", "session_id", "created_at", "presence")}) if s else None
    if typ == "mra":
        m = await db.permanent_mra.find_one({"node_id": key}, {"user_essence": 1, "ai_essence": 1, "quality": 1, "promoted_at": 1, "source_session_id": 1})
        return canonical_hash({k: m.get(k) for k in ("user_essence", "ai_essence", "quality", "promoted_at", "source_session_id")}) if m else None
    if typ == "codon":
        from bson import ObjectId
        c = await db.living_codons.find_one({"_id": ObjectId(key)}, {"name": 1, "core_move": 1, "target_angle": 1, "triadic_zone": 1, "angle_backfilled_at": 1})
        return canonical_hash({k: c.get(k) for k in ("name", "core_move", "target_angle", "triadic_zone", "angle_backfilled_at")}) if c else None
    return None


# ---------------------------------------------------------------- sessions
async def load_sessions(db, prov_presence_by_session: Dict[str, str]) -> Dict[str, dict]:
    """session_id -> {presence, user_id, ended, messages[{id, role, ts, content?}]}"""
    out = {}
    cols = [c for c in await db.list_collection_names() if c.endswith("_sessions") and c != "user_sessions"]
    for c in cols:
        stem = c[: -len("_sessions")]
        async for s in db[c].find({}, {"session_id": 1, "user_id": 1, "active": 1, "ended_at": 1, "presence_key": 1,
                                       "messages.id": 1, "messages.role": 1, "messages.timestamp": 1, "messages.content": 1}):
            sid = s.get("session_id")
            if not sid:
                continue
            presence = prov_presence_by_session.get(sid) or s.get("presence_key") or stem
            msgs = [{"id": m.get("id"), "role": m.get("role"), "ts": parse_ts(m.get("timestamp")),
                     "content": m.get("content") if sid in prov_presence_by_session else None}
                    for m in (s.get("messages") or [])]
            out[sid] = {"presence": presence, "user_id": s.get("user_id"), "collection": c,
                        "ended": (s.get("active") is False) or bool(s.get("ended_at")), "messages": msgs}
    # collections whose stem differs from the captured presence (e.g. resonance -> ansel)
    stem_map = {}
    for sid, p in prov_presence_by_session.items():
        if sid in out:
            stem_map.setdefault(out[sid]["collection"], set()).add(p)
    for sid, s in out.items():
        if sid not in prov_presence_by_session and s["collection"] != "presence_sessions":
            ps = stem_map.get(s["collection"])
            if ps and len(ps) == 1:
                s["presence"] = next(iter(ps))
    return out


def participation(prov: dict, sess: Optional[dict], now: datetime):
    """(participation dict, settled bool)."""
    ts = parse_ts(prov.get("timestamp"))
    msgs = (sess or {}).get("messages") or []
    i = next((k for k, m in enumerate(msgs) if m["id"] and m["id"] == prov.get("turn_id")), None)
    part = {"response_msg_id": None, "match": "unmatched", "response_ts": None, "response_len_chars": None,
            "prompting_user_msg_id": None, "next_user_msg_id": None, "next_user_delay_s": None, "end_state": None}
    nxt = None
    if i is not None:
        r = msgs[i]
        part.update(response_msg_id=r["id"], match="matched", response_ts=r["ts"].isoformat() if r["ts"] else None,
                    response_len_chars=len(r["content"] or "") if r["content"] is not None else None)
        prev_user = next((m for m in reversed(msgs[:i]) if m["role"] == "user"), None)
        part["prompting_user_msg_id"] = prev_user["id"] if prev_user else None
        nxt = next((m for m in msgs[i + 1:] if m["role"] == "user"), None)
    if nxt:
        part["next_user_msg_id"] = nxt["id"]
        rts = msgs[i]["ts"]
        part["next_user_delay_s"] = round((nxt["ts"] - rts).total_seconds(), 3) if (nxt["ts"] and rts) else None
        part["end_state"] = "continued"
        return part, True
    if sess and sess["ended"]:
        part["end_state"] = "session-ended"
        return part, True
    if ts and now - ts > SETTLE_AFTER:
        part["end_state"] = "unknown"
        return part, True
    return part, False


# ---------------------------------------------------------------- scopes
def _scope_key(scope: str, e: dict):
    return {"S1": e["session_id"], "S2": e["presence"], "S3": e["visitor"]}[scope]


def uncaptured_between(unc: List[dict], scope: str, ref: dict, t0: datetime, t1: datetime):
    if not (t0 and t1):
        return None, 0
    n = unknown = 0
    for u in unc:
        if not (u["ts"] and t0 < u["ts"] < t1):
            continue
        if scope == "S1" and u["session_id"] != ref["session_id"]:
            continue
        if scope == "S3":
            if u["visitor"] is None:
                unknown += 1
                continue
            if u["visitor"] != ref["visitor"]:
                continue
        n += 1
    return n, unknown


def scope_measure(scope: str, cur: dict, history: List[dict], unc: List[dict], profile: Optional[dict] = None) -> dict:
    profile = profile or {}
    key = _scope_key(scope, cur)
    seq = [e for e in history if _scope_key(scope, e) == key]
    if not seq:
        return {"pred_entry_id": "none-observed", "uncaptured_between": None}
    pred = seq[-1]
    n_unc, n_unk = uncaptured_between(unc, scope, cur, pred["ts"], cur["ts"])
    earlier = {}
    for k in range(len(seq) - 2, -1, -1):
        for el in seq[k]["verified"]:
            earlier.setdefault(el, k)
    tr = transform(set(pred["verified"]), set(cur["verified"]), earlier)
    returned = []
    for el in tr["returned"]:
        k = earlier[el]
        s = seq[k]
        du, _ = uncaptured_between(unc, scope, cur, s["ts"], cur["ts"])
        returned.append({"element": el, "last_seen_entry_id": s["entry_id"],
                         "d_captured": len(seq) - 1 - k, "d_uncaptured": du})
    tr["returned"] = returned
    adjacent = (n_unc == 0 and pred["session_id"] == cur["session_id"] and (scope != "S3" or n_unk == 0))
    tr["adjacent"] = adjacent
    tr["per_type"] = per_type(pred["verified"], cur["verified"])
    out = {"pred_entry_id": pred["entry_id"], "uncaptured_between": n_unc,
           "uncaptured_unknown_visitor": n_unk if scope == "S3" else None,
           "verified": tr,
           "uncertainty": enumerate_resolutions(set(pred["verified"]), set(cur["verified"]),
                                                pred["uncertain"], cur["uncertain"], ENUM_CAP),
           "text_layer": text_layer(pred["text"], cur["text"])}
    gaps = []
    if n_unc:
        gaps += [f"uncaptured-between:{n_unc}", "predecessor-not-adjacent", "gap-hides-events:possible"]
    elif not adjacent:
        gaps.append("predecessor-not-adjacent")
    if profile.get("ts_unplaceable"):
        # Known uncaptured turns whose timestamp cannot be parsed: counted, never placed.
        sids = {cur["session_id"]} if scope == "S1" else {cur["session_id"], pred["session_id"]}
        unp = [u for u in unc if u["ts"] is None and u["session_id"] in sids
               and (scope != "S3" or u["visitor"] in (cur["visitor"], None))]
        out["uncaptured_unplaceable"] = len(unp)
        if unp:
            gaps += [f"uncaptured-unplaceable:{len(unp)}", "adjacency-unverifiable"]
            if tr["adjacent"]:
                tr["adjacent"] = False
                gaps.append("predecessor-not-adjacent")
    if profile.get("codon_scope"):
        cond = set(pred.get("conditional") or []) | set(cur.get("conditional") or [])
        involved = cond & (set(pred["verified"]) | set(cur["verified"]))
        out["conditional_identity_n"] = len(involved)
        if involved:
            gaps.append("conditional-identity:mutable-angle")
    out["gaps"] = gaps
    return out


# ---------------------------------------------------------------- entry
def build_entry(prov: dict, idx: dict, sess: Optional[dict], history: List[dict], unc: List[dict],
                part: dict, ordinal: int, version: str = DERIVATION_VERSION) -> dict:
    profile = PROFILES[version]
    sid = prov.get("session_id")
    report: dict = {}
    mentions, gaps = recover(prov, idx, [m for m in (sess or {}).get("messages", []) if m["content"] is not None],
                             profile, report)
    verified = sorted({m["element"] for m in mentions if m["class"] == "VERIFIED"})
    conditional = sorted({m["element"] for m in mentions if m["class"] == "VERIFIED" and m.get("conditional")})
    uncertain = [m["candidates"] for m in mentions if m["class"] == "CANDIDATES"]
    text = sorted({f'{m["type"]}:{m["frag_hash"][:16]}' for m in mentions if m["class"] == "TEXT_ONLY"})
    meta = {}
    for el in verified:
        t, k = el.split(":", 1)
        if t == "seed" and k in idx["seed_meta"]:
            meta[el] = idx["seed_meta"][k]
        elif t == "mra" and k in idx["mra_meta"]:
            meta[el] = idx["mra_meta"][k]
    uid = prov.get("user_id")
    canon = idx["aliases"].get(uid)
    am = prov.get("assembled_messages") or []
    recomputed = h(json.dumps(am, ensure_ascii=False, sort_keys=False))
    comp = prov.get("components") or {}
    cls_counts, type_counts = {}, {}
    for m in mentions:
        cls_counts[m["class"]] = cls_counts.get(m["class"], 0) + 1
        type_counts[m["type"]] = type_counts.get(m["type"], 0) + 1
    ts = parse_ts(prov.get("timestamp"))
    cur = {"entry_id": f'{version}:{prov["provenance_id"]}', "session_id": sid,
           "presence": prov.get("presence"), "visitor": canon or uid, "ts": ts,
           "verified": verified, "uncertain": uncertain, "text": text, "conditional": conditional}
    scopes = {s: scope_measure(s, cur, history, unc, profile) for s in ("S1", "S2", "S3")}
    if part["match"] != "matched":
        gaps.append("response-unmatched")
    if recomputed != prov.get("content_hash"):
        gaps.append("provenance-hash-mismatch")
    availability = {"verified": verified, "uncertain": uncertain, "text": text,
                    "counts_by_class": cls_counts, "counts_by_type": type_counts}
    extra = {}
    if profile.get("completeness"):
        extra = {"completeness": report.get("completeness", {}), "configuration_complete": report.get("complete", True)}
    if profile.get("codon_scope"):
        availability["conditional"] = conditional
    return {
        **extra,
        "entry_id": cur["entry_id"], "derivation_version": version, "norm_version": NORM_VERSION,
        "source": {"provenance_oid": str(prov["_id"]), "provenance_id": prov.get("provenance_id"),
                   "turn_id": prov.get("turn_id"), "content_hash_recorded": prov.get("content_hash"),
                   "content_hash_recomputed": recomputed,
                   "integrity_verified": recomputed == prov.get("content_hash"),
                   "evidence_hashes": {"codon_selection": canonical_hash(comp.get("codon_selection")),
                                       "memory_components": canonical_hash(comp.get("memory_components"))}},
        "chronology": {"presence": prov.get("presence"), "session_id": sid, "exchange_index": prov.get("exchange_index"),
                       "timestamp": ts.isoformat() if ts else None, "ordinal": ordinal,
                       "session_open": prov.get("exchange_index") == 1,
                       "first_captured_in_session": not any(e["session_id"] == sid for e in history)},
        "visitor": {"user_id": uid, "resolved_visitor": canon or uid, "resolution": "alias" if canon else "raw"},
        "availability": availability,
        "element_meta": meta,
        "mentions": mentions,
        "scopes": scopes,
        "participation": part,
        "gaps": gaps,
    }


def hashed_part(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if k not in ("_id", "chain", "run_id", "derived_at")}


def chain_hash(prev: str, entry: dict) -> str:
    return h(prev + canonical_hash(hashed_part(entry)))


def _hist_item(e: dict) -> dict:
    c = e["chronology"]
    return {"entry_id": e["entry_id"], "session_id": c["session_id"], "presence": c["presence"],
            "visitor": e["visitor"]["resolved_visitor"], "ts": parse_ts(c["timestamp"]),
            "verified": e["availability"]["verified"], "uncertain": e["availability"]["uncertain"],
            "text": e["availability"]["text"], "conditional": e["availability"].get("conditional") or []}


# ---------------------------------------------------------------- lock
async def acquire_lock(ledger: Ledger, holder: str) -> bool:
    now = datetime.now(timezone.utc)
    try:
        r = await ledger.state.update_one(
            {"_id": "lock", "expires_at": {"$lt": now}},
            {"$set": {"holder": holder, "acquired_at": now, "expires_at": now + LOCK_TTL}}, upsert=True)
        return bool(r.matched_count or r.upserted_id)
    except DuplicateKeyError:
        return False


async def release_lock(ledger: Ledger, holder: str):
    await ledger.state.update_one({"_id": "lock", "holder": holder},
                                  {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}})


async def renew_lock(ledger: Ledger, holder: str) -> bool:
    r = await ledger.state.update_one({"_id": "lock", "holder": holder},
                                      {"$set": {"expires_at": datetime.now(timezone.utc) + LOCK_TTL}})
    return r.matched_count == 1


# ---------------------------------------------------------------- shared derivation context
async def derivation_context(db) -> dict:
    idx = await build_indexes(db)
    pres_by_sess = {}
    async for p in db.turn_provenance.find({}, {"session_id": 1, "presence": 1}):
        pres_by_sess.setdefault(p.get("session_id"), p.get("presence"))
    first = await db.turn_provenance.find_one({}, {"timestamp": 1}, sort=[("_id", 1)])
    return {"idx": idx, "window_start": parse_ts(first["timestamp"]) if first else None,
            "sessions": await load_sessions(db, pres_by_sess),
            "captured": set(await db.turn_provenance.distinct("turn_id"))}


def uncaptured_for(ctx: dict, presence: str, profile: dict) -> List[dict]:
    """Known assistant turns without provenance; unparseable timestamps are kept (ts=None) only when the profile counts them."""
    unc, ws = [], ctx["window_start"]
    for sid, s in ctx["sessions"].items():
        if s["presence"] != presence:
            continue
        vis = ctx["idx"]["aliases"].get(s["user_id"], s["user_id"])
        for m in s["messages"]:
            if m["role"] != "assistant" or m["id"] in ctx["captured"]:
                continue
            if m["ts"] and (ws is None or m["ts"] >= ws):
                unc.append({"ts": m["ts"], "session_id": sid, "visitor": vis})
            elif m["ts"] is None and profile.get("ts_unplaceable"):
                unc.append({"ts": None, "session_id": sid, "visitor": vis})
    return unc


# ---------------------------------------------------------------- run
async def run_once(db, trigger: str = "manual", ledger: Optional[Ledger] = None,
                   max_records: Optional[int] = None, now: Optional[datetime] = None,
                   version: str = DERIVATION_VERSION) -> dict:
    ledger = ledger or Ledger(db)
    profile = PROFILES[version]
    run_id = str(uuid.uuid4())
    try:
        if not await acquire_lock(ledger, run_id):
            return {"status": "skipped-locked", "run_id": None, "version": version}
    except Exception as e:
        logger.exception("[OBSERVATORY] lock acquisition failed")
        return {"status": "failed", "run_id": None, "version": version, "errors": [repr(e)], "processed": 0}
    now = now or datetime.now(timezone.utc)
    started = datetime.now(timezone.utc)
    processed, unsettled, errors, status, run_recorded = 0, 0, [], "failed", False
    try:
        await ledger.ensure_indexes()
        await ledger.runs.update_many({"status": "running", "started_at": {"$lt": started - LOCK_TTL}},
                                      {"$set": {"status": "abandoned"}})
        await ledger.runs.insert_one({"run_id": run_id, "trigger": trigger, "derivation_version": version,
                                      "norm_version": NORM_VERSION, "enum_cap": ENUM_CAP, "code_commit": _code_commit(),
                                      "started_at": started, "status": "running",
                                      "unavailable_evidence": UNAVAILABLE_EVIDENCE})
        run_recorded = True
        ctx = await derivation_context(db)
        idx, sessions = ctx["idx"], ctx["sessions"]
        lost = False
        for presence in sorted(await db.turn_provenance.distinct("presence")):
            if not await renew_lock(ledger, run_id):
                errors.append("lock-lost")
                break
            last = await ledger.entries.find_one(
                {"derivation_version": version, "chronology.presence": presence},
                sort=[("chronology.ordinal", -1)])
            q = {"presence": presence}
            if last:
                from bson import ObjectId
                q["_id"] = {"$gt": ObjectId(last["source"]["provenance_oid"])}
            if not await db.turn_provenance.count_documents(q, limit=1):
                continue
            history = [_hist_item(e) async for e in ledger.entries.find(
                {"derivation_version": version, "chronology.presence": presence},
                {"entry_id": 1, "chronology": 1, "visitor": 1, "availability": 1}).sort("chronology.ordinal", 1)]
            prev_hash = last["chain"]["entry_hash"] if last else "GENESIS"
            ordinal = last["chronology"]["ordinal"] + 1 if last else 0
            unc = uncaptured_for(ctx, presence, profile)
            async for prov in db.turn_provenance.find(q).sort("_id", 1):
                if max_records is not None and processed >= max_records:
                    break
                sess = sessions.get(prov.get("session_id"))
                part, settled = participation(prov, sess, now)
                if not settled:
                    unsettled += 1
                    break  # frontier: keep chain in provenance order
                entry = await asyncio.to_thread(build_entry, prov, idx, sess, history, unc, part, ordinal, version)
                entry["chain"] = {"prev_entry_hash": prev_hash, "entry_hash": chain_hash(prev_hash, entry)}
                entry["run_id"] = run_id
                entry["derived_at"] = datetime.now(timezone.utc)
                try:
                    await ledger.entries.insert_one(entry)
                except DuplicateKeyError:
                    errors.append(f"duplicate:{entry['entry_id']}")
                    break
                prev_hash = entry["chain"]["entry_hash"]
                history.append(_hist_item(entry))
                ordinal += 1
                processed += 1
                if processed % 25 == 0 and not await renew_lock(ledger, run_id):
                    errors.append("lock-lost")
                    lost = True
                    break
                await asyncio.sleep(0)
            if lost or (max_records is not None and processed >= max_records):
                break
        status = "ok-with-errors" if errors else "ok"
    except Exception as e:  # recorded; next run resumes from the ledger frontier
        logger.exception("[OBSERVATORY] run failed")
        errors.append(repr(e))
        status = "failed"
    finally:
        await release_lock(ledger, run_id)
    summary = {"status": status, "processed": processed, "unsettled_frontiers": unsettled,
               "errors": errors[:20], "finished_at": datetime.now(timezone.utc), "version": version}
    try:
        summary["ledger_total"] = await ledger.entries.count_documents({"derivation_version": version})
        if run_recorded:
            await ledger.runs.update_one({"run_id": run_id}, {"$set": summary})
    except Exception:
        logger.exception("[OBSERVATORY] run summary could not be recorded")
    logger.info(f"[OBSERVATORY] run {run_id[:8]} v{version} {trigger}: {status}, processed={processed}")
    return {"run_id": run_id, **summary}


async def catch_up(db, trigger: str, ledger: Optional[Ledger] = None, delay_s: float = 0,
                   versions=PRODUCTION_VERSIONS) -> dict:
    """Run until nothing new is settled (covers suspension, restarts, missed ticks)."""
    if delay_s:
        await asyncio.sleep(delay_s)
    last = {}
    for _ in range(20):
        progressed, healthy = False, True
        for v in versions:
            last = await run_once(db, trigger, ledger, version=v)
            if last.get("status") == "skipped-locked" and trigger == "startup-catch-up":
                # A lock left by a crashed process expires after LOCK_TTL; retry once then.
                await asyncio.sleep(LOCK_TTL.total_seconds() + 5)
                last = await run_once(db, trigger, ledger, version=v)
            if last.get("status") != "ok":
                healthy = False
                break
            progressed = progressed or bool(last.get("processed"))
        if not healthy or not progressed:
            break
    return last


# ---------------------------------------------------------------- verification
async def verify(db, ledger: Optional[Ledger] = None, check_drift: bool = False,
                 version: str = DERIVATION_VERSION, reproduce_check: bool = False) -> dict:
    """Three separately labelled claims:
    ledger_integrity (chain + ordinals), source_consistency (inputs unchanged), reproducibility (re-derivation)."""
    ledger = ledger or Ledger(db)
    V = {"derivation_version": version}
    integ = {"presences": {}, "ok": True}
    drift_n = checked = 0
    for presence in sorted(await ledger.entries.distinct("chronology.presence", V)):
        prev, n, broken = "GENESIS", 0, None
        async for e in ledger.entries.find({**V, "chronology.presence": presence}).sort("chronology.ordinal", 1):
            if e["chain"]["prev_entry_hash"] != prev or chain_hash(prev, e) != e["chain"]["entry_hash"] \
                    or e["chronology"]["ordinal"] != n:
                broken = broken or e["entry_id"]
            prev = e["chain"]["entry_hash"]
            n += 1
            if check_drift:
                for m in e["mentions"]:
                    if m["class"] == "VERIFIED" and m.get("record_fingerprint"):
                        checked += 1
                        if await current_fingerprint(db, m["element"]) != m["record_fingerprint"]:
                            drift_n += 1
        integ["presences"][presence] = {"entries": n, "chain_ok": broken is None, "broken_at": broken}
        integ["ok"] = integ["ok"] and broken is None
    from bson import ObjectId
    src = {"ok": True, "checked": 0, "provenance_changed": [], "components_changed": []}
    batch = []

    async def check(items):
        found = {str(p["_id"]): p async for p in db.turn_provenance.find(
            {"_id": {"$in": [ObjectId(x["source"]["provenance_oid"]) for x in items]}},
            {"assembled_messages": 1, "components.codon_selection": 1, "components.memory_components": 1})}
        for x in items:
            src["checked"] += 1
            p = found.get(x["source"]["provenance_oid"])
            if not p or h(json.dumps(p.get("assembled_messages") or [], ensure_ascii=False)) != x["source"]["content_hash_recomputed"]:
                src["provenance_changed"].append(x["entry_id"])
                continue
            comp, eh = p.get("components") or {}, x["source"].get("evidence_hashes") or {}
            if any(canonical_hash(comp.get(k)) != eh.get(k) for k in ("codon_selection", "memory_components")):
                src["components_changed"].append(x["entry_id"])

    async for e in ledger.entries.find(V, {"entry_id": 1, "source": 1}):
        batch.append(e)
        if len(batch) >= 200:
            await check(batch)
            batch = []
    if batch:
        await check(batch)
    src["ok"] = not src["provenance_changed"] and not src["components_changed"]
    out = {"version": version, "ledger_integrity": integ, "source_consistency": src, "reproducibility": None,
           "drift": {"verified_mentions_checked": checked, "source_drifted": drift_n} if check_drift else None,
           "presences": integ["presences"], "provenance_changed": src["provenance_changed"]}
    if reproduce_check:
        out["reproducibility"] = await reproduce(db, ledger, version)
    out["ok"] = integ["ok"] and src["ok"] and (out["reproducibility"] is None or out["reproducibility"]["ok"])
    return out


async def reproduce(db, ledger: Ledger, version: str, now: Optional[datetime] = None) -> dict:
    """Re-derive every stored entry in memory and compare. Uses stored participation (time-dependent);
    identification uses the CURRENT store, so a pass proves reproducibility only while the store has not drifted."""
    from bson import ObjectId
    profile, now = PROFILES[version], now or datetime.now(timezone.utc)
    ctx = await derivation_context(db)
    res = {"ok": True, "checked": 0, "mismatched": 0, "missing_provenance": 0, "participation_time_dependent": 0,
           "basis": "current store; stored participation", "first_mismatch": None}
    for presence in sorted(await ledger.entries.distinct("chronology.presence", {"derivation_version": version})):
        unc, history, prev = uncaptured_for(ctx, presence, profile), [], "GENESIS"
        async for e in ledger.entries.find({"derivation_version": version, "chronology.presence": presence}).sort("chronology.ordinal", 1):
            prov = await db.turn_provenance.find_one({"_id": ObjectId(e["source"]["provenance_oid"])})
            res["checked"] += 1
            if not prov:
                res["missing_provenance"] += 1
            else:
                sess = ctx["sessions"].get(prov.get("session_id"))
                new = await asyncio.to_thread(build_entry, prov, ctx["idx"], sess, history, unc,
                                              e["participation"], e["chronology"]["ordinal"], version)
                if chain_hash(prev, new) != e["chain"]["entry_hash"]:
                    res["mismatched"] += 1
                    res["first_mismatch"] = res["first_mismatch"] or e["entry_id"]
                if participation(prov, sess, now)[0] != e["participation"]:
                    res["participation_time_dependent"] += 1
            history.append(_hist_item(e))
            prev = e["chain"]["entry_hash"]
    res["ok"] = res["mismatched"] == 0 and res["missing_provenance"] == 0
    return res
