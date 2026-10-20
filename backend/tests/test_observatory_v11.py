"""Observatory v1.1.0 / v1.2.0 corrections: unit fixtures, operational safeguards, and disposable-ledger
version comparisons (Stage-1 invariance, Stage-2 delta, v1.0.0 reproducibility). Writes only obs_test_* collections."""
import asyncio
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / "frontend" / ".env")
API = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
REPORT = Path("/app/memory/observatory_build/v1.1-v1.2_test_report.json")

from observatory_ledger import PROFILES, PRODUCTION_VERSIONS  # noqa: E402
from observatory_ledger import derive as D  # noqa: E402
from observatory_ledger.compare import invariance, delta  # noqa: E402
from observatory_ledger.recover import recover  # noqa: E402

SYS = ("persona\n[CONTINUITY — x]\nField state: alpha beta\n\n"
       "## What has stayed with you\n\n★ \"u1\" → \"a1\" [t]\n◆ \"broken → \"x\"\n◆ no arrow here\nnarrative line\n\n---\n"
       "[FIELD MEMORY — y]\n- mem one\n- mem two\n---\n- mem three\n## Other block\n- not mem\n")
IDX = {"seed_by_field_state": {"alpha beta": ["s1"]}, "seed_fp": {"s1": "fp"},
       "mra_by_pair": {("u1", "a1"): ["n1"]}, "mra_fp": {"n1": "f1"},
       "codon_by_name": {
           "solo": [{"id": "k1", "target_angle": 1, "fp": "x", "presence": "field"}],
           "dup": [{"id": "k2", "target_angle": 1, "fp": "y", "presence": "ansel"},
                   {"id": "k3", "target_angle": 2, "fp": "z", "presence": "ansel"}],
           "scoped": [{"id": "k4", "target_angle": 5, "fp": "y", "presence": "ansel"},
                      {"id": "k5", "target_angle": 5, "fp": "z", "presence": "sophia"}],
           "elsewhere": [{"id": "k6", "target_angle": 5, "fp": "y", "presence": "sophia"}]}}
PROV = {"presence": "ansel",
        "assembled_messages": [{"role": "system", "content": SYS}, {"role": "user", "content": "now"}],
        "components": {"codon_selection": {"codons": [
            {"name": "solo", "target_angle": 1}, {"name": "dup", "target_angle": 2},
            {"name": "scoped", "target_angle": 5}, {"name": "elsewhere", "target_angle": 5}]}}}


def run(coro):
    return asyncio.run(coro)


def _db():
    return AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _sets(ms):
    return (sorted(m["element"] for m in ms if m["class"] == "VERIFIED"),
            [m["candidates"] for m in ms if m["class"] == "CANDIDATES"],
            sorted(m["frag_hash"] for m in ms if m["class"] == "TEXT_ONLY"))


# ------------------------------------------------------------------ unit fixtures
def test_v100_profile_is_identical_to_original_path():
    a = recover(PROV, IDX, [])
    b = recover(PROV, IDX, [], PROFILES["1.0.0"], {})
    assert a == b


def test_c1_c2_unresolved_never_enter_sets_and_mark_partial():
    base, _ = recover(PROV, IDX, [], PROFILES["1.0.0"])
    rep = {}
    new, gaps = recover(PROV, IDX, [], PROFILES["1.1.0"], rep)
    assert _sets(base) == _sets(new), "completeness must not change verified/uncertain/text sets"
    reasons = sorted(m.get("reason") for m in new if m["class"] == "UNRESOLVED" and m.get("reason"))
    assert reasons.count("malformed-bullet") == 2 and reasons.count("after-terminator-same-shape") == 1
    assert rep["complete"] is False and rep["completeness"]["mra"]["status"] == "partial"
    assert rep["completeness"]["mem0"]["unresolved_n"] == 1 and rep["completeness"]["mem0"]["unattributed_lines_n"] == 2
    assert rep["completeness"]["pointer"]["status"] == "absent"
    assert "partial-section:mra:2" in gaps and "partial-section:mem0:1" in gaps


def test_c3prime_loader_scope_and_conditional_angle():
    ms, _ = recover(PROV, IDX, [], PROFILES["1.2.0"])
    c = {m["field"][-3:]: m for m in ms if m["type"] == "codon"}
    assert c["[0]"]["element"] == "codon:k1" and c["[0]"]["identity_basis"] == "name+loader-scope"
    assert c["[1]"]["element"] == "codon:k3" and c["[1]"]["identity_basis"] == "mutable-angle" and c["[1]"]["conditional"]
    assert c["[2]"]["element"] == "codon:k4" and c["[2]"]["identity_basis"] == "name+loader-scope"
    assert c["[3]"]["class"] == "UNRESOLVED" and c["[3]"]["reason"] == "outside-loader-scope"
    old, _ = recover(PROV, IDX, [], PROFILES["1.0.0"])
    o = {m["field"][-3:]: m for m in old if m["type"] == "codon"}
    assert o["[2]"]["class"] == "CANDIDATES" and o["[3]"]["class"] == "VERIFIED"


