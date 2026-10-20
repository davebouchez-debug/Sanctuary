# Read-only scan: find lattice columns with pred_position earlier/later-column for UI verification
import os, requests, collections
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/observatory"
st = requests.get(f"{BASE}/status", timeout=30).json()
for p in [x["presence"] for x in st["presences"]]:
    for s in ["S1", "S2", "S3"]:
        d = requests.get(f"{BASE}/lattice", params={"presence": p, "scope": s, "limit": 24}, timeout=60).json()
        cnt = collections.Counter(c.get("pred_position") for c in d["columns"] if c.get("kind") == "entry")
        unenum = sum(1 for c in d["columns"] if c.get("uncertainty") and c["uncertainty"].get("resolutions_n") == "not-enumerated")
        nounc = sum(1 for c in d["columns"] if c.get("kind") == "entry" and not c.get("uncertainty"))
        hits = [(c["ordinal"], c["pred_position"], c.get("pred_col")) for c in d["columns"] if c.get("pred_position") in ("earlier-column", "later-column")]
        print(p, s, dict(cnt), "unenum", unenum, "nounc", nounc, "hits", hits[:4])
