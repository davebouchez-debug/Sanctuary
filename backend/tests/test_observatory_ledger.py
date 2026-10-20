"""Observatory ledger tests: math, recovery, isolation, determinism, append-only,
suspension catch-up, crash resume, locking, tamper detection, API, lattice honesty.

Integration tests write only to throwaway `obs_test_*` ledger collections.
"""
import asyncio
import hashlib
import json
import os
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / "frontend" / ".env")
API = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

from observatory_ledger.measure import (rcc5, jaccard, transform, enumerate_resolutions,  # noqa: E402
                                        EMPTY_BOTH, EMPTY_PRED, EMPTY_CURR)
from observatory_ledger import derive as D  # noqa: E402
from observatory_ledger.recover import recover, sections  # noqa: E402


def run(coro):
    return asyncio.run(coro)


def _db():
    return AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


# ------------------------------------------------------------------ math
def test_rcc5_five_relations_and_empty_cases():
    assert rcc5({1}, {2}) == "DR"
    assert rcc5({1, 2}, {2, 3}) == "PO"
    assert rcc5({1, 2}, {1, 2}) == "EQ"
    assert rcc5({1}, {1, 2}) == "PP"
    assert rcc5({1, 2}, {1}) == "PPi"
    assert rcc5(set(), set()) == EMPTY_BOTH
    assert rcc5(set(), {1}) == EMPTY_PRED
    assert rcc5({1}, set()) == EMPTY_CURR


def test_jaccard_edges():
    assert jaccard(set(), set()) is None
    assert jaccard(set(), {1}) == 0
    assert jaccard({1, 2}, {2, 3}) == round(1 / 3, 6)


def test_introduced_is_disjoint_union_of_first_and_returned():
    pred, cur = {"a", "b"}, {"b", "c", "d"}
    tr = transform(pred, cur, {"c": (0, "E-5")})
    assert tr["returned"] == ["c"] and tr["introduced_first_observed"] == ["d"]
    assert set(tr["returned"]) | set(tr["introduced_first_observed"]) == cur - pred
    assert not set(tr["returned"]) & set(tr["introduced_first_observed"])
    assert tr["withdrawn"] == ["a"] and tr["present_at_both"] == ["b"]


# v0.2 §5 synthetic example, every number
E0 = {"g", "seed:9f00", "c1", "c2", "c9"}
E1 = {"g", "seed:aa01", "n-12", "n-30", "c1", "c2", "c3"}
E2 = {"g", "seed:aa01", "n-12", "n-30", "c2", "c3", "c4", "h:m-100", "h:m-101"}
X2 = {"g", "seed:ab77", "c2", "c7"}
E3 = {"g", "seed:ab77", "n-12", "n-41", "c2"}
U = ["mra:n-55", "mra:n-56"]


def test_synthetic_E1_vs_E0():
    tr = transform(E0, E1, {"n-30": (0, "E-5")})
    assert len(tr["present_at_both"]) == 3 and len(tr["withdrawn"]) == 2
    assert tr["returned"] == ["n-30"] and sorted(tr["introduced_first_observed"]) == ["c3", "n-12", "seed:aa01"]
    assert tr["jaccard"] == 0.333333 and tr["relation_rcc5"] == "PO"
    u = enumerate_resolutions(E0, E1, [], [U], 65536)
    assert u["relation_set"] == ["PO"] and u["determined"] and u["jaccard_range"] == [0.3, 0.3]


def test_synthetic_E2_vs_E1():
    tr = transform(E1, E2, {})
    assert tr["jaccard"] == 0.6 and tr["relation_rcc5"] == "PO"
    u = enumerate_resolutions(E1, E2, [U], [U], 65536)
    assert u["resolutions_n"] == 4 and u["relation_set"] == ["PO"]
    assert u["jaccard_range"] == [0.5, round(7 / 11, 6)]


def test_synthetic_E3_scopes():
    s3 = transform(E2, E3, {})
    assert s3["jaccard"] == round(3 / 11, 6) and len(s3["withdrawn"]) == 6
    u = enumerate_resolutions(E2, E3, [U], [], 65536)
    assert u["jaccard_range"] == [0.25, 0.25]
    s2 = transform(X2, E3, {"n-12": (2, "E2")})
    assert s2["returned"] == ["n-12"] and s2["introduced_first_observed"] == ["n-41"] and s2["jaccard"] == 0.5


def _brute(pv, cv, pu, cu):
    from itertools import product
    vs = [list(x) for x in pu] + [list(x) for x in cu]
    rels, js = set(), []
    for combo in product(*vs):
        p, c = set(pv) | set(combo[:len(pu)]), set(cv) | set(combo[len(pu):])
        rels.add(rcc5(p, c))
        j = jaccard(p, c)
        if j is not None:
            js.append(j)
    return sorted(rels), [min(js), max(js)] if js else None


