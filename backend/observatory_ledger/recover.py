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


_HEADER = re.compile(r"^(## |\[[A-Z])")


def _after_terminator(text, s0, e0, kept):
    """Lines a text-only block dropped after its terminator: (same-shape continuation lines, other lines count)."""
    body = list(_lines(text, s0, e0))[1:]
    rest = body[len(kept) + 1:]
    shape = kept[0][0].strip()[:2] if kept else None
    cont, other, stopped = [], 0, False
    for ln, s, e in rest:
        st = ln.strip()
        if _HEADER.match(st) or st == "---":
            stopped = True
        if not stopped and shape and st[:2] == shape:
            cont.append((ln, s, e))
        else:
            other += 1
    return cont, other


def recover(prov: dict, idx: dict, session_msgs: List[dict], profile: Optional[dict] = None,
            report: Optional[dict] = None) -> Tuple[List[dict], List[str]]:
    """Return (mentions, gap_codes). idx holds store indexes built by derive.
    profile/report: version flags; when profile['completeness'], per-section completeness is written to report."""
    profile = profile or {}
    complete_mode = profile.get("completeness")
    comp = prov.get("components") or {}
    am = prov.get("assembled_messages") or []
    sysp = (am[0].get("content") or "") if am and am[0].get("role") == "system" else (comp.get("system_prompt") or "")
    field = "assembled_messages[0].content" if am and am[0].get("role") == "system" else "components.system_prompt"
    if not complete_mode:
        field = "assembled_messages[0].content"
    mentions, gaps, n = [], [], 0
    sec_report: Dict[str, dict] = {}

    def nid():
        nonlocal n
        n += 1
        return f"m{n}"

    def note(typ, **kw):
        r = sec_report.setdefault(typ, {"status": "complete", "unresolved_n": 0})
        for k, v in kw.items():
            r[k] = r.get(k, 0) + v
        if r["unresolved_n"] or r.get("missing_field_state"):
            r["status"] = "partial"

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
                if complete_mode:
                    note("seed", missing_field_state=1)
            elif complete_mode:
                note("seed")
        elif typ == "mra":
            for ln, s, e in _lines(sysp, s0, e0):
                mm = _MRA_LINE.match(ln.strip())
                if not mm:
                    if complete_mode and ln.strip()[:1] in ("★", "◆"):
                        mentions.append(_mention(nid(), "mra", field, s, e, ln, "UNRESOLVED",
                                                 extra={"reason": "malformed-bullet", "render_matches_current_record": "n/a"}))
                        note("mra", unresolved_n=1)
                    elif complete_mode and not ln.lstrip().startswith("## What has stayed with you"):
                        note("mra", non_bullet_lines_n=1)
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
                    if complete_mode:
                        note("mra", unresolved_n=1)
            if complete_mode:
                note("mra")
        else:
            kept = _text_block_lines(sysp, s0, e0)
            for ln, s, e in kept:
                mentions.append(_mention(nid(), typ, field, s, e, ln, "TEXT_ONLY",
                                         extra={"render_matches_current_record": "n/a"}))
            if complete_mode:
                cont, other = _after_terminator(sysp, s0, e0, kept)
                for ln, s, e in cont:
                    mentions.append(_mention(nid(), typ, field, s, e, ln, "UNRESOLVED",
                                             extra={"reason": "after-terminator-same-shape",
                                                    "render_matches_current_record": "n/a"}))
                note(typ, unresolved_n=len(cont), unattributed_lines_n=other)

    if complete_mode:
        found = {t for t, _, _ in sections(sysp)}
        for t, _ in ANCHORS:
            if t not in found:
                sec_report[t] = {"status": "absent", "unresolved_n": 0}
        for t, r in sec_report.items():
            if r["status"] == "partial":
                gaps.append(f"partial-section:{t}:{r['unresolved_n']}")

    pres = (prov.get("presence") or "").lower()
    sel = comp.get("codon_selection") or {}
    for k, c in enumerate(sel.get("codons") or []):
        name = c.get("name")
        recs = idx["codon_by_name"].get(name, [])
        f = f"components.codon_selection.codons[{k}]"
        frag = json.dumps(c, ensure_ascii=False, sort_keys=True, default=str)
        if profile.get("codon_scope"):
            mentions.append(_codon_scoped(nid(), f, frag, c, recs, pres))
            continue
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
    if report is not None and complete_mode:
        report["completeness"] = {t: sec_report[t] for t in sorted(sec_report)}
        report["complete"] = not any(r["status"] == "partial" for r in sec_report.values())
    return mentions, gaps


def _codon_scoped(mid, f, frag, c, recs, pres):
    """C3': identity within the loader's selection scope (record presence in {rendering presence, 'field'}).
    The current angle is only a declared, mutable secondary basis."""
    scoped = [r for r in recs if r.get("presence") in (pres, "field")]
    if len(scoped) == 1:
        r = scoped[0]
        return _mention(mid, "codon", f, None, None, frag, "VERIFIED", element=f"codon:{r['id']}",
                        extra={"record_fingerprint": r["fp"], "identity_basis": "name+loader-scope",
                               "render_matches_current_record": r.get("target_angle") == c.get("target_angle")})
    if scoped:
        tie = [r for r in scoped if r.get("target_angle") == c.get("target_angle")]
        if len(tie) == 1:
            return _mention(mid, "codon", f, None, None, frag, "VERIFIED", element=f"codon:{tie[0]['id']}",
                            extra={"record_fingerprint": tie[0]["fp"], "identity_basis": "mutable-angle",
                                   "conditional": True, "render_matches_current_record": True})
        return _mention(mid, "codon", f, None, None, frag, "CANDIDATES",
                        candidates=[f"codon:{r['id']}" for r in (tie or scoped)])
    return _mention(mid, "codon", f, None, None, frag, "UNRESOLVED",
                    extra={"reason": "outside-loader-scope" if recs else "name-not-in-store"})


def evidence_text(prov: dict, mention: dict) -> str:
    """Exact evidence for a mention, re-read live from the provenance record."""
    f = mention["field"]
    am = prov.get("assembled_messages") or []
    if f in ("assembled_messages[0].content", "components.system_prompt"):
        txt = ((am[0].get("content") or "") if am else "") if f.startswith("assembled") else \
            ((prov.get("components") or {}).get("system_prompt") or "")
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
