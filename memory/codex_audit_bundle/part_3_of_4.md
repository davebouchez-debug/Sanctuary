# SANCTUARY 1.0 · OBSERVATORY AUDIT BUNDLE · PART 3 OF 4
## API, server wiring, cron, and Engagement Lattice frontend
Files in this part:
- `backend/observatory_ledger/routes.py`
- `backend/server.py (excerpt: only lines added for the Observatory)`
- `.emergent/crons.yml`
- `backend/.env (excerpt, value redacted)`
- `frontend/src/components/observatory/EngagementLattice.jsx`
- `frontend/src/components/observatory/LatticeGrid.jsx`
- `frontend/src/components/observatory/EvidenceDrawer.jsx`
- `frontend/src/components/observatory/LedgerStatus.jsx`

Codex: part 3 of 4. Continue collecting; audit once all 4 parts are received.


===== FILE: backend/observatory_ledger/routes.py =====
```python
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

from . import DERIVATION_VERSION
from .derive import Ledger, catch_up, parse_ts, verify, load_sessions
from .recover import evidence_text, canonical_hash

logger = logging.getLogger("observatory_ledger")
router = APIRouter(prefix="/api/observatory")
_state = {"db": None, "task": None}


def init_observatory(db):
    _state["db"] = db


def _spawn(trigger: str, delay_s: float = 0):
    t = _state["task"]
    if t and not t.done():
        return False
    _state["task"] = asyncio.create_task(catch_up(_state["db"], trigger, delay_s=delay_s))
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
async def status():
    db = _state["db"]
    led = Ledger(db)
    total = await led.entries.count_documents({"derivation_version": DERIVATION_VERSION})
    prov_total = await db.turn_provenance.count_documents({})
    runs = await led.runs.find({}, {"_id": 0, "unavailable_evidence": 0}).sort("started_at", -1).limit(8).to_list(8)
    per = []
    async for r in led.entries.aggregate([
        {"$match": {"derivation_version": DERIVATION_VERSION}},
        {"$group": {"_id": "$chronology.presence", "n": {"$sum": 1}, "last": {"$max": "$chronology.timestamp"},
                    "visitors": {"$addToSet": "$visitor.resolved_visitor"}}}]):
        per.append({"presence": r["_id"], "entries": r["n"], "last_timestamp": r["last"], "visitors": len(r["visitors"])})
    per.sort(key=lambda x: -x["entries"])
    last_work = await led.runs.find_one({"processed": {"$gt": 0}}, {"_id": 0, "unavailable_evidence": 0}, sort=[("started_at", -1)])
    return {"derivation_version": DERIVATION_VERSION, "ledger_entries": total, "provenance_records": prov_total,
            "pending": prov_total - total, "running": bool(_state["task"] and not _state["task"].done()),
            "presences": per, "runs": runs, "last_work_run": last_work,
            "unavailable_evidence": (await led.runs.find_one({}, {"unavailable_evidence": 1}, sort=[("started_at", -1)]) or {}).get("unavailable_evidence")}


@router.get("/visitors")
async def visitors(presence: str):
    led = Ledger(_state["db"])
    out = []
    async for r in led.entries.aggregate([
        {"$match": {"derivation_version": DERIVATION_VERSION, "chronology.presence": presence}},
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
                  before_ordinal: Optional[int] = None):
    if scope not in ("S1", "S2", "S3"):
        raise HTTPException(400, "scope must be S1, S2 or S3")
    db = _state["db"]
    led = Ledger(db)
    limit = max(4, min(limit, 60))
    q = {"derivation_version": DERIVATION_VERSION, "chronology.presence": presence}
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

    meta, first_seen, columns = {}, {}, []
    for ci, item in enumerate(timeline):
        if item["kind"] == "uncaptured":
            columns.append({"kind": "uncaptured", "timestamp": item["timestamp"], "session_id": item["session_id"],
                            "visitor": item["visitor"]})
            continue
        c = item["entry"]
        meta.update(c.get("element_meta") or {})
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
            "_avail": set(avail), "_tr": tr, "_unc": c["availability"]["uncertain"],
        })

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
            return "retained" if tr.get("adjacent") else "present-gap"
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
        rows.append({"element": el, "type": el.split(":")[0], "label": _label(el, meta), "cells": cells})
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
    return {"presence": presence, "scope": scope, "visitor": visitor, "columns": columns, "rows": rows,
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
async def verify_route(drift: bool = False):
    return await verify(_state["db"], check_drift=drift)
```
===== END FILE: backend/observatory_ledger/routes.py =====


