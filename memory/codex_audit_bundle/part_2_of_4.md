# SANCTUARY 1.0 · OBSERVATORY AUDIT BUNDLE · PART 2 OF 4
## Backend core: maths, identification, derivation engine
Files in this part:
- `backend/observatory_ledger/__init__.py`
- `backend/observatory_ledger/measure.py`
- `backend/observatory_ledger/recover.py`
- `backend/observatory_ledger/derive.py`

Codex: part 2 of 4. Continue collecting; audit once all 4 parts are received.


===== FILE: backend/observatory_ledger/__init__.py =====
```python
"""Observatory relational-history ledger (read-only observer of Sanctuary records)."""
DERIVATION_VERSION = "1.0.0"
NORM_VERSION = "norm-v1"
ENUM_CAP = 65536
```
===== END FILE: backend/observatory_ledger/__init__.py =====


===== FILE: backend/observatory_ledger/measure.py =====
```python
"""Pure measurement math for the Observatory ledger (no I/O).

RCC5-analogous relations on NON-EMPTY finite sets; empty cases reported
explicitly. Introduced = first-observed ⊔ returned (scope-relative).
"""
from itertools import product
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

EMPTY_BOTH, EMPTY_PRED, EMPTY_CURR = "∅∅", "∅·", "·∅"


def rcc5(x: Set, y: Set) -> str:
    """Relation of predecessor set x to current set y."""
    if not x and not y:
        return EMPTY_BOTH
    if not x:
        return EMPTY_PRED
    if not y:
        return EMPTY_CURR
    if x == y:
        return "EQ"
    if not (x & y):
        return "DR"
    if x < y:
        return "PP"
    if y < x:
        return "PPi"
    return "PO"


def jaccard(x: Set, y: Set) -> Optional[float]:
    union = x | y
    if not union:
        return None
    return round(len(x & y) / len(union), 6)


def transform(pred: Set, cur: Set, earlier_in_scope: Dict[str, Tuple[int, str]]):
    """earlier_in_scope: element -> (ordinal, entry_id) of its latest appearance
    in scope strictly BEFORE the predecessor."""
    introduced = cur - pred
    returned = sorted(e for e in introduced if e in earlier_in_scope)
    first = sorted(introduced - set(returned))
    return {
        "introduced_first_observed": first,
        "returned": returned,
        "withdrawn": sorted(pred - cur),
        "present_at_both": sorted(pred & cur),
        "relation_rcc5": rcc5(pred, cur),
        "jaccard": jaccard(pred, cur),
    }


def enumerate_resolutions(
    pred_verified: Set, cur_verified: Set,
    pred_uncertain: Sequence[Sequence[str]], cur_uncertain: Sequence[Sequence[str]],
    cap: int,
):
    """Evaluate every identity resolution of CANDIDATES mentions.
    Each uncertain mention is an independent variable over its candidate list."""
    variables = [list(c) for c in pred_uncertain] + [list(c) for c in cur_uncertain]
    if not variables:
        return None
    n_total_vars = len(variables)
    # Exact reduction: a mention whose candidates touch no verified element and no
    # other mention's candidates is always one distinct element on its own side.
    pred_verified, cur_verified = set(pred_verified), set(cur_verified)
    known = pred_verified | cur_verified
    owners: Dict[str, int] = {}
    for v in variables:
        for c in set(v):
            owners[c] = owners.get(c, 0) + 1
    keep_p, keep_c = [], []
    for i, v in enumerate(variables):
        free = not (set(v) & known) and all(owners[c] == 1 for c in set(v))
        side_pred = i < len(pred_uncertain)
        if free:
            (pred_verified if side_pred else cur_verified).add(f"__free{i}")
        else:
            (keep_p if side_pred else keep_c).append(v)
    variables = keep_p + keep_c
    n_pred = len(keep_p)
    total = 1
    for v in variables:
        total *= max(1, len(v))
    if total > cap:
        return {"mentions_n": n_total_vars, "interacting_n": len(variables), "resolutions_n": "not-enumerated",
                "relation_set": [], "jaccard_range": None, "counts_range": None,
                "determined": False}
    rels, js, intro, wd, both = set(), [], [], [], []
    for combo in product(*variables):
        p = set(pred_verified) | set(combo[:n_pred])
        c = set(cur_verified) | set(combo[n_pred:])
        rels.add(rcc5(p, c))
        j = jaccard(p, c)
        if j is not None:
            js.append(j)
        intro.append(len(c - p)); wd.append(len(p - c)); both.append(len(p & c))
    rng = lambda a: [min(a), max(a)] if a else None
    return {
        "mentions_n": n_total_vars, "interacting_n": len(variables), "resolutions_n": total,
        "relation_set": sorted(rels), "jaccard_range": rng(js),
        "counts_range": {"introduced": rng(intro), "withdrawn": rng(wd), "present_at_both": rng(both)},
        "determined": len(rels) == 1,
    }


def per_type(pred: Iterable[str], cur: Iterable[str]) -> Dict[str, dict]:
    """Relation per element type (type = prefix before ':')."""
    def split(s):
        out: Dict[str, Set[str]] = {}
        for e in s:
            out.setdefault(e.split(":", 1)[0], set()).add(e)
        return out
    ps, cs = split(pred), split(cur)
    return {t: {"relation_rcc5": rcc5(ps.get(t, set()), cs.get(t, set())),
                "jaccard": jaccard(ps.get(t, set()), cs.get(t, set()))}
            for t in sorted(set(ps) | set(cs))}


def text_layer(pred: Iterable[str], cur: Iterable[str]) -> dict:
    p, c = set(pred), set(cur)
    return {"shared_frag_hashes_n": len(p & c), "introduced_n": len(c - p), "withdrawn_n": len(p - c)}
```
===== END FILE: backend/observatory_ledger/measure.py =====