def test_free_variable_reduction_is_exact():
    rnd = random.Random(7)
    pool = [f"e{i}" for i in range(14)]
    for _ in range(300):
        pv, cv = set(rnd.sample(pool, rnd.randint(0, 5))), set(rnd.sample(pool, rnd.randint(0, 5)))
        pu = [rnd.sample(pool, rnd.randint(2, 3)) for _ in range(rnd.randint(0, 3))]
        cu = [rnd.sample(pool, rnd.randint(2, 3)) for _ in range(rnd.randint(0, 3))]
        if not pu and not cu:
            continue
        r = enumerate_resolutions(pv, cv, pu, cu, 10 ** 6)
        rels, jr = _brute(pv, cv, pu, cu)
        assert r["relation_set"] == rels and r["jaccard_range"] == jr


def test_enumeration_cap_reports_not_enumerated():
    pu = [[f"a{i}", f"b{i}", "shared"] for i in range(12)]
    r = enumerate_resolutions({"x"}, {"x"}, pu, [], 1024)
    assert r["resolutions_n"] == "not-enumerated" and not r["determined"]


def test_scope_predecessors_gaps_and_returns():
    t = lambda m: datetime(2026, 11, 1, tzinfo=timezone.utc) + timedelta(minutes=m)
    mk = lambda eid, sid, vis, m, ver: {"entry_id": eid, "session_id": sid, "presence": "ansel", "visitor": vis,
                                         "ts": t(m), "verified": sorted(ver), "uncertain": [], "text": []}
    hist = [mk("E-5", "S-9", "v1", 0, {"n-30"}), mk("E0", "S-0", "v1", 10, E0),
            mk("E1", "S-A", "v1", 20, E1), mk("E2", "S-A", "v1", 22, E2),
            mk("X1", "S-X", "v2", 30, X2), mk("X2", "S-X", "v2", 31, X2)]
    unc = [{"ts": t(25), "session_id": "S-A", "visitor": "v1"}]
    cur = mk("E3", "S-B", "v1", 60, E3)
    s1 = D.scope_measure("S1", cur, hist, unc)
    assert s1["pred_entry_id"] == "none-observed"
    s3 = D.scope_measure("S3", cur, hist, unc)
    assert s3["pred_entry_id"] == "E2" and s3["uncaptured_between"] == 1
    assert s3["verified"]["adjacent"] is False and "predecessor-not-adjacent" in s3["gaps"]
    s2 = D.scope_measure("S2", cur, hist, unc)
    assert s2["pred_entry_id"] == "X2" and s2["uncaptured_between"] == 0
    ret = s2["verified"]["returned"][0]
    assert ret["element"] == "n-12" and ret["last_seen_entry_id"] == "E2" and ret["d_captured"] == 2 and ret["d_uncaptured"] == 1
    e2 = D.scope_measure("S1", mk("E2b", "S-A", "v1", 23, E2), hist[:3], [])
    assert e2["verified"]["adjacent"] is True and e2["uncaptured_between"] == 0
    ret_e1 = D.scope_measure("S3", hist[2], hist[:2], [])["verified"]["returned"]
    assert ret_e1 and ret_e1[0]["element"] == "n-30" and ret_e1[0]["last_seen_entry_id"] == "E-5"


# ------------------------------------------------------------------ recovery
def test_recover_classes_on_synthetic_prompt():
    sysp = ("persona\n[CONTINUITY — x]\nField state: alpha beta\nDynamic: d\n\n"
            "## What has stayed with you\n\n★ \"u1\" → \"a1\" [t]\n◆ \"dup\" → \"d\"\n◆ \"nope\" → \"n\"\n\n---\n"
            "[FIELD MEMORY — y]\n- mem one\n- mem two\n")
    idx = {"seed_by_field_state": {"alpha beta": ["s1"]}, "seed_fp": {"s1": "fp"},
           "mra_by_pair": {("u1", "a1"): ["n1"], ("dup", "d"): ["n2", "n3"]}, "mra_fp": {"n1": "f1"},
           "codon_by_name": {"c": [{"id": "k1", "target_angle": 1, "fp": "x"}],
                             "dd": [{"id": "k2", "target_angle": 1, "fp": "y"}, {"id": "k3", "target_angle": 2, "fp": "z"}],
                             "tt": [{"id": "k4", "target_angle": 5, "fp": "y"}, {"id": "k5", "target_angle": 5, "fp": "z"}]}}
    prov = {"assembled_messages": [{"role": "system", "content": sysp}, {"role": "user", "content": "hi"},
                                   {"role": "assistant", "content": "hello"}, {"role": "user", "content": "now"}],
            "components": {"codon_selection": {"codons": [{"name": "c", "target_angle": 1}, {"name": "dd", "target_angle": 2},
                                                          {"name": "tt", "target_angle": 5}, {"name": "zz"}]}}}
    ms, gaps = recover(prov, idx, [{"id": "u", "content": "hi"}, {"id": "a", "content": "hello"}])
    by = {(m["type"], m["class"]) for m in ms}
    assert ("seed", "VERIFIED") in by and ("mra", "VERIFIED") in by and ("mra", "CANDIDATES") in by
    assert ("mra", "UNRESOLVED") in by and ("mem0", "TEXT_ONLY") in by
    codons = [m for m in ms if m["type"] == "codon"]
    assert [m["class"] for m in codons] == ["VERIFIED", "VERIFIED", "CANDIDATES", "UNRESOLVED"]
    assert codons[1]["element"] == "codon:k3" and codons[1]["identity_basis"] == "name+current-angle"
    assert {m["element"] for m in ms if m["type"] == "history"} == {"history:u", "history:a"}
    assert sum(m["type"] == "mem0" for m in ms) == 2 and not gaps