===== FILE: backend/server.py (excerpt: only lines added for the Observatory) =====
```python
app.include_router(api_router)

# Observatory relational-history ledger: independent read-only observer.
from observatory_ledger.routes import router as observatory_ledger_router, init_observatory, start_catch_up_on_boot
init_observatory(db)
app.include_router(observatory_ledger_router)


@app.on_event("startup")
async def observatory_ledger_catch_up():
    start_catch_up_on_boot(delay_s=20)
```
===== END FILE: backend/server.py (excerpt: only lines added for the Observatory) =====


===== FILE: .emergent/crons.yml =====
```yaml
crons:
  - name: observatory-ledger
    description: "Hourly Observatory catch-up: measures newly settled engagements into the relational-history ledger"
    cron: "7 * * * *"
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    endpoint: "{{BASE_URL}}/api/observatory/cron/tick"
    method: POST
    enabled: true
```
===== END FILE: .emergent/crons.yml =====


===== FILE: backend/.env (excerpt, value redacted) =====
```
WEBHOOK_CRON_SECRET="<redacted — present in backend/.env>"
```
===== END FILE: backend/.env (excerpt, value redacted) =====


===== FILE: frontend/src/components/observatory/EngagementLattice.jsx =====
```jsx
import React, { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { API } from "../../App";
import { LatticeGrid } from "./LatticeGrid";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { LedgerStatus } from "./LedgerStatus";

const REFRESH_MS = 60000;
const SCOPES = [
  { key: "S1", label: "Same conversation" },
  { key: "S2", label: "Same presence · any visitor" },
  { key: "S3", label: "Same presence · same visitor" },
];

const Chip = ({ active, onClick, children, testid }) => (
  <button onClick={onClick} data-testid={testid}
    className={`rounded-full border px-3 py-1 font-mono text-[11px] tracking-wider transition-colors ${active ? "border-emerald-400/50 bg-emerald-400/10 text-emerald-300" : "border-white/10 text-zinc-400 hover:text-zinc-200"}`}>
    {children}
  </button>
);

export const EngagementLattice = () => {
  const [status, setStatus] = useState(null);
  const [presence, setPresence] = useState("");
  const [scope, setScope] = useState("S2");
  const [visitor, setVisitor] = useState("");
  const [visitors, setVisitors] = useState([]);
  const [before, setBefore] = useState(null);
  const [showText, setShowText] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [entryId, setEntryId] = useState(null);
  const [error, setError] = useState(null);
  const reqId = useRef(0);

  const loadStatus = useCallback(async () => {
    try {
      const { data: s } = await axios.get(`${API}/observatory/status`);
      setStatus(s);
      setPresence((p) => p || s.presences?.[0]?.presence || "");
    } catch {
      setError("Observer status unavailable — retrying automatically.");
    }
  }, []);

  const loadLattice = useCallback(async () => {
    if (!presence) return;
    const id = ++reqId.current;
    setLoading(true);
    try {
      const params = { presence, scope, limit: 24 };
      if (scope === "S3" && visitor) params.visitor = visitor;
      if (before != null) params.before_ordinal = before;
      const { data: d } = await axios.get(`${API}/observatory/lattice`, { params });
      if (id !== reqId.current) return;
      setData(d);
      setError(null);
      if (scope === "S3" && !visitor && d.visitor) setVisitor(d.visitor);
    } catch {
      if (id === reqId.current) setError("Lattice could not be loaded — retrying automatically.");
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }, [presence, scope, visitor, before]);

  useEffect(() => { loadStatus(); const t = setInterval(loadStatus, REFRESH_MS); return () => clearInterval(t); }, [loadStatus]);
  useEffect(() => { loadLattice(); }, [loadLattice]);
  useEffect(() => {
    if (before != null) return undefined;
    const t = setInterval(loadLattice, REFRESH_MS);
    return () => clearInterval(t);
  }, [loadLattice, before]);
  useEffect(() => {
    if (!presence) return;
    let live = true;
    axios.get(`${API}/observatory/visitors`, { params: { presence } })
      .then(({ data: v }) => live && setVisitors(v.visitors || []))
      .catch(() => live && setVisitors([]));
    return () => { live = false; };
  }, [presence]);

  const pickPresence = (p) => { setPresence(p); setVisitor(""); setBefore(null); };
  const pickScope = (s) => { setScope(s); setBefore(null); };

  return (
    <div className="space-y-5" data-testid="engagement-lattice">
      <LedgerStatus status={status} />
      <div className="rounded-2xl border border-white/10 bg-[#0A0C12]/80 p-4 backdrop-blur-xl">
        <div className="flex flex-wrap gap-2" data-testid="lattice-presence-picker">
          {(status?.presences || []).map((p) => (
            <Chip key={p.presence} active={presence === p.presence} onClick={() => pickPresence(p.presence)}
              testid={`lattice-presence-${p.presence}`}>{p.presence} {p.entries}</Chip>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2" data-testid="lattice-scope-picker">
          <span className="mr-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">compare with</span>
          {SCOPES.map((s) => (
            <Chip key={s.key} active={scope === s.key} onClick={() => pickScope(s.key)} testid={`lattice-scope-${s.key}`}>
              {s.key} · {s.label}
            </Chip>
          ))}
          {scope === "S3" && (
            <select value={visitor} onChange={(e) => { setVisitor(e.target.value); setBefore(null); }}
              data-testid="lattice-visitor-select"
              className="rounded-full border border-white/10 bg-black/40 px-3 py-1 font-mono text-[11px] text-zinc-300">
              {visitors.map((v) => <option key={v.visitor} value={v.visitor}>visitor {String(v.visitor).slice(0, 8)}{v.is_test ? " (test record)" : ""} · {v.entries}</option>)}
            </select>
          )}
          <label className="ml-auto flex items-center gap-2 font-mono text-[11px] text-zinc-400">
            <input type="checkbox" checked={showText} onChange={(e) => setShowText(e.target.checked)} data-testid="lattice-text-toggle" />
            text-only layer
          </label>
        </div>
      </div>
      {error && <div className="rounded-xl border border-amber-400/30 bg-amber-400/5 px-4 py-2 font-mono text-[11px] text-amber-300" data-testid="lattice-error">{error}</div>}
      <LatticeGrid data={data} loading={loading} showText={showText} onOpen={setEntryId}
        onOlder={() => setBefore(data?.first_ordinal)} onLatest={() => setBefore(null)} paged={before != null} />
      <EvidenceDrawer entryId={entryId} onClose={() => setEntryId(null)} />
    </div>
  );
};
```
===== END FILE: frontend/src/components/observatory/EngagementLattice.jsx =====


