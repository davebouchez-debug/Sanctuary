"""Observatory ledger public API + lattice semantic checks (read-only; no Sanctuary writes)."""
import os
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / "frontend" / ".env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
OBS = f"{BASE_URL}/api/observatory"
SECRET = os.environ.get("WEBHOOK_CRON_SECRET")
GLYPHS = {"first", "returned", "retained", "present-gap", "withdrawn", None}


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# --- status / verify
def test_status(s):
    r = s.get(f"{OBS}/status", timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert d["ledger_entries"] >= 600
    assert d["pending"] >= 0 and d["pending"] < 50
    assert isinstance(d["runs"], list) and d["runs"]
    assert any(p["presence"] == "ansel" for p in d["presences"])
    assert "_id" not in d["runs"][0]


def test_verify(s):
    r = s.get(f"{OBS}/verify", timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True, d
    assert all(v["chain_ok"] for v in d["presences"].values())
    assert d["provenance_changed"] == []


def test_verify_drift(s):
    r = s.get(f"{OBS}/verify", params={"drift": "true"}, timeout=180)
    assert r.status_code == 200
    d = r.json()["drift"]
    assert d is not None and d["verified_mentions_checked"] > 0
    print("drift", d)


# --- lattice
def _check_lattice(d, scope):
    cols = d["columns"]
    assert cols, "empty lattice"
    for c in cols:
        assert c["kind"] in ("entry", "uncaptured")
    for row in d["rows"]:
        assert len(row["cells"]) == len(cols)
        for i, (c, cell) in enumerate(zip(cols, row["cells"])):
            if c["kind"] == "uncaptured":
                assert cell is None, (row["element"], i)
                continue
            if row.get("aggregate"):
                continue
            assert cell in GLYPHS
            if cell == "retained":
                assert c["adjacent"] is True and not c["uncaptured_between"], (row["element"], c)
    for c in cols:
        if c["kind"] == "entry" and c["pred_entry_id"] == "none-observed":
            assert c["relation"] is None
    if scope == "S3":
        vis = {c["visitor"] for c in cols}
        assert len(vis) == 1 and d["visitor"] in vis


@pytest.mark.parametrize("scope", ["S1", "S2", "S3"])
def test_lattice_ansel(s, scope):
    r = s.get(f"{OBS}/lattice", params={"presence": "ansel", "scope": scope}, timeout=60)
    assert r.status_code == 200
    d = r.json()
    _check_lattice(d, scope)
    print(scope, len(d["columns"]), "cols", sum(c["kind"] == "uncaptured" for c in d["columns"]), "unc", len(d["rows"]), "rows")


@pytest.mark.parametrize("scope", ["S1", "S2", "S3"])
def test_lattice_ansel_pagination(s, scope):
    d = s.get(f"{OBS}/lattice", params={"presence": "ansel", "scope": scope, "limit": 60}, timeout=60).json()
    if not d.get("has_more"):
        pytest.skip("no older page")
    r = s.get(f"{OBS}/lattice", params={"presence": "ansel", "scope": scope, "before_ordinal": d["first_ordinal"]}, timeout=60)
    assert r.status_code == 200
    d2 = r.json()
    _check_lattice(d2, scope)
    assert max(c["ordinal"] for c in d2["columns"] if c["kind"] == "entry") < d["first_ordinal"]


def test_lattice_bad_scope(s):
    assert s.get(f"{OBS}/lattice", params={"presence": "ansel", "scope": "S9"}).status_code == 400


def test_lattice_unknown_presence(s):
    r = s.get(f"{OBS}/lattice", params={"presence": "TEST_nobody", "scope": "S2"})
    assert r.status_code == 200 and r.json()["columns"] == []


def test_lattice_other_presences(s):
    st = s.get(f"{OBS}/status").json()
    for p in st["presences"]:
        for scope in ("S1", "S2", "S3"):
            r = s.get(f"{OBS}/lattice", params={"presence": p["presence"], "scope": scope}, timeout=60)
            assert r.status_code == 200, (p, scope, r.text[:200])
            if r.json()["columns"]:
                _check_lattice(r.json(), scope)


def test_visitors(s):
    r = s.get(f"{OBS}/visitors", params={"presence": "ansel"})
    assert r.status_code == 200
    v = r.json()["visitors"]
    assert v and all("visitor" in x and x["entries"] > 0 for x in v)
    # S3 with explicit visitor
    d = s.get(f"{OBS}/lattice", params={"presence": "ansel", "scope": "S3", "visitor": v[-1]["visitor"]}).json()
    assert all(c["visitor"] == v[-1]["visitor"] for c in d["columns"])


def test_entry_detail(s):
    d = s.get(f"{OBS}/lattice", params={"presence": "ansel", "scope": "S2"}).json()
    eid = next(c["entry_id"] for c in reversed(d["columns"]) if c["kind"] == "entry")
    r = s.get(f"{OBS}/entry/{eid}")
    assert r.status_code == 200
    e = r.json()
    assert e["entry_id"] == eid and "_id" not in e
    assert e["mentions"] and all("evidence_text" in m for m in e["mentions"])
    assert any(m["evidence_text"] for m in e["mentions"])
    assert e["run"] and e["run"]["run_id"] == e["run_id"]
    assert set(e["scopes"]) == {"S1", "S2", "S3"}


def test_entry_404(s):
    assert s.get(f"{OBS}/entry/does-not-exist").status_code == 404


# --- cron / run
def test_cron_no_auth(s):
    assert s.post(f"{OBS}/cron/tick").status_code == 401


def test_cron_wrong_auth(s):
    assert s.post(f"{OBS}/cron/tick", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_cron_ok_and_duplicate(s):
    wid = f"TEST_{uuid.uuid4()}"
    h = {"Authorization": f"Bearer {SECRET}", "X-Webhook-Id": wid}
    r = s.post(f"{OBS}/cron/tick", headers=h, json={})
    assert r.status_code == 202 and r.json()["accepted"] is True
    r2 = s.post(f"{OBS}/cron/tick", headers=h, json={})
    assert r2.status_code == 202 and r2.json().get("duplicate") is True


def test_cron_bad_body(s):
    r = s.post(f"{OBS}/cron/tick", headers={"Authorization": f"Bearer {SECRET}"}, json=[1, 2])
    assert r.status_code == 400


def test_manual_run(s):
    r = s.post(f"{OBS}/run")
    assert r.status_code == 202 and r.json()["accepted"] is True