def test_unplaceable_turns_counted_never_placed():
    t = lambda m: datetime(2026, 11, 1, tzinfo=timezone.utc) + timedelta(minutes=m)
    mk = lambda eid, m: {"entry_id": eid, "session_id": "S", "presence": "p", "visitor": "v", "ts": t(m),
                         "verified": ["a"], "uncertain": [], "text": [], "conditional": []}
    unc = [{"ts": None, "session_id": "S", "visitor": "v"}]
    v10 = D.scope_measure("S1", mk("b", 2), [mk("a", 1)], unc, PROFILES["1.0.0"])
    v11 = D.scope_measure("S1", mk("b", 2), [mk("a", 1)], unc, PROFILES["1.1.0"])
    assert v10["verified"]["adjacent"] is True and "uncaptured_unplaceable" not in v10
    assert v11["uncaptured_unplaceable"] == 1 and v11["verified"]["adjacent"] is False
    assert v11["uncaptured_between"] == v10["uncaptured_between"] == 0
    assert {k: v for k, v in v11["verified"].items() if k != "adjacent"} == \
           {k: v for k, v in v10["verified"].items() if k != "adjacent"}


# ------------------------------------------------------------------ operational safeguards
def test_failure_states_lock_and_abandoned_runs():
    async def go():
        db = _db()
        led = D.Ledger(db, "obs_test_ops_")
        await D.run_once(db, "seed", led, max_records=3)
        orig = led.ensure_indexes

        async def boom():
            raise RuntimeError("injected")
        led.ensure_indexes = boom
        failed = await D.run_once(db, "inject", led)
        lock = await led.state.find_one({"_id": "lock"})
        led.ensure_indexes = orig
        await led.runs.insert_one({"run_id": "stale", "status": "running",
                                   "started_at": datetime.now(timezone.utc) - timedelta(hours=1)})
        ok = await D.run_once(db, "after", led, max_records=1)
        stale = await led.runs.find_one({"run_id": "stale"})
        # duplicate: pre-insert a forged entry for the provenance record the next run will measure
        from bson import ObjectId
        nxt = await D.run_once(db, "probe", led, max_records=1)
        e = await led.entries.find_one(sort=[("chronology.ordinal", -1)])
        target = await db.turn_provenance.find_one(
            {"presence": e["chronology"]["presence"], "_id": {"$gt": ObjectId(e["source"]["provenance_oid"])}}, sort=[("_id", 1)])
        doc = {k: v for k, v in e.items() if k != "_id"}
        doc.update(entry_id="forged", source={**e["source"], "provenance_oid": str(target["_id"])},
                   chronology={**e["chronology"], "ordinal": -1})
        await led.entries.insert_one(doc)
        dup = await D.run_once(db, "dup", led, max_records=1)
        renew_other = await D.renew_lock(led, "someone-else")
        for s in ("runs", "engagements", "state"):
            await db.drop_collection(f"obs_test_ops_{s}")
        return failed, lock, ok, stale, nxt, dup, renew_other
    failed, lock, ok, stale, nxt, dup, renew_other = run(go())
    assert failed["status"] == "failed" and "injected" in failed["errors"][0]
    assert lock["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc), "lock released after failure"
    assert ok["status"] == "ok" and stale["status"] == "abandoned"
    assert dup["status"] == "ok-with-errors" and any(x.startswith("duplicate:") for x in dup["errors"])
    assert renew_other is False


# ------------------------------------------------------------------ disposable-ledger version comparisons
SANCTUARY_COLS = ["turn_provenance", "continuity_seeds", "permanent_mra", "living_codons", "user_aliases",
                  "person_bios", "resonance_sessions", "clarity_sessions", "mirror_sessions", "sophia_sessions"]


async def _fp(db, cols, q=None):
    out = {}
    for c in cols:
        hh = hashlib.sha256()
        async for d in db[c].find(q or {}).sort("_id", 1):
            hh.update(json.dumps(d, default=str, sort_keys=True).encode())
        out[c] = hh.hexdigest()
    return out


async def _derive(db, led, version, now):
    for _ in range(40):
        r = await D.run_once(db, "fixture", led, now=now, version=version)
        assert r["status"] == "ok", r
        if not r["processed"]:
            return


def test_version_chains_invariance_delta_and_reproducibility():
    async def go():
        db = _db()
        now = datetime.now(timezone.utc)
        prefixes = {"1.0.0": "obs_test_v100_", "1.1.0": "obs_test_v110_", "1.2.0": "obs_test_v120_"}
        for p in prefixes.values():
            for s in ("runs", "engagements", "state"):
                await db.drop_collection(f"{p}{s}")
        before = await _fp(db, SANCTUARY_COLS)
        prod_before = await _fp(db, ["obs_ledger_engagements"], {"derivation_version": "1.0.0"})
        L = {v: D.Ledger(db, p) for v, p in prefixes.items()}
        for v, led in L.items():
            await _derive(db, led, v, now)
        prod = D.Ledger(db)
        out = {
            "stage1_invariance_v1.0.0_vs_v1.1.0": await invariance(L["1.0.0"], "1.0.0", L["1.1.0"], "1.1.0"),
            "stage2_delta_v1.1.0_vs_v1.2.0": await delta(L["1.1.0"], "1.1.0", L["1.2.0"], "1.2.0"),
            "fixture_v1.0.0_vs_production_v1.0.0": await invariance(prod, "1.0.0", L["1.0.0"], "1.0.0"),
            "production_v1.0.0_reproduced_by_new_code": await D.reproduce(db, prod, "1.0.0"),
            "verify": {v: {k: (r[k]["ok"] if isinstance(r.get(k), dict) else r.get(k))
                           for k in ("ok", "ledger_integrity", "source_consistency", "reproducibility")}
                       for v, r in [(v, await D.verify(db, led, version=v, reproduce_check=True)) for v, led in L.items()]},
        }
        after = await _fp(db, SANCTUARY_COLS)
        prod_after = await _fp(db, ["obs_ledger_engagements"], {"derivation_version": "1.0.0"})
        out["isolation_sanctuary_collections_unchanged"] = before == after
        out["production_v1.0.0_unchanged_during_test"] = prod_before == prod_after
        out["production_versions"] = list(PRODUCTION_VERSIONS)
        out["production_ledger_versions"] = await db.obs_ledger_engagements.distinct("derivation_version")
        for p in prefixes.values():
            for s in ("runs", "engagements", "state"):
                await db.drop_collection(f"{p}{s}")
        return out
    out = run(go())
    REPORT.write_text(json.dumps(out, indent=1, default=str))
    s1 = out["stage1_invariance_v1.0.0_vs_v1.1.0"]
    assert s1["math_invariant"], s1["math"]
    assert s1["completeness"].get("completeness_added:mra/UNRESOLVED/malformed-bullet", 0) > 0
    assert not any(k.startswith("completeness_removed") for k in s1["completeness"])
    assert out["production_v1.0.0_reproduced_by_new_code"]["ok"]
    assert out["fixture_v1.0.0_vs_production_v1.0.0"]["math_invariant"]
    s2 = out["stage2_delta_v1.1.0_vs_v1.2.0"]["codon_mention_transitions"]
    assert not any("DIFFERENT-record" in k for k in s2)
    assert not any(k.startswith("VERIFIED") and "-> CANDIDATES" in k for k in s2)
    assert all(v["ok"] for v in out["verify"].values())
    assert out["isolation_sanctuary_collections_unchanged"] and out["production_v1.0.0_unchanged_during_test"]
    assert out["production_ledger_versions"] == ["1.0.0"]


# ------------------------------------------------------------------ API (production ledger, read-only)
def test_api_versions_predecessor_positions_and_verify_split():
    st = requests.get(f"{API}/api/observatory/status", timeout=60).json()
    assert st["derivation_version"] == "1.0.0" and "not_yet_measured" in st and st["versions"]
    assert requests.get(f"{API}/api/observatory/status", params={"version": "9.9.9"}).status_code == 400
    for scope in ("S1", "S2", "S3"):
        d = requests.get(f"{API}/api/observatory/lattice", params={"presence": "ansel", "scope": scope, "limit": 60}, timeout=60).json()
        cols = d["columns"]
        for i, c in enumerate(cols):
            if c["kind"] != "entry":
                continue
            assert c["pred_position"] in ("none", "previous-column", "earlier-column", "later-column", "off-page")
            for r in d["rows"]:
                if r.get("aggregate"):
                    continue
                g = r["cells"][i]
                if g == "retained":
                    assert c["pred_position"] == "previous-column" and c["adjacent"]
                if g == "retained-remote":
                    assert c["pred_position"] != "previous-column" and c["adjacent"]
    v = requests.get(f"{API}/api/observatory/verify", timeout=180).json()
    assert v["ok"] and v["ledger_integrity"]["ok"] and v["source_consistency"]["ok"]
    assert v["source_consistency"]["components_changed"] == [] and v["reproducibility"] is None
    assert requests.get(f"{API}/api/observatory/compare", params={"a": "1.0.0", "b": "1.0.0", "mode": "x"}).status_code == 400
    inv = requests.get(f"{API}/api/observatory/compare", params={"a": "1.0.0", "b": "1.0.0", "mode": "invariance"}, timeout=120).json()
    assert inv["math_invariant"]