===== FILE: frontend/src/components/observatory/LatticeGrid.jsx =====
```jsx
import React, { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";

const CELL = 46;
const GLYPH = {
  first: { ch: "◆", cls: "text-emerald-300", title: "first observed in this scope" },
  returned: { ch: "↺", cls: "text-sky-300", title: "returned (seen earlier in scope, then absent)" },
  retained: { ch: "━━━", cls: "text-zinc-300", title: "retained from the adjacent predecessor" },
  "present-gap": { ch: "· · ·", cls: "text-sky-200/70", title: "present at both observations — unobserved turns between" },
  withdrawn: { ch: "○", cls: "text-zinc-500", title: "withdrawn since predecessor" },
  uncertain: { ch: "◇", cls: "text-amber-200/80", title: "present, identity uncertain (one of several stored records with identical text)" },
};
const TYPE_LABEL = { seed: "Continuity seeds", mra: "Breadcrumbs (permanent MRA)", codon: "Codons", history: "Conversation history" };
const fmtGap = (s) => (s == null ? "" : s < 90 ? `${Math.round(s)}s` : s < 5400 ? `${Math.round(s / 60)}m` : s < 172800 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`);
const hatch = { backgroundImage: "repeating-linear-gradient(45deg, rgba(255,255,255,0.06) 0 4px, transparent 4px 8px)" };