===== FILE: backend/observatory_ledger/recover.py =====
```python
"""Locate and identify context mentions inside one provenance record (no I/O).

Evidence classes: VERIFIED | CANDIDATES | TEXT_ONLY | UNRESOLVED.
Only VERIFIED mentions enter the record-layer sets.
"""
import hashlib
import json
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

ANCHORS = [
    ("seed", "[CONTINUITY"),
    ("mra", "## What has stayed with you"),
    ("cache", "## SESSION CACHE MRA"),
    ("council", "## Elsewhere in the shared field"),
    ("bio", "[RUNNING BIO"),
    ("pointer", "When you were last here:"),
    ("mem0", "[FIELD MEMORY"),
]
TEXT_ONLY_TYPES = {"cache", "council", "bio", "pointer", "mem0"}
_MRA_LINE = re.compile(r'^[★◆]\s*"(.*)"\s*→\s*"(.*?)"(?:\s*\[.*\])?\s*$')


def norm(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s or "")).strip()


def h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def canonical_hash(obj) -> str:
    return h(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str))


def sections(text: str) -> List[Tuple[str, int, int]]:
    """(type, start, end) spans in positional order; a span ends at the next anchor."""
    found = sorted((text.find(a), t) for t, a in ANCHORS if text.find(a) != -1)
    return [(t, i, found[k + 1][0] if k + 1 < len(found) else len(text))
            for k, (i, t) in enumerate(found)]


def _lines(text: str, start: int, end: int):
    """Yield (line, abs_start, abs_end) for non-empty lines in [start, end)."""
    pos = start
    for raw in text[start:end].split("\n"):
        s, e = pos, pos + len(raw)
        pos = e + 1
        if raw.strip():
            yield raw, s, e


def _text_block_lines(text, start, end):
    """Text-only fragments: lines after the header, stopping at a block terminator."""
    out = []
    for i, (ln, s, e) in enumerate(_lines(text, start, end)):
        if i == 0:
            continue
        st = ln.strip()
        if st == "---" or (st.startswith("## ") or (st.startswith("[") and st.endswith("]") and i > 0)):
            break
        out.append((ln, s, e))
    return out


def _mention(mid, typ, field, s, e, frag, cls, element=None, candidates=None, extra=None):
    m = {"mention_id": mid, "type": typ, "field": field, "start": s, "end": e,
         "frag_hash": h(norm(frag)), "class": cls, "element": element,
         "candidates": candidates}
    if extra:
        m.update(extra)
    return m


def recover(prov: dict, idx: dict, session_msgs: List[dict]) -> Tuple[List[dict], List[str]]:
    """Return (mentions, gap_codes). idx holds store indexes built by derive."""
    comp = prov.get("components") or {}
    am = prov.get("assembled_messages") or []
    sysp = (am[0].get("content") or "") if am and am[0].get("role") == "system" else (comp.get("system_prompt") or "")
    field = "assembled_messages[0].content"
    mentions, gaps, n = [], [], 0

    def nid():
        nonlocal n
        n += 1
        return f"m{n}"

    for typ, s0, e0 in sections(sysp):
        if typ == "seed":
            got = 0
            for ln, s, e in _lines(sysp, s0, e0):
                if not ln.startswith("Field state:"):
                    continue
                val = norm(ln[len("Field state:"):])
                if not val:
                    continue
                got += 1
                ids = idx["seed_by_field_state"].get(val, [])
                if len(ids) == 1:
                    mentions.append(_mention(nid(), "seed", field, s, e, ln, "VERIFIED", element=f"seed:{ids[0]}",
                                             extra={"record_fingerprint": idx["seed_fp"][ids[0]],
                                                    "render_matches_current_record": True}))
                elif ids:
                    mentions.append(_mention(nid(), "seed", field, s, e, ln, "CANDIDATES",
                                             candidates=[f"seed:{i}" for i in ids]))
                else:
                    mentions.append(_mention(nid(), "seed", field, s, e, ln, "UNRESOLVED",
                                             extra={"render_matches_current_record": False}))
            if not got:
                gaps.append("segmentation-failed:seed")
        elif typ == "mra":
            for ln, s, e in _lines(sysp, s0, e0):
                mm = _MRA_LINE.match(ln.strip())
                if not mm:
                    continue
                key = (norm(mm.group(1)), norm(mm.group(2)))
                ids = idx["mra_by_pair"].get(key, [])
                if len(ids) == 1:
                    mentions.append(_mention(nid(), "mra", field, s, e, ln, "VERIFIED", element=f"mra:{ids[0]}",
                                             extra={"record_fingerprint": idx["mra_fp"][ids[0]],
                                                    "render_matches_current_record": True}))
                elif ids:
                    mentions.append(_mention(nid(), "mra", field, s, e, ln, "CANDIDATES",
                                             candidates=[f"mra:{i}" for i in ids]))
                else:
                    mentions.append(_mention(nid(), "mra", field, s, e, ln, "UNRESOLVED",
                                             extra={"render_matches_current_record": False}))
        else:
            for ln, s, e in _text_block_lines(sysp, s0, e0):
                mentions.append(_mention(nid(), typ, field, s, e, ln, "TEXT_ONLY",
                                         extra={"render_matches_current_record": "n/a"}))

    sel = comp.get("codon_selection") or {}
    for k, c in enumerate(sel.get("codons") or []):
        name = c.get("name")
        recs = idx["codon_by_name"].get(name, [])
        f = f"components.codon_selection.codons[{k}]"
        frag = json.dumps(c, ensure_ascii=False, sort_keys=True, default=str)
        if len(recs) == 1:
            r = recs[0]
            mentions.append(_mention(nid(), "codon", f, None, None, frag, "VERIFIED", element=f"codon:{r['id']}",
                                     extra={"record_fingerprint": r["fp"],
                                            "render_matches_current_record": r.get("target_angle") == c.get("target_angle")}))
        elif recs:
            tie = [r for r in recs if r.get("target_angle") == c.get("target_angle")]
            if len(tie) == 1:
                mentions.append(_mention(nid(), "codon", f, None, None, frag, "VERIFIED", element=f"codon:{tie[0]['id']}",
                                         extra={"record_fingerprint": tie[0]["fp"], "identity_basis": "name+current-angle",
                                                "render_matches_current_record": True}))
            else:
                mentions.append(_mention(nid(), "codon", f, None, None, frag, "CANDIDATES",
                                         candidates=[f"codon:{r['id']}" for r in (tie or recs)]))
        else:
            mentions.append(_mention(nid(), "codon", f, None, None, frag, "UNRESOLVED"))

    by_hash: Dict[str, List[str]] = {}
    for m in session_msgs:
        by_hash.setdefault(h(norm(m.get("content"))), []).append(m.get("id"))
    hist = am[1:-1] if len(am) >= 2 else []
    for k, m in enumerate(hist):
        ids = by_hash.get(h(norm(m.get("content"))), [])
        f = f"assembled_messages[{k + 1}]"
        frag = m.get("content") or ""
        if len(ids) == 1:
            mentions.append(_mention(nid(), "history", f, None, None, frag, "VERIFIED", element=f"history:{ids[0]}"))
        elif ids:
            mentions.append(_mention(nid(), "history", f, None, None, frag, "CANDIDATES",
                                     candidates=[f"history:{i}" for i in ids]))
        else:
            mentions.append(_mention(nid(), "history", f, None, None, frag, "UNRESOLVED"))
            if "history-hash-mismatch" not in gaps:
                gaps.append("history-hash-mismatch")
    return mentions, gaps


def evidence_text(prov: dict, mention: dict) -> str:
    """Exact evidence for a mention, re-read live from the provenance record."""
    f = mention["field"]
    am = prov.get("assembled_messages") or []
    if f == "assembled_messages[0].content":
        txt = (am[0].get("content") or "") if am else ""
        return txt[mention["start"]:mention["end"]]
    m = re.match(r"assembled_messages\[(\d+)\]", f)
    if m:
        i = int(m.group(1))
        return (am[i].get("content") or "") if i < len(am) else ""
    m = re.match(r"components\.codon_selection\.codons\[(\d+)\]", f)
    if m:
        codons = ((prov.get("components") or {}).get("codon_selection") or {}).get("codons") or []
        i = int(m.group(1))
        return json.dumps(codons[i], ensure_ascii=False, sort_keys=True, default=str) if i < len(codons) else ""
    return ""
```
===== END FILE: backend/observatory_ledger/recover.py =====