# ------------------------------------------------------------------ integration
SANCTUARY_COLS = ["turn_provenance", "continuity_seeds", "permanent_mra", "living_codons", "user_aliases",
                  "person_bios", "resonance_sessions", "clarity_sessions", "mirror_sessions", "sophia_sessions"]


async def _fingerprint(db):
    out = {}
    for c in SANCTUARY_COLS:
        hsh = hashlib.sha256()
        n = 0
        async for d in db[c].find({}).sort("_id", 1):
            hsh.update(json.dumps(d, default=str, sort_keys=True).encode())
            n += 1
        out[c] = (n, hsh.hexdigest())
    return out


async def _drop(db, prefix):
    for s in ("runs", "engagements", "state"):
        await db.drop_collection(f"{prefix}{s}")


async def _chain(led):
    return [(e["chronology"]["presence"], e["chronology"]["ordinal"], e["chain"]["entry_hash"])
            async for e in led.entries.find({}, {"chronology": 1, "chain": 1}).sort([("chronology.presence", 1), ("chronology.ordinal", 1)])]


async def _full_run(db, led, now):
    for _ in range(30):
        r = await D.run_once(db, "test", led, now=now)
        if not r["processed"]:
            return r
    return r


def test_static_isolation_imports():
    forbidden = re.compile(r"^\s*(from|import)\s+(server|permanent_mra|mem0\w*|session_cache_mra|person_bio|"
                           r"living_codons|presence_template|presences|auto_forge|\w*canonical_memory|user_aliases|"
                           r"emergentintegrations|openai|anthropic)\b", re.M)
    for f in (ROOT / "observatory_ledger").glob("*.py"):
        assert not forbidden.search(f.read_text()), f"{f.name} imports a Sanctuary operational module"


