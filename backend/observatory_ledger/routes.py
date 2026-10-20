"""Observatory ledger API: cron tick (secret), status, lattice, entry evidence, verify."""
import asyncio
import hmac
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from . import DERIVATION_VERSION, PROFILES
from .compare import delta, invariance
from .derive import Ledger, catch_up, parse_ts, verify, load_sessions
from .recover import evidence_text, canonical_hash

logger = logging.getLogger("observatory_ledger")
router = APIRouter(prefix="/api/observatory")
_state = {"db": None, "task": None}


def init_observatory(db):
    _state["db"] = db


def _log_task_failure(t: asyncio.Task):
    if not t.cancelled() and t.exception():
        logger.error("[OBSERVATORY] background derivation task failed", exc_info=t.exception())


def _version(v: Optional[str]) -> str:
    v = v or DERIVATION_VERSION
    if v not in PROFILES:
        raise HTTPException(400, f"unknown derivation version {v}")
    return v


def _spawn(trigger: str, delay_s: float = 0):
    t = _state["task"]
    if t and not t.done():
        return False
    _state["task"] = asyncio.create_task(catch_up(_state["db"], trigger, delay_s=delay_s))
    _state["task"].add_done_callback(_log_task_failure)
    return True


HOURLY_S = 3600


async def _hourly_loop():
    # Backstop for the platform cron (preview registration can be unavailable); the run lock prevents overlap.
    while True:
        await asyncio.sleep(HOURLY_S)
        try:
            _spawn("hourly-loop")
        except Exception:
            logger.exception("[OBSERVATORY] hourly loop spawn failed")


def start_catch_up_on_boot(delay_s: float = 20):
    _spawn("startup-catch-up", delay_s)
    if not _state.get("loop") or _state["loop"].done():
        _state["loop"] = asyncio.create_task(_hourly_loop())


