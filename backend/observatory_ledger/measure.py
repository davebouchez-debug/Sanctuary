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
