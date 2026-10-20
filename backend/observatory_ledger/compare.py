"""Cross-version comparison (aggregate counts only): Stage-1 invariance and Stage-2 mathematical delta."""
from collections import Counter
from typing import Dict

SCOPES = ("S1", "S2", "S3")
TIME_FIELDS = ("uncaptured_between", "uncaptured_unknown_visitor", "uncaptured_unplaceable")


def _strip(v, version):
    p = f"{version}:"
    return v[len(p):] if isinstance(v, str) and v.startswith(p) else v


def _math(entry: dict, version: str) -> dict:
    """Set-mathematics outputs of one entry, version-neutral; excludes timestamp/gap-derived fields."""
    a = entry["availability"]
    out = {"verified": a["verified"], "uncertain": a["uncertain"], "text": a["text"], "scopes": {}}
    for s in SCOPES:
        sc = entry["scopes"][s]
        v = dict(sc.get("verified") or {})
        v.pop("adjacent", None)
        v["returned"] = [{"element": r["element"], "last_seen": _strip(r["last_seen_entry_id"], version),
                          "d_captured": r["d_captured"]} for r in v.get("returned", [])]
        out["scopes"][s] = {"pred": _strip(sc.get("pred_entry_id"), version), "verified": v,
                            "uncertainty": sc.get("uncertainty"), "text_layer": sc.get("text_layer")}
    return out


def _timing(entry: dict) -> dict:
    out = {"participation": entry["participation"], "scopes": {}}
    for s in SCOPES:
        sc = entry["scopes"][s]
        out["scopes"][s] = {**{k: sc.get(k) for k in TIME_FIELDS if k != "uncaptured_unplaceable"},
                            "adjacent": (sc.get("verified") or {}).get("adjacent"),
                            "d_uncaptured": [r["d_uncaptured"] for r in (sc.get("verified") or {}).get("returned", [])]}
    return out


async def _load(ledger, version) -> Dict[str, dict]:
    return {e["source"]["provenance_oid"]: e async for e in
            ledger.entries.find({"derivation_version": version}, {"_id": 0})}


async def invariance(ledger_a, va: str, ledger_b, vb: str) -> dict:
    A, B = await _load(ledger_a, va), await _load(ledger_b, vb)
    common = set(A) & set(B)
    r = Counter()
    for oid in common:
        ea, eb = A[oid], B[oid]
        ma, mb = _math(ea, va), _math(eb, vb)
        r["math_entries_differing"] += ma != mb
        for k in ("verified", "uncertain", "text"):
            r[f"math_diff:{k}"] += ma[k] != mb[k]
        for s in SCOPES:
            for k in ("pred", "verified", "uncertainty", "text_layer"):
                r[f"math_diff:{s}.{k}"] += ma["scopes"][s][k] != mb["scopes"][s][k]
        ta, tb = _timing(ea), _timing(eb)
        r["timing_entries_differing"] += ta != tb
        for s in SCOPES:
            r[f"timing_diff:{s}.adjacent"] += ta["scopes"][s]["adjacent"] != tb["scopes"][s]["adjacent"]
            r[f"timing_diff:{s}.uncaptured"] += ta["scopes"][s]["uncaptured_between"] != tb["scopes"][s]["uncaptured_between"]
            r[f"timing_info:{s}.unplaceable_counted"] += bool((eb["scopes"][s].get("uncaptured_unplaceable") or 0))
        r["timing_diff:participation"] += ta["participation"] != tb["participation"]
        ca = Counter((m["type"], m["class"], m.get("reason")) for m in ea["mentions"])
        cb = Counter((m["type"], m["class"], m.get("reason")) for m in eb["mentions"])
        for (t, c, why), n in (cb - ca).items():
            r[f"completeness_added:{t}/{c}/{why}"] += n
        for (t, c, why), n in (ca - cb).items():
            r[f"completeness_removed:{t}/{c}/{why}"] += n
        r["completeness_partial_entries"] += eb.get("configuration_complete") is False
        r["gap_codes_differing_entries"] += sorted(ea["gaps"]) != sorted(eb["gaps"])
    zero = {k: v for k, v in r.items() if k.startswith("math_diff") and v == 0}
    return {"a": va, "b": vb, "entries_a": len(A), "entries_b": len(B), "compared": len(common),
            "math_invariant": r["math_entries_differing"] == 0 and len(A) == len(B) == len(common),
            "math": {k: v for k, v in sorted(r.items()) if k.startswith("math") and k not in zero},
            "math_fields_checked_identical": len(zero),
            "timing_and_gaps_reported_separately": {k: v for k, v in sorted(r.items()) if k.startswith(("timing", "gap"))},
            "completeness": {k: v for k, v in sorted(r.items()) if k.startswith("completeness")}}