@router.post("/cron/tick")
async def cron_tick(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else ""
    if not secret or not token or not hmac.compare_digest(token, secret):
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = None
    if body is not None and not isinstance(body, dict):
        return JSONResponse({"detail": "invalid body"}, status_code=400)
    run_key = request.headers.get("x-webhook-id") or (body or {}).get("run_id")
    led = Ledger(_state["db"])
    if run_key:
        r = await led.state.update_one({"_id": "webhooks"}, {"$addToSet": {"seen": run_key}}, upsert=True)
        if not r.modified_count and not r.upserted_id:
            return JSONResponse({"accepted": False, "duplicate": True}, status_code=202)
        await led.state.update_one({"_id": "webhooks"}, {"$push": {"seen": {"$each": [], "$slice": -200}}})
    started = _spawn("cron")
    return JSONResponse({"accepted": True, "started": started}, status_code=202)


@router.post("/run")
async def manual_run():
    return JSONResponse({"accepted": True, "started": _spawn("manual")}, status_code=202)


@router.get("/status")
async def status(version: Optional[str] = None):
    version = _version(version)
    db = _state["db"]
    led = Ledger(db)
    total = await led.entries.count_documents({"derivation_version": version})
    prov_total = await db.turn_provenance.count_documents({})
    runs = await led.runs.find({}, {"_id": 0, "unavailable_evidence": 0}).sort("started_at", -1).limit(8).to_list(8)
    per = []
    async for r in led.entries.aggregate([
        {"$match": {"derivation_version": version}},
        {"$group": {"_id": "$chronology.presence", "n": {"$sum": 1}, "last": {"$max": "$chronology.timestamp"},
                    "visitors": {"$addToSet": "$visitor.resolved_visitor"}}}]):
        per.append({"presence": r["_id"], "entries": r["n"], "last_timestamp": r["last"], "visitors": len(r["visitors"])})
    per.sort(key=lambda x: -x["entries"])
    versions = [{"version": r["_id"], "entries": r["n"]} async for r in led.entries.aggregate(
        [{"$group": {"_id": "$derivation_version", "n": {"$sum": 1}}}, {"$sort": {"_id": 1}}])]
    last_work = await led.runs.find_one({"processed": {"$gt": 0}}, {"_id": 0, "unavailable_evidence": 0}, sort=[("started_at", -1)])
    return {"derivation_version": version, "versions": versions, "ledger_entries": total, "provenance_records": prov_total,
            # Provenance records not yet in this version's ledger (unsettled turns plus any backlog).
            "not_yet_measured": prov_total - total, "running": bool(_state["task"] and not _state["task"].done()),
            "presences": per, "runs": runs, "last_work_run": last_work,
            "unavailable_evidence": (await led.runs.find_one({}, {"unavailable_evidence": 1}, sort=[("started_at", -1)]) or {}).get("unavailable_evidence")}


@router.get("/visitors")
async def visitors(presence: str, version: Optional[str] = None):
    version = _version(version)
    led = Ledger(_state["db"])
    out = []
    async for r in led.entries.aggregate([
        {"$match": {"derivation_version": version, "chronology.presence": presence}},
        {"$group": {"_id": "$visitor.resolved_visitor", "n": {"$sum": 1}, "last": {"$max": "$chronology.timestamp"}}},
        {"$sort": {"last": -1}}]):
        out.append({"visitor": r["_id"], "entries": r["n"], "last_timestamp": r["last"],
                    "is_test": bool(_TEST_VISITOR.match(str(r["_id"] or "")))})
    return {"visitors": out}


# QA-created provenance (labelled at view time only; measurements are never altered).
_TEST_VISITOR = re.compile(r"^(prov_|e1-|test|TEST|qa[-_])", re.I)


def _label(el: str, meta: dict) -> str:
    t, k = el.split(":", 1)
    if t == "seed":
        m = meta.get(el) or {}
        return f"seed {k[-6:]} · {str(m.get('created_at'))[5:10]} · ← {str(m.get('source_session_id'))[:6]}"
    if t == "mra":
        m = meta.get(el) or {}
        return f"crumb {k[:8]} · ← {str(m.get('source_session_id'))[:6]}"
    if t == "codon":
        return f"codon {meta.get(el, {}).get('name') or k[-6:]}"
    return f"{t} · {k[:8]}"


@router.get("/lattice")
async def lattice(presence: str, scope: str = "S2", visitor: Optional[str] = None, limit: int = 24,
                  before_ordinal: Optional[int] = None, version: Optional[str] = None):
    if scope not in ("S1", "S2", "S3"):
        raise HTTPException(400, "scope must be S1, S2 or S3")
    version = _version(version)
    db = _state["db"]
    led = Ledger(db)
    limit = max(4, min(limit, 60))
    q = {"derivation_version": version, "chronology.presence": presence}
    if scope == "S3":
        if not visitor:
            last = await led.entries.find_one(q, sort=[("chronology.ordinal", -1)])
            visitor = last["visitor"]["resolved_visitor"] if last else None
        q["visitor.resolved_visitor"] = visitor
    if before_ordinal is not None:
        q["chronology.ordinal"] = {"$lt": before_ordinal}
    proj = {"_id": 0, "mentions": 0}
    cols = await led.entries.find(q, proj).sort("chronology.ordinal", -1).limit(limit).to_list(limit)
    cols.reverse()
    if not cols:
        return {"presence": presence, "scope": scope, "visitor": visitor, "columns": [], "rows": [], "uncertain_rows": []}

    # Known-but-uncaptured assistant turns between the first and last column (scope-filtered).
    t0, t1 = parse_ts(cols[0]["chronology"]["timestamp"]), parse_ts(cols[-1]["chronology"]["timestamp"])
    captured = set(await db.turn_provenance.distinct("turn_id", {"presence": presence}))
    pres_by_sess = {s: presence for s in await db.turn_provenance.distinct("session_id", {"presence": presence})}
    sessions = await load_sessions(db, pres_by_sess)
    vis_of_session = {}
    async for a in db.user_aliases.find({}, {"canonical_id": 1, "aliases": 1}):
        for x in (a.get("aliases") or []):
            vis_of_session[x] = a["canonical_id"]
    shown_sessions = {c["chronology"]["session_id"] for c in cols}
    unc = []
    for sid, s in sessions.items():
        if s["presence"] != presence:
            continue
        if scope == "S1" and sid not in shown_sessions:
            continue
        v = vis_of_session.get(s["user_id"], s["user_id"])
        if scope == "S3" and v != visitor:
            continue
        for m in s["messages"]:
            if m["role"] == "assistant" and m["id"] not in captured and m["ts"] and t0 < m["ts"] < t1:
                unc.append({"kind": "uncaptured", "timestamp": m["ts"].isoformat(), "session_id": sid, "visitor": v})

    timeline = [{"kind": "entry", "timestamp": c["chronology"]["timestamp"], "entry": c} for c in cols] + unc
    timeline.sort(key=lambda x: x["timestamp"])

    meta, first_seen, columns, conditional = {}, {}, [], set()
    for ci, item in enumerate(timeline):
        if item["kind"] == "uncaptured":
            columns.append({"kind": "uncaptured", "timestamp": item["timestamp"], "session_id": item["session_id"],
                            "visitor": item["visitor"]})
            continue
        c = item["entry"]
        meta.update(c.get("element_meta") or {})
        conditional.update(c["availability"].get("conditional") or [])
        sc = c["scopes"][scope]
        avail = c["availability"]["verified"]
        for el in avail:
            first_seen.setdefault(el, ci)
        tr = sc.get("verified") or {}
        for el in tr.get("withdrawn", []):
            first_seen.setdefault(el, ci)
        columns.append({
            "kind": "entry", "entry_id": c["entry_id"], "timestamp": c["chronology"]["timestamp"],
            "session_id": c["chronology"]["session_id"], "exchange_index": c["chronology"]["exchange_index"],
            "ordinal": c["chronology"]["ordinal"], "session_open": c["chronology"]["session_open"],
            "visitor": c["visitor"]["resolved_visitor"], "pred_entry_id": sc.get("pred_entry_id"),
            "uncaptured_between": sc.get("uncaptured_between"),
            "relation": tr.get("relation_rcc5"), "jaccard": tr.get("jaccard"),
            "adjacent": tr.get("adjacent"), "uncertainty": sc.get("uncertainty"),
            "text_layer": sc.get("text_layer"), "gaps": (sc.get("gaps") or []) + (c.get("gaps") or []),
            "participation": c["participation"],
            "counts": {"verified": len(avail), "uncertain": len(c["availability"]["uncertain"]),
                       "text_only": len(c["availability"]["text"])},
            "configuration_complete": c.get("configuration_complete"),
            "conditional_identity_n": sc.get("conditional_identity_n"),
            "_avail": set(avail), "_tr": tr, "_unc": c["availability"]["uncertain"],
        })

    # Predecessor position relative to the display (mathematical adjacency is never implied by column adjacency).
    col_of = {c["entry_id"]: i for i, c in enumerate(columns) if c["kind"] == "entry"}
    prev_entry = None
    for i, c in enumerate(columns):
        if c["kind"] != "entry":
            continue
        p = c["pred_entry_id"]
        if p == "none-observed":
            c["pred_position"], c["pred_col"] = "none", None
        elif p not in col_of:
            c["pred_position"], c["pred_col"] = "off-page", None
        else:
            j = col_of[p]
            c["pred_col"] = j
            c["pred_position"] = "previous-column" if j == prev_entry else ("later-column" if j > i else "earlier-column")
        prev_entry = i

    def glyph(col, el):
        if col["kind"] != "entry":
            return None
        tr = col["_tr"]
        if el in col["_avail"]:
            if col["pred_entry_id"] == "none-observed":
                return "first"
            if any(r["element"] == el for r in tr.get("returned", [])):
                return "returned"
            if el in tr.get("introduced_first_observed", []):
                return "first"
            if not tr.get("adjacent"):
                return "present-gap"
            return "retained" if col["pred_position"] == "previous-column" else "retained-remote"
        if el in tr.get("withdrawn", []):
            return "withdrawn"
        return None

    from bson import ObjectId
    missing = [e for e in first_seen if e not in meta and e.split(":")[0] in ("seed", "mra", "codon")]
    seed_ids = [ObjectId(e[5:]) for e in missing if e.startswith("seed:")]
    async for sd in db.continuity_seeds.find({"_id": {"$in": seed_ids}}, {"session_id": 1, "created_at": 1}):
        meta[f"seed:{sd['_id']}"] = {"source_session_id": sd.get("session_id"), "created_at": str(sd.get("created_at"))}
    async for nd in db.permanent_mra.find({"node_id": {"$in": [e[4:] for e in missing if e.startswith("mra:")]}},
                                          {"node_id": 1, "source_session_id": 1, "promoted_at": 1}):
        meta[f"mra:{nd['node_id']}"] = {"source_session_id": nd.get("source_session_id"), "created_at": str(nd.get("promoted_at"))}
    codon_ids = [ObjectId(e[6:]) for e in first_seen if e.startswith("codon:")]
    async for cd in db.living_codons.find({"_id": {"$in": codon_ids}}, {"name": 1}):
        meta[f"codon:{cd['_id']}"] = {"name": cd.get("name")}

    order = {"seed": 0, "mra": 1, "codon": 2, "history": 3}
    elements = sorted(first_seen, key=lambda e: (order.get(e.split(":")[0], 9), first_seen[e], e))
    rows, history_row = [], []
    for el in elements:
        cells = [glyph(c, el) for c in columns]
        if el.startswith("history:"):
            history_row.append(cells)
            continue
        rows.append({"element": el, "type": el.split(":")[0], "label": _label(el, meta), "cells": cells,
                     "conditional": el in conditional})
    if history_row:
        agg = []
        for i, c in enumerate(columns):
            if c["kind"] != "entry":
                agg.append(None)
                continue
            vals = [r[i] for r in history_row if r[i]]
            agg.append({"present": sum(v != "withdrawn" for v in vals),
                        "introduced": sum(v in ("first", "returned") for v in vals),
                        "withdrawn": sum(v == "withdrawn" for v in vals)})
        rows.append({"element": "history:*", "type": "history", "label": "conversation history (messages)", "cells": agg,
                     "aggregate": True})

    # Uncertain identities (CANDIDATES): one row per candidate set; presence only, never merged into verified rows.
    unc_rows = {}
    for i, c in enumerate(columns):
        if c["kind"] != "entry":
            continue
        for cands in c.pop("_unc"):
            key = "|".join(sorted(cands))
            r = unc_rows.setdefault(key, {"element": f"uncertain:{canonical_hash(sorted(cands))[:12]}",
                                          "type": cands[0].split(":")[0], "uncertain": True,
                                          "candidates": sorted(cands), "cells": [None] * len(columns),
                                          "mult": [0] * len(columns), "_first": i})
            r["cells"][i] = "uncertain"
            r["mult"][i] += 1
    noun = {"mra": "breadcrumb", "seed": "seed", "codon": "codon", "history": "message"}
    for r in sorted(unc_rows.values(), key=lambda r: (order.get(r["type"], 9), r["_first"])):
        r.pop("_first")
        r["label"] = f"uncertain {noun.get(r['type'], r['type'])} · 1 of {len(r['candidates'])}"
        rows.append(r)

    for c in columns:
        c.pop("_avail", None)
        c.pop("_tr", None)
    return {"presence": presence, "scope": scope, "visitor": visitor, "version": version, "columns": columns, "rows": rows,
            "has_more": cols[0]["chronology"]["ordinal"] > 0 and await led.entries.count_documents(
                {**q, "chronology.ordinal": {"$lt": cols[0]["chronology"]["ordinal"]}}, limit=1) > 0,
            "first_ordinal": cols[0]["chronology"]["ordinal"]}


@router.get("/entry/{entry_id:path}")
async def entry(entry_id: str):
    db = _state["db"]
    led = Ledger(db)
    e = await led.entries.find_one({"entry_id": entry_id}, {"_id": 0})
    if not e:
        raise HTTPException(404, "entry not found")
    from bson import ObjectId
    prov = await db.turn_provenance.find_one({"_id": ObjectId(e["source"]["provenance_oid"])})
    for m in e["mentions"]:
        m["evidence_text"] = evidence_text(prov, m) if prov else None
    run = await led.runs.find_one({"run_id": e.get("run_id")}, {"_id": 0})
    e["run"] = run
    return e


@router.get("/verify")
async def verify_route(drift: bool = False, reproduce: bool = False, version: Optional[str] = None):
    return await verify(_state["db"], check_drift=drift, version=_version(version), reproduce_check=reproduce)


@router.get("/compare")
async def compare_route(a: str, b: str, mode: str = "delta"):
    """Aggregate cross-version comparison of the production ledger (counts only)."""
    _version(a), _version(b)
    led = Ledger(_state["db"])
    if mode == "invariance":
        return await invariance(led, a, led, b)
    if mode == "delta":
        return await delta(led, a, led, b)
    raise HTTPException(400, "mode must be invariance or delta")