def test_isolation_determinism_resume_suspension_and_append_only():
    async def go():
        db = _db()
        now = datetime.now(timezone.utc)
        for p in ("obs_test_a_", "obs_test_b_", "obs_test_c_", "obs_test_d_"):
            await _drop(db, p)
        before = await _fingerprint(db)
        A, B, C, Dl = (D.Ledger(db, p) for p in ("obs_test_a_", "obs_test_b_", "obs_test_c_", "obs_test_d_"))
        await _full_run(db, A, now)
        await _full_run(db, B, now)
        # crash/interrupt simulation: tiny batches, repeated
        for _ in range(200):
            r = await D.run_once(db, "test-resume", C, max_records=37, now=now)
            if not r["processed"]:
                break
        # suspension simulation: observer "asleep" until midway, then catches up
        provs = await db.turn_provenance.find({}, {"timestamp": 1}).sort("_id", 1).to_list(None)
        mid = D.parse_ts(provs[len(provs) // 2]["timestamp"]) + D.SETTLE_AFTER
        await _full_run(db, Dl, mid)
        n_mid = await Dl.entries.count_documents({})
        await _full_run(db, Dl, now)
        after = await _fingerprint(db)
        ca, cb, cc, cd = await _chain(A), await _chain(B), await _chain(C), await _chain(Dl)
        n_a = await A.entries.count_documents({})
        snapshot = [e async for e in A.entries.find({}, {"_id": 0, "run_id": 0, "derived_at": 0}).sort("entry_id", 1)]
        again = await D.run_once(db, "test-rerun", A, now=now)
        snapshot2 = [e async for e in A.entries.find({}, {"_id": 0, "run_id": 0, "derived_at": 0}).sort("entry_id", 1)]
        ver = await D.verify(db, A)
        unsettled_ok = all([e["participation"]["end_state"] async for e in A.entries.find({}, {"participation": 1})])
        for p in ("obs_test_b_", "obs_test_c_", "obs_test_d_"):
            await _drop(db, p)
        return before, after, ca, cb, cc, cd, n_a, n_mid, snapshot, snapshot2, again, ver, unsettled_ok
    before, after, ca, cb, cc, cd, n_a, n_mid, s1, s2, again, ver, unsettled_ok = run(go())
    assert before == after, "Sanctuary collections changed during observation"
    assert n_a > 500
    assert ca == cb, "two runs of the same version must produce identical chains"
    assert ca == cc, "interrupted/resumed derivation must equal one full run"
    assert 0 < n_mid < n_a and ca == cd, "suspension catch-up must equal continuous operation"
    assert again["processed"] == 0 and s1 == s2, "re-run must append nothing and leave entries byte-identical"
    assert ver["ok"] and not ver["provenance_changed"]
    assert unsettled_ok


def test_tamper_detection_and_lock():
    async def go():
        db = _db()
        led = D.Ledger(db, "obs_test_a_")
        if not await led.entries.count_documents({}):
            await _full_run(db, led, datetime.now(timezone.utc))
        e = await led.entries.find_one({"chronology.presence": "ansel", "chronology.ordinal": 5})
        await led.entries.update_one({"_id": e["_id"]}, {"$set": {"participation.response_len_chars": -1}})
        v = await D.verify(db, led)
        await led.state.update_one({"_id": "lock"}, {"$set": {"holder": "other", "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)}}, upsert=True)
        locked = await D.run_once(db, "test-lock", led)
        await led.state.update_one({"_id": "lock"}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)}})
        stale = await D.run_once(db, "test-stale", led)
        await _drop(db, "obs_test_a_")
        return e["entry_id"], v, locked, stale
    eid, v, locked, stale = run(go())
    assert not v["ok"] and v["presences"]["ansel"]["broken_at"] == eid
    assert locked["status"] == "skipped-locked"
    assert stale["status"] == "ok"


# ------------------------------------------------------------------ API
def test_cron_tick_auth_and_idempotency():
    url = f"{API}/api/observatory/cron/tick"
    assert requests.post(url, json={}).status_code == 401
    assert requests.post(url, json={}, headers={"Authorization": "Bearer wrong"}).status_code == 401
    hdr = {"Authorization": f"Bearer {os.environ['WEBHOOK_CRON_SECRET']}", "X-Webhook-Id": f"test-{random.random()}"}
    env = {"event": "schedule.triggered", "schedule_id": "observatory-ledger", "run_id": hdr["X-Webhook-Id"], "data": None}
    r1 = requests.post(url, json=env, headers=hdr)
    r2 = requests.post(url, json=env, headers=hdr)
    assert r1.status_code == 202 and r1.json()["accepted"]
    assert r2.status_code == 202 and r2.json().get("duplicate")


def test_status_and_entry_evidence():
    st = requests.get(f"{API}/api/observatory/status").json()
    assert st["ledger_entries"] > 500 and st["runs"] and st["unavailable_evidence"]
    lat = requests.get(f"{API}/api/observatory/lattice", params={"presence": "ansel", "scope": "S2", "limit": 8}).json()
    eid = next(c["entry_id"] for c in lat["columns"] if c["kind"] == "entry")
    e = requests.get(f"{API}/api/observatory/entry/{eid}").json()
    seeds = [m for m in e["mentions"] if m["type"] == "seed" and m["class"] == "VERIFIED"]
    assert seeds and all(m["evidence_text"].startswith("Field state:") for m in seeds)
    assert e["run"]["code_commit"]


@pytest.mark.parametrize("scope", ["S1", "S2", "S3"])
def test_lattice_gap_honesty(scope):
    presences = [p["presence"] for p in requests.get(f"{API}/api/observatory/status").json()["presences"]]
    for p in presences:
        lat = requests.get(f"{API}/api/observatory/lattice", params={"presence": p, "scope": scope, "limit": 60}).json()
        cols = lat["columns"]
        for i, c in enumerate(cols):
            if c["kind"] != "entry":
                continue
            if c["pred_entry_id"] == "none-observed":
                assert c["relation"] is None
            for row in lat["rows"]:
                if row.get("aggregate"):
                    continue
                g = row["cells"][i]
                if g == "retained":
                    assert c["adjacent"] and c["uncaptured_between"] == 0
                    j = next((k for k, x in enumerate(cols) if x.get("entry_id") == c["pred_entry_id"]), None)
                    if j is not None:
                        between = [x for x in cols[j + 1:i] if x["kind"] == "uncaptured"
                                   and (scope != "S1" or x["session_id"] == c["session_id"])]
                        assert not between, "solid connector may not span an uncaptured turn in scope"
                if g == "present-gap":
                    assert not c["adjacent"]
            if scope == "S3":
                assert c["visitor"] == lat["visitor"]
            if c["uncertainty"] and not c["uncertainty"]["determined"]:
                assert c["uncertainty"]["resolutions_n"] == "not-enumerated" or len(c["uncertainty"]["relation_set"]) > 1