def _codon_state(m):
    if m["class"] != "VERIFIED":
        return m["class"]
    return {"name+current-angle": "VERIFIED(angle)", "mutable-angle": "VERIFIED(mutable-angle)",
            "name+loader-scope": "VERIFIED(name+scope)"}.get(m.get("identity_basis"), "VERIFIED(unique-name)")


def _jbin(d):
    d = abs(d)
    return "0" if d == 0 else "(0,0.05]" if d <= 0.05 else "(0.05,0.10]" if d <= 0.10 else "(0.10,0.25]" if d <= 0.25 else ">0.25"


async def delta(ledger_a, va: str, ledger_b, vb: str) -> dict:
    A, B = await _load(ledger_a, va), await _load(ledger_b, vb)
    common = set(A) & set(B)
    mt, sc, jd, rel = Counter(), Counter(), Counter(), Counter()
    entries_changed = 0
    for oid in common:
        ea, eb = A[oid], B[oid]
        ca = {m["field"]: m for m in ea["mentions"] if m["type"] == "codon"}
        cb = {m["field"]: m for m in eb["mentions"] if m["type"] == "codon"}
        for f in ca.keys() | cb.keys():
            if f not in ca or f not in cb:
                mt["codon_mention_unpaired"] += 1
                continue
            sa, sb = _codon_state(ca[f]), _codon_state(cb[f])
            k = f"{sa} -> {sb}"
            if sa.startswith("VERIFIED") and sb.startswith("VERIFIED"):
                k += " same-record" if ca[f]["element"] == cb[f]["element"] else " DIFFERENT-record"
            elif sa == sb == "CANDIDATES":
                k += " same-set" if sorted(ca[f]["candidates"]) == sorted(cb[f]["candidates"]) else " changed-set"
            mt[k] += 1
        ma, mb = _math(ea, va), _math(eb, vb)
        entries_changed += ma["verified"] != mb["verified"]
        sc["entries_verified_set_changed"] += ma["verified"] != mb["verified"]
        sc["entries_text_layer_changed"] += ma["text"] != mb["text"]
        for s in SCOPES:
            xa, xb = ma["scopes"][s], mb["scopes"][s]
            if xa["pred"] == "none-observed":
                continue
            sc[f"{s}/comparisons"] += 1
            va_, vb_ = xa["verified"], xb["verified"]
            sets_a = (va_.get("present_at_both"), va_.get("withdrawn"), va_.get("introduced_first_observed"), [r["element"] for r in va_.get("returned", [])])
            sets_b = (vb_.get("present_at_both"), vb_.get("withdrawn"), vb_.get("introduced_first_observed"), [r["element"] for r in vb_.get("returned", [])])
            changed = sets_a != sets_b
            sc[f"{s}/verified_sets_changed"] += changed
            if va_.get("relation_rcc5") != vb_.get("relation_rcc5"):
                rel[f"{s}/{va_.get('relation_rcc5')}->{vb_.get('relation_rcc5')}"] += 1
            if va_.get("jaccard") is not None and vb_.get("jaccard") is not None:
                jd[f"{s}/|dJ| {_jbin(vb_['jaccard'] - va_['jaccard'])}"] += 1
            ua, ub = xa["uncertainty"], xb["uncertainty"]
            da, db_ = (ua or {}).get("determined", True) if ua else "no-uncertainty", (ub or {}).get("determined", True) if ub else "no-uncertainty"
            if da != db_:
                sc[f"{s}/uncertainty_state {da}->{db_}"] += 1
            sc[f"{s}/text_layer_changed"] += xa["text_layer"] != xb["text_layer"]
            sc[f"{s}/conditional_identity_comparisons"] += bool(B[oid]["scopes"][s].get("conditional_identity_n"))
    return {"a": va, "b": vb, "compared": len(common), "entries_with_changed_verified_set": entries_changed,
            "codon_mention_transitions": dict(sorted(mt.items())), "comparisons": dict(sorted(sc.items())),
            "relation_changes": dict(sorted(rel.items())), "jaccard_change_distribution": dict(sorted(jd.items()))}