===== FILE: backend/observatory_ledger/derive.py =====
```python
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

from . import DERIVATION_VERSION, NORM_VERSION, ENUM_CAP
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
        await self.entries.create_index([("derivation_version", 1), ("chronology.presence", 1), ("chronology.ordinal", 1)])


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
                                              "angle_backfilled_at": 1}):
        codon_by.setdefault(c.get("name"), []).append({
            "id": str(c["_id"]), "target_angle": c.get("target_angle"),
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


def scope_measure(scope: str, cur: dict, history: List[dict], unc: List[dict]) -> dict:
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
    out["gaps"] = gaps
    return out


# ---------------------------------------------------------------- entry
def build_entry(prov: dict, idx: dict, sess: Optional[dict], history: List[dict], unc: List[dict],
                part: dict, ordinal: int) -> dict:
    sid = prov.get("session_id")
    mentions, gaps = recover(prov, idx, [m for m in (sess or {}).get("messages", []) if m["content"] is not None])
    verified = sorted({m["element"] for m in mentions if m["class"] == "VERIFIED"})
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
    cur = {"entry_id": f'{DERIVATION_VERSION}:{prov["provenance_id"]}', "session_id": sid,
           "presence": prov.get("presence"), "visitor": canon or uid, "ts": ts,
           "verified": verified, "uncertain": uncertain, "text": text}
    scopes = {s: scope_measure(s, cur, history, unc) for s in ("S1", "S2", "S3")}
    if part["match"] != "matched":
        gaps.append("response-unmatched")
    if recomputed != prov.get("content_hash"):
        gaps.append("provenance-hash-mismatch")
    return {
        "entry_id": cur["entry_id"], "derivation_version": DERIVATION_VERSION, "norm_version": NORM_VERSION,
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
        "availability": {"verified": verified, "uncertain": uncertain, "text": text,
                         "counts_by_class": cls_counts, "counts_by_type": type_counts},
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
            "text": e["availability"]["text"]}


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


# ---------------------------------------------------------------- run
async def run_once(db, trigger: str = "manual", ledger: Optional[Ledger] = None,
                   max_records: Optional[int] = None, now: Optional[datetime] = None) -> dict:
    ledger = ledger or Ledger(db)
    await ledger.ensure_indexes()
    run_id = str(uuid.uuid4())
    if not await acquire_lock(ledger, run_id):
        return {"status": "skipped-locked", "run_id": None}
    now = now or datetime.now(timezone.utc)
    started = datetime.now(timezone.utc)
    run = {"run_id": run_id, "trigger": trigger, "derivation_version": DERIVATION_VERSION,
           "norm_version": NORM_VERSION, "enum_cap": ENUM_CAP, "code_commit": _code_commit(),
           "started_at": started, "status": "running", "unavailable_evidence": UNAVAILABLE_EVIDENCE}
    await ledger.runs.insert_one(dict(run))
    processed, unsettled, errors = 0, 0, []
    try:
        idx = await build_indexes(db)
        pres_by_sess = {}
        async for p in db.turn_provenance.find({}, {"session_id": 1, "presence": 1}):
            pres_by_sess.setdefault(p.get("session_id"), p.get("presence"))
        first = await db.turn_provenance.find_one({}, {"timestamp": 1}, sort=[("_id", 1)])
        window_start = parse_ts(first["timestamp"]) if first else None
        sessions = await load_sessions(db, pres_by_sess)
        captured_turns = set(await db.turn_provenance.distinct("turn_id"))
        for presence in sorted(await db.turn_provenance.distinct("presence")):
            last = await ledger.entries.find_one(
                {"derivation_version": DERIVATION_VERSION, "chronology.presence": presence},
                sort=[("chronology.ordinal", -1)])
            q = {"presence": presence}
            if last:
                from bson import ObjectId
                q["_id"] = {"$gt": ObjectId(last["source"]["provenance_oid"])}
            if not await db.turn_provenance.count_documents(q, limit=1):
                continue
            history = [_hist_item(e) async for e in ledger.entries.find(
                {"derivation_version": DERIVATION_VERSION, "chronology.presence": presence},
                {"entry_id": 1, "chronology": 1, "visitor": 1, "availability": 1}).sort("chronology.ordinal", 1)]
            prev_hash = last["chain"]["entry_hash"] if last else "GENESIS"
            ordinal = last["chronology"]["ordinal"] + 1 if last else 0
            unc = []
            for sid, s in sessions.items():
                if s["presence"] != presence:
                    continue
                vis = s["user_id"]
                vis = idx["aliases"].get(vis, vis)
                for m in s["messages"]:
                    if m["role"] == "assistant" and m["id"] not in captured_turns and m["ts"] and \
                            (window_start is None or m["ts"] >= window_start):
                        unc.append({"ts": m["ts"], "session_id": sid, "visitor": vis})
            async for prov in db.turn_provenance.find(q).sort("_id", 1):
                if max_records is not None and processed >= max_records:
                    break
                sess = sessions.get(prov.get("session_id"))
                part, settled = participation(prov, sess, now)
                if not settled:
                    unsettled += 1
                    break  # frontier: keep chain in provenance order
                entry = await asyncio.to_thread(build_entry, prov, idx, sess, history, unc, part, ordinal)
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
                await asyncio.sleep(0)
            if max_records is not None and processed >= max_records:
                break
        status = "ok"
    except Exception as e:  # recorded; next run resumes from the ledger frontier
        logger.exception("[OBSERVATORY] run failed")
        errors.append(repr(e))
        status = "failed"
    finally:
        await release_lock(ledger, run_id)
    summary = {"status": status, "processed": processed, "unsettled_frontiers": unsettled,
               "errors": errors[:20], "finished_at": datetime.now(timezone.utc),
               "ledger_total": await ledger.entries.count_documents({"derivation_version": DERIVATION_VERSION})}
    await ledger.runs.update_one({"run_id": run_id}, {"$set": summary})
    logger.info(f"[OBSERVATORY] run {run_id[:8]} {trigger}: {status}, processed={processed}")
    return {"run_id": run_id, **summary}


async def catch_up(db, trigger: str, ledger: Optional[Ledger] = None, delay_s: float = 0) -> dict:
    """Run until nothing new is settled (covers suspension, restarts, missed ticks)."""
    if delay_s:
        await asyncio.sleep(delay_s)
    last = {}
    for _ in range(20):
        last = await run_once(db, trigger, ledger)
        if last.get("status") == "skipped-locked" and trigger == "startup-catch-up":
            # A lock left by a crashed process expires after LOCK_TTL; retry once then.
            await asyncio.sleep(LOCK_TTL.total_seconds() + 5)
            last = await run_once(db, trigger, ledger)
        if last.get("status") != "ok" or not last.get("processed"):
            break
    return last


async def verify(db, ledger: Optional[Ledger] = None, check_drift: bool = False) -> dict:
    """Chain integrity + Tier-1 provenance integrity (+ optional Tier-2 drift)."""
    ledger = ledger or Ledger(db)
    out = {"presences": {}, "ok": True, "provenance_changed": [], "drift": None}
    drift_n = checked = 0
    for presence in sorted(await ledger.entries.distinct("chronology.presence", {"derivation_version": DERIVATION_VERSION})):
        prev, n, broken = "GENESIS", 0, None
        async for e in ledger.entries.find({"derivation_version": DERIVATION_VERSION, "chronology.presence": presence}
                                           ).sort("chronology.ordinal", 1):
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
        out["presences"][presence] = {"entries": n, "chain_ok": broken is None, "broken_at": broken}
        out["ok"] = out["ok"] and broken is None
    from bson import ObjectId
    batch = []

    async def check(items):
        found = {str(p["_id"]): p async for p in db.turn_provenance.find(
            {"_id": {"$in": [ObjectId(x["source"]["provenance_oid"]) for x in items]}}, {"assembled_messages": 1})}
        for x in items:
            p = found.get(x["source"]["provenance_oid"])
            if not p or h(json.dumps(p.get("assembled_messages") or [], ensure_ascii=False)) != x["source"]["content_hash_recomputed"]:
                out["provenance_changed"].append(x["entry_id"])

    async for e in ledger.entries.find({"derivation_version": DERIVATION_VERSION}, {"entry_id": 1, "source": 1}):
        batch.append(e)
        if len(batch) >= 200:
            await check(batch)
            batch = []
    if batch:
        await check(batch)
    out["ok"] = out["ok"] and not out["provenance_changed"]
    if check_drift:
        out["drift"] = {"verified_mentions_checked": checked, "source_drifted": drift_n}
    return out
```
===== END FILE: backend/observatory_ledger/derive.py =====

— END OF PART 2 OF 4 —