const ColHead = ({ c, prev, onOpen }) => {
  const boundary = prev && prev.session_id !== c.session_id;
  const dt = prev ? (new Date(c.timestamp) - new Date(prev.timestamp)) / 1000 : null;
  return (
    <div style={{ width: CELL, ...(c.kind === "uncaptured" ? hatch : {}) }}
      className={`flex-shrink-0 px-0.5 text-center font-mono text-[9px] leading-tight ${boundary ? "border-l-2 border-zinc-400/60" : "border-l border-white/[0.04]"}`}>
      {c.kind === "uncaptured" ? (
        <div className="py-1 text-zinc-500" title="assistant turn exists but its input was not captured" data-testid="lattice-col-uncaptured">uncapt.</div>
      ) : (
        <button onClick={() => onOpen(c.entry_id)} className="w-full py-1 text-zinc-300 hover:text-emerald-300" data-testid={`lattice-col-${c.ordinal}`}
          title={`${new Date(c.timestamp).toLocaleString()} · session ${c.session_id.slice(0, 8)} · visitor ${String(c.visitor).slice(0, 8)}`}>
          #{c.exchange_index}{c.session_open ? "·open" : ""}
        </button>
      )}
      <div className="text-zinc-500">{fmtGap(dt)}</div>
      {c.kind === "entry" && <div className="truncate text-zinc-500">{String(c.visitor).slice(0, 4)}</div>}
    </div>
  );
};

const Strip = ({ label, columns, render, testid }) => (
  <div className="flex border-t border-white/10" data-testid={testid}>
    <div className="sticky left-0 z-10 w-60 flex-shrink-0 bg-[#0A0C12] px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">{label}</div>
    {columns.map((c, i) => (
      <div key={i} style={{ width: CELL, ...(c.kind === "uncaptured" ? hatch : {}) }}
        className="flex-shrink-0 border-l border-white/[0.04] px-0.5 py-1 text-center font-mono text-[9px] leading-tight text-zinc-400">
        {c.kind === "entry" ? render(c) : null}
      </div>
    ))}
  </div>
);

const relCell = (c) => {
  if (c.pred_entry_id === "none-observed") return <span className="text-zinc-500" title="no earlier observation in this scope">—</span>;
  const u = c.uncertainty;
  const undetermined = u && !u.determined;
  return (
    <span title={u ? `uncertain identities: ${u.resolutions_n === "not-enumerated" ? "not enumerated" : `${u.relation_set.join(" | ")}, J ${u.jaccard_range?.join("–")}`}` : "all identities verified"}>
      <div className="text-zinc-200">{undetermined ? (u.resolutions_n === "not-enumerated" ? `${c.relation}?` : `{${u.relation_set.join(",")}}`) : c.relation}</div>
      <div>{c.jaccard != null ? c.jaccard.toFixed(2) : "—"}</div>
      {u && u.jaccard_range && u.jaccard_range[0] !== u.jaccard_range[1] && <div className="text-zinc-500">{u.jaccard_range.map((x) => x.toFixed(2)).join("–")}</div>}
      {c.uncaptured_between > 0 && <div className="text-amber-300/80">⚠{c.uncaptured_between}</div>}
    </span>
  );
};

