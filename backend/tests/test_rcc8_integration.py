"""RCC8 environment integration regression (RCC8_ENVIRONMENT=on): chambers, provenance, forging, guardian gates."""
import json
import os
import time

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
TOKEN = "rcc8_qa_tok"
USER = "fw-test-user"
H = {"Authorization": f"Bearer {TOKEN}"}
ALLOWED = {"EC", "PO", "TPP", "NTPP", "TPPi", "NTPPi", "EQ"}
MSGS = [
    "TEST_ I keep thinking about the old oak tree behind my childhood house.",
    "My father carved our initials into it the summer before he left.",
    "I wonder whether places hold onto us the way we hold onto them.",
]
CHAMBERS = [  # (name, start, stream, end)
    ("sophia", "spiral/start", "spiral/message/stream", "spiral/session/{}/end"),
    ("paige", "hospitality/start", "hospitality/message/stream", "hospitality/session/{}/end"),
    ("ansel", "resonance/start", "resonance/message/stream", "resonance/session/{}/end"),
    ("claude", "mirror/start", "mirror/message/stream", "mirror/session/{}/end"),
    ("jasmine", "clarity/start", "clarity/message/stream", "clarity/session/{}/end"),
]

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
RESULTS = {}


def stream(path, sid, text):
    out, events = "", []
    with requests.post(f"{API}/{path}", json={"session_id": sid, "content": text}, headers=H, stream=True, timeout=180) as r:
        assert r.status_code == 200, r.text[:300]
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                try:
                    ev = json.loads(line[6:])
                except Exception:
                    continue
                events.append(ev.get("type"))
                if ev.get("type") == "token":
                    out += ev.get("content", "")
    return out, events


# Health
def test_health():
    r = requests.get(f"{API}/health", timeout=30)
    assert r.status_code == 200 and r.json()["status"] == "healthy"


# Guardian-only gates
@pytest.mark.parametrize("path", ["health/memory", "field-keeper/export"])
def test_guardian_gate(path):
    r = requests.get(f"{API}/{path}", timeout=30)
    assert r.status_code == 401, f"no-auth {r.status_code}"
    r = requests.get(f"{API}/{path}", headers=H, timeout=30)
    assert r.status_code == 403, f"guest {r.status_code}"


# Each chamber: greeting unchanged, 3 turns, provenance branches, end forges
@pytest.mark.parametrize("name,start,msg,end", CHAMBERS, ids=[c[0] for c in CHAMBERS])
def test_chamber_rcc8(name, start, msg, end):
    seeds_before = db.continuity_seeds.count_documents({"user_id": USER})
    mra_before = db.permanent_mra.count_documents({"user_id": USER})
    r = requests.post(f"{API}/{start}", json={"user_name": "TEST_Rowan", "user_id": USER, "new_thread": True}, headers=H, timeout=120)
    assert r.status_code == 200, r.text[:300]
    s = r.json()
    sid = s["session_id"]
    assert not s.get("resumed"), f"{name} resumed despite new_thread"
    welcome = s.get("message") or s.get("welcome") or s.get("greeting") or (s.get("messages") or [{}])[-1]
    print(name, "start keys", list(s.keys()))
    assert welcome, f"{name} no welcome message"
    replies = []
    for m in MSGS:
        txt, evs = stream(msg, sid, m)
        replies.append(len(txt.split()))
        assert txt.strip(), f"{name} empty reply; events={evs[-5:]}"
    time.sleep(4)
    rows = list(db.turn_provenance.find({"session_id": sid}, {"_id": 0, "exchange_index": 1, "components.codon_selection": 1}).sort("exchange_index", 1))
    summary = []
    for row in rows:
        sel = (row.get("components") or {}).get("codon_selection") or {}
        summary.append((row.get("exchange_index"), sel.get("selection_branch"), sel.get("selected_count"),
                        {k: v for k, v in (sel.get("rcc8") or {}).items() if k != "memory_relations"},
                        (sel.get("rcc8") or {}).get("memory_relations")))
    print(name, "replies", replies)
    for x in summary:
        print("  ", x)
    assert len(rows) >= 3, f"{name} provenance rows {len(rows)}"
    for row in rows:
        ei = row.get("exchange_index")
        sel = row["components"]["codon_selection"]
        assert sel["selected_count"] <= 20
        if ei == 1:
            assert sel["selection_branch"] == "meaning-ranked", f"{name} ex1 {sel['selection_branch']}"
            assert "rcc8" not in sel
            assert all("rcc8" not in c for c in sel["codons"])
        elif ei >= 2:
            assert sel["selection_branch"] == "rcc8", f"{name} ex{ei} {sel['selection_branch']}"
            assert sel["codons"], "no codons"
            for c in sel["codons"]:
                assert c.get("rcc8") in ALLOWED, f"bad rel {c.get('rcc8')}"
            meta = sel["rcc8"]
            for k in ("reachable", "candidates", "eps", "floor", "consistency_violations", "memory_relations"):
                assert k in meta, f"meta missing {k}"
            assert meta["consistency_violations"] == 0
            assert meta["reachable"] <= meta["candidates"]
            mr = meta["memory_relations"]
            assert mr is None or all(x in ALLOWED for x in mr), f"mem rels {mr}"
    exs = sorted(r_.get("exchange_index") for r_ in rows)
    assert exs[0] == 1, f"{name} exchange indices {exs}"
    # end -> forge
    r = requests.post(f"{API}/{end.format(sid)}", headers=H, timeout=180)
    assert r.status_code == 200, f"{name} end {r.status_code} {r.text[:300]}"
    time.sleep(6)
    seeds_after = db.continuity_seeds.count_documents({"user_id": USER})
    mra_after = db.permanent_mra.count_documents({"user_id": USER})
    print(name, "seeds", seeds_before, "->", seeds_after, "mra", mra_before, "->", mra_after, "end resp", str(r.json())[:200])
    RESULTS[name] = dict(seeds=(seeds_before, seeds_after), mra=(mra_before, mra_after))
    if name in ("sophia", "ansel"):
        assert seeds_after > seeds_before, f"{name} no new continuity seed"