const partCell = (c) => {
  const p = c.participation;
  return (
    <span title={`response ${p.match}${p.end_state ? ` · ${p.end_state}` : ""}`}>
      <div className="text-zinc-300">{p.response_len_chars != null ? `${p.response_len_chars}c` : p.match}</div>
      <div>{p.next_user_delay_s != null ? `↩${fmtGap(p.next_user_delay_s)}` : p.end_state === "session-ended" ? "end" : "?"}</div>
    </span>
  );
};

const ElementRow = ({ row, columns }) => (
  <div className="flex hover:bg-white/[0.02]" data-testid={`lattice-row-${row.element}`}>
    <div className={`sticky left-0 z-10 w-60 flex-shrink-0 truncate bg-[#0A0C12] px-2 py-0.5 font-mono text-[10px] ${row.uncertain ? "italic text-amber-200/70" : "text-zinc-400"}`}
      title={row.uncertain ? `candidates: ${row.candidates.join(", ")}` : row.element}>{row.label}</div>
    {row.cells.map((g, i) => {
      const unc = columns[i].kind === "uncaptured";
      const meta = !row.aggregate && g ? GLYPH[g] : null;
      return (
        <div key={i} style={{ width: CELL, ...(unc ? hatch : {}) }} title={meta?.title}
          className={`flex-shrink-0 border-l border-white/[0.04] text-center font-mono text-[11px] leading-5 ${meta?.cls || ""}`}>
          {row.aggregate ? (g ? <span className="text-[9px] text-zinc-400" title={`present ${g.present} · new ${g.introduced} · withdrawn ${g.withdrawn}`}>{g.present}{g.introduced ? <span className="text-emerald-300">+{g.introduced}</span> : ""}</span> : null) : meta?.ch}
          {row.uncertain && row.mult?.[i] > 1 && <span className="text-[8px] text-amber-200/70">×{row.mult[i]}</span>}
        </div>
      );
    })}
  </div>
);

const Group = ({ type, rows, columns }) => {
  const [open, setOpen] = useState(type !== "codon");
  return (
    <div data-testid={`lattice-group-${type}`}>
      <button onClick={() => setOpen(!open)} className="sticky left-0 flex items-center gap-1 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500 hover:text-zinc-300" data-testid={`lattice-group-toggle-${type}`}>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}{TYPE_LABEL[type] || type} · {rows.filter((r) => !r.uncertain).length}
        {rows.some((r) => r.uncertain) && <span className="normal-case tracking-normal text-amber-200/70"> + {rows.filter((r) => r.uncertain).length} uncertain</span>}
      </button>
      {open && rows.map((r) => <ElementRow key={r.element} row={r} columns={columns} />)}
    </div>
  );
};

export const LatticeGrid = ({ data, loading, showText, onOpen, onOlder, onLatest, paged }) => {
  const columns = data?.columns || [];
  const groups = useMemo(() => {
    const g = {};
    (data?.rows || []).forEach((r) => { (g[r.type] = g[r.type] || []).push(r); });
    return ["seed", "mra", "codon", "history"].filter((t) => g[t]).map((t) => [t, g[t]]);
  }, [data]);
  if (!data) return <div className="font-mono text-xs text-zinc-500" data-testid="lattice-loading">{loading ? "measuring view…" : "no data"}</div>;
  return (
    <div className="rounded-2xl border border-white/10 bg-[#0A0C12]" data-testid="lattice-grid">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="font-mono text-[11px] text-zinc-400">
          <span className="font-cinzel text-base text-zinc-100">{data.presence}</span> · scope {data.scope}
          {data.scope === "S3" && ` · visitor ${String(data.visitor).slice(0, 8)}`} · {columns.filter((c) => c.kind === "entry").length} engagements
          {columns.some((c) => c.kind === "uncaptured") && <span className="ml-2 inline-flex items-center gap-1 text-amber-300/80"><AlertTriangle size={11} />{columns.filter((c) => c.kind === "uncaptured").length} uncaptured turns shown</span>}
        </div>
        <div className="flex gap-2">
          {data.has_more && <button onClick={onOlder} data-testid="lattice-older" className="rounded-full border border-white/10 px-3 py-1 font-mono text-[11px] text-zinc-400 hover:text-zinc-200">← older</button>}
          {paged && <button onClick={onLatest} data-testid="lattice-latest" className="rounded-full border border-white/10 px-3 py-1 font-mono text-[11px] text-zinc-400 hover:text-zinc-200">latest →</button>}
        </div>
      </div>
      {columns.length === 0 ? <div className="px-4 pb-4 font-mono text-xs text-zinc-500">No engagements in this scope yet.</div> : (
        <div className="max-h-[70vh] overflow-auto pb-2">
          <div className="inline-block min-w-full">
            <div className="sticky top-0 z-20 flex bg-[#0A0C12]">
              <div className="sticky left-0 z-10 w-60 flex-shrink-0 bg-[#0A0C12] px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">engagement · Δt · visitor</div>
              {columns.map((c, i) => <ColHead key={i} c={c} prev={columns[i - 1]} onOpen={onOpen} />)}
            </div>
            {groups.map(([t, rows]) => <Group key={t} type={t} rows={rows} columns={columns} />)}
            <Strip label={`relation to predecessor [${data.scope}]`} columns={columns} render={relCell} testid="lattice-relation-strip" />
            {showText && <Strip label="text-only fragments (shared/+new/−gone)" columns={columns} testid="lattice-text-strip"
              render={(c) => c.text_layer ? `${c.text_layer.shared_frag_hashes_n}/+${c.text_layer.introduced_n}/−${c.text_layer.withdrawn_n}` : "—"} />}
            <Strip label="participation · reply / next" columns={columns} render={partCell} testid="lattice-participation-strip" />
          </div>
        </div>
      )}
      <Legend />
    </div>
  );
};

const Legend = () => (
  <div className="flex flex-wrap gap-x-5 gap-y-1 border-t border-white/10 px-4 py-3 font-mono text-[10px] text-zinc-400" data-testid="lattice-legend">
    {Object.entries(GLYPH).map(([k, g]) => <span key={k}><span className={g.cls}>{g.ch}</span> {g.title}</span>)}
    <span><span className="inline-block h-2.5 w-4 align-middle" style={hatch} /> uncaptured turn (exists, context unknown)</span>
    <span>│ thick rule = session boundary</span>
    <span>relation: RCC5 on verified identities · {"{…}"} = several possible under uncertain identities · ? = too many to enumerate</span>
    <span>⚠n = n unobserved turns between this and its predecessor</span>
  </div>
);
```
===== END FILE: frontend/src/components/observatory/LatticeGrid.jsx =====


===== FILE: frontend/src/components/observatory/EvidenceDrawer.jsx =====
```jsx
import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import axios from "axios";
import { X, ChevronDown, ChevronRight } from "lucide-react";
import { API } from "../../App";

const CLASS_ORDER = ["VERIFIED", "CANDIDATES", "UNRESOLVED", "TEXT_ONLY"];

const Mention = ({ m }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-white/[0.04] py-1.5" data-testid={`evidence-mention-${m.mention_id}`}>
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 text-left font-mono text-[11px] text-zinc-300">
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <span className="w-16 text-zinc-500">{m.type}</span>
        <span className="truncate">{m.element || (m.candidates ? `${m.candidates.length} candidates` : `#${m.frag_hash.slice(0, 10)}`)}</span>
        {m.render_matches_current_record === false && <span className="ml-auto text-amber-300/80" title="rendered text differs from the stored record as it reads now">≠ store</span>}
        {m.identity_basis && <span className="ml-auto text-zinc-500" title="identified by name plus current angle (angle may have drifted)">angle tie-break</span>}
      </button>
      {open && (
        <div className="ml-5 mt-1 space-y-1 font-mono text-[10px] text-zinc-500">
          <div>field {m.field}{m.start != null ? ` [${m.start}–${m.end}]` : ""} · frag {m.frag_hash.slice(0, 16)}</div>
          {m.candidates && <div>candidates: {m.candidates.join(", ")}</div>}
          {m.record_fingerprint && <div>record fingerprint {m.record_fingerprint.slice(0, 16)}</div>}
          <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded bg-black/40 p-2 text-zinc-300">{m.evidence_text}</pre>
        </div>
      )}
    </div>
  );
};

const Row = ({ k, v }) => (
  <div className="flex justify-between gap-3 py-0.5"><span className="text-zinc-500">{k}</span><span className="truncate text-right text-zinc-300">{String(v ?? "—")}</span></div>
);

const ScopeBlock = ({ name, s }) => {
  const v = s.verified || {};
  return (
    <div className="rounded-lg border border-white/10 p-2" data-testid={`evidence-scope-${name}`}>
      <div className="mb-1 text-zinc-400">{name} · predecessor {String(s.pred_entry_id).slice(-8)}</div>
      {s.pred_entry_id !== "none-observed" && (<>
        <Row k="relation (verified)" v={v.relation_rcc5} />
        <Row k="jaccard (verified)" v={v.jaccard} />
        <Row k="first-observed / returned" v={`${(v.introduced_first_observed || []).length} / ${(v.returned || []).length}`} />
        <Row k="withdrawn / present-at-both" v={`${(v.withdrawn || []).length} / ${(v.present_at_both || []).length}`} />
        <Row k="adjacent" v={v.adjacent ? "yes" : "no"} />
        <Row k="uncaptured between" v={s.uncaptured_between} />
        {s.uncertainty && <Row k="with uncertain identities" v={s.uncertainty.resolutions_n === "not-enumerated" ? "not enumerated" : `${s.uncertainty.relation_set.join(" | ")} · J ${s.uncertainty.jaccard_range?.join("–")}`} />}
      </>)}
    </div>
  );
};

export const EvidenceDrawer = ({ entryId, onClose }) => {
  const [e, setE] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    let live = true;
    setE(null); setErr(null);
    if (entryId) {
      axios.get(`${API}/observatory/entry/${encodeURIComponent(entryId)}`)
        .then(({ data }) => live && setE(data))
        .catch(() => live && setErr("Could not load this entry."));
    }
    return () => { live = false; };
  }, [entryId]);
  useEffect(() => {
    if (!entryId) return undefined;
    const onKey = (ev) => ev.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [entryId, onClose]);
  if (!entryId) return null;
  const groups = CLASS_ORDER.map((c) => [c, (e?.mentions || []).filter((m) => m.class === c)]);
  return createPortal(
    <>
    <div className="fixed inset-0 z-[70] bg-black/40" onClick={onClose} data-testid="evidence-backdrop" />
    <div className="fixed inset-y-0 right-0 z-[71] w-full max-w-xl overflow-y-auto border-l border-white/10 bg-[#07080C]/95 p-5 backdrop-blur-xl" data-testid="evidence-drawer">
      <div className="mb-4 flex items-center justify-between">
        <div className="font-cinzel text-lg text-zinc-100">Evidence</div>
        <button onClick={onClose} data-testid="evidence-close" className="rounded-lg border border-white/10 p-1.5 text-zinc-400 hover:text-zinc-100"><X size={16} /></button>
      </div>
      {err ? <div className="font-mono text-xs text-amber-300" data-testid="evidence-error">{err}</div> : !e ? <div className="font-mono text-xs text-zinc-500">loading…</div> : (
        <div className="space-y-4 font-mono text-[11px]">
          <section className="rounded-lg border border-white/10 p-3" data-testid="evidence-source">
            <Row k="presence · turn" v={`${e.chronology.presence} · #${e.chronology.exchange_index}`} />
            <Row k="time" v={new Date(e.chronology.timestamp).toLocaleString()} />
            <Row k="session" v={e.chronology.session_id} />
            <Row k="visitor" v={`${e.visitor.resolved_visitor} (${e.visitor.resolution})`} />
            <Row k="provenance" v={e.source.provenance_id} />
            <Row k="input integrity" v={e.source.integrity_verified ? "hash verified" : "MISMATCH"} />
            <Row k="chain position" v={`#${e.chronology.ordinal} · ${e.chain.entry_hash.slice(0, 16)}`} />
            <Row k="method" v={`v${e.derivation_version} · ${e.norm_version} · run ${String(e.run_id).slice(0, 8)} · commit ${String(e.run?.code_commit).slice(0, 8)}`} />
            <Row k="response" v={`${e.participation.match} · ${e.participation.response_len_chars ?? "—"} chars · ${e.participation.end_state}`} />
            {e.gaps.length > 0 && <Row k="gaps" v={e.gaps.join(", ")} />}
          </section>
          <section className="grid gap-2" data-testid="evidence-scopes">
            {["S1", "S2", "S3"].map((s) => <ScopeBlock key={s} name={s} s={e.scopes[s]} />)}
          </section>
          {groups.map(([c, ms]) => ms.length > 0 && (
            <section key={c} data-testid={`evidence-class-${c}`}>
              <div className="mb-1 uppercase tracking-widest text-zinc-500">{c.replace("_", "-").toLowerCase()} · {ms.length}</div>
              {ms.map((m) => <Mention key={m.mention_id} m={m} />)}
            </section>
          ))}
        </div>
      )}
    </div>
    </>,
    document.body
  );
};
```
===== END FILE: frontend/src/components/observatory/EvidenceDrawer.jsx =====


===== FILE: frontend/src/components/observatory/LedgerStatus.jsx =====
```jsx
import React from "react";
import { ShieldCheck, ShieldAlert, RefreshCw } from "lucide-react";

const fmt = (t) => (t ? new Date(t).toLocaleString() : "—");

export const LedgerStatus = ({ status }) => {
  const last = status?.runs?.[0];
  const lastWork = status?.last_work_run;
  const ok = last ? last.status === "ok" : null;
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5" data-testid="ledger-status">
      <Cell label="Engagements measured" value={status?.ledger_entries ?? "—"} testid="ledger-entries" />
      <Cell label="Awaiting settlement" value={status?.pending ?? "—"} testid="ledger-pending"
        hint="Turns whose outcome is not yet known (next message, session end, or 24h)" />
      <Cell label="Last observer run" value={last ? `${fmt(last.finished_at || last.started_at)}` : "—"} testid="ledger-last-run"
        hint={last ? `${last.trigger} · ${last.status}` : ""} />
      <Cell label="Last new measurements" value={lastWork ? `${lastWork.processed} · ${fmt(lastWork.finished_at)}` : "—"} testid="ledger-last-work" />
      <div className="rounded-xl border border-white/10 bg-[#0A0C12]/80 p-3" data-testid="ledger-health">
        <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">Observer</div>
        <div className={`mt-1 flex items-center gap-2 font-mono text-sm ${ok === false ? "text-amber-300" : "text-emerald-300"}`}>
          {status?.running ? <RefreshCw size={14} className="animate-spin" /> : ok === false ? <ShieldAlert size={14} /> : <ShieldCheck size={14} />}
          {status?.running ? "measuring…" : ok === false ? "last run failed — will retry" : "automatic · hourly"}
        </div>
      </div>
    </div>
  );
};

const Cell = ({ label, value, hint, testid }) => (
  <div className="rounded-xl border border-white/10 bg-[#0A0C12]/80 p-3" title={hint} data-testid={testid}>
    <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">{label}</div>
    <div className="mt-1 truncate font-mono text-sm text-zinc-200">{value}</div>
    {hint && <div className="mt-0.5 truncate font-mono text-[10px] text-zinc-600">{hint}</div>}
  </div>
);
```
===== END FILE: frontend/src/components/observatory/LedgerStatus.jsx =====

— END OF PART 3 OF 4 —
