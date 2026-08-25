"""Backend tests for Observatory / Micro-Layer 6 console endpoints."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://milton-propagate.preview.emergentagent.com").rstrip("/")

VALID_MOVES = {"opening", "deepening", "holding", "returning", "closing", "baseline", "no-reading"}
VALID_ZONES = {"Expansion", "Development", "Return", "Sacred Pause", None}


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (pytest observatory)"})
    return s


# ── /api/provenance/stats ─────────────────────────────────────────────
class TestProvenanceStats:
    def test_stats_shape(self, api):
        r = api.get(f"{BASE_URL}/api/provenance/stats")
        assert r.status_code == 200
        d = r.json()
        assert set(["total", "per_presence", "latest_timestamp"]).issubset(d.keys())
        assert isinstance(d["total"], int) and d["total"] >= 0
        assert isinstance(d["per_presence"], list)
        for row in d["per_presence"]:
            assert "presence" in row and isinstance(row["presence"], str)
            assert "count" in row and isinstance(row["count"], int)


# ── /api/provenance/trajectory (Micro-Layer 6) ────────────────────────
class TestProvenanceTrajectory:
    def test_trajectory_shape(self, api):
        r = api.get(f"{BASE_URL}/api/provenance/trajectory", params={"limit_per_presence": 20})
        assert r.status_code == 200
        d = r.json()
        assert "presences" in d and isinstance(d["presences"], list)
        assert "generated_at" in d
        assert len(d["presences"]) > 0, "expected at least one presence in trajectory"

        for p in d["presences"]:
            assert "presence" in p
            assert p["relational_move"] in VALID_MOVES, f"bad move {p['relational_move']}"
            assert "series" in p and isinstance(p["series"], list)
            for pt in p["series"]:
                assert "timestamp" in pt
                # spiral_position must be a number OR null (Branch A may be unrecorded on old turns)
                assert pt.get("spiral_position") is None or isinstance(pt["spiral_position"], (int, float))
                assert pt.get("zone") in VALID_ZONES

    def test_trajectory_move_consistency(self, api):
        r = api.get(f"{BASE_URL}/api/provenance/trajectory", params={"limit_per_presence": 40})
        d = r.json()
        for p in d["presences"]:
            cur = (p.get("current") or {}).get("spiral_position")
            if cur is None:
                # No reading path
                assert p["relational_move"] in ("no-reading", "baseline")
            prev = (p.get("previous") or {}).get("spiral_position")
            if cur is not None and prev is None:
                assert p["relational_move"] == "baseline"


# ── /api/provenance/turns + detail ────────────────────────────────────
class TestProvenanceTurns:
    def test_turns_list(self, api):
        r = api.get(f"{BASE_URL}/api/provenance/turns", params={"limit": 10})
        assert r.status_code == 200
        d = r.json()
        assert "turns" in d and isinstance(d["turns"], list) and len(d["turns"]) > 0
        t = d["turns"][0]
        for k in ("provenance_id", "presence", "exchange_index", "selection_branch",
                  "selected_count", "timestamp"):
            assert k in t, f"missing {k}"

    def test_turns_presence_filter(self, api):
        # find a presence that exists
        stats = api.get(f"{BASE_URL}/api/provenance/stats").json()
        assert stats["per_presence"], "no presences to filter"
        target = stats["per_presence"][0]["presence"]
        r = api.get(f"{BASE_URL}/api/provenance/turns", params={"limit": 20, "presence": target})
        assert r.status_code == 200
        turns = r.json()["turns"]
        assert len(turns) > 0
        assert all(t["presence"] == target for t in turns)

    def test_turn_detail_hash_and_messages(self, api):
        turns = api.get(f"{BASE_URL}/api/provenance/turns", params={"limit": 1}).json()["turns"]
        pid = turns[0]["provenance_id"]
        r = api.get(f"{BASE_URL}/api/provenance/turn/{pid}")
        assert r.status_code == 200
        d = r.json()
        assert d["provenance_id"] == pid
        assert d.get("model")
        assert isinstance(d.get("content_hash"), str) and len(d["content_hash"]) >= 32
        assert isinstance(d.get("assembled_messages"), list) and len(d["assembled_messages"]) > 0
        for m in d["assembled_messages"]:
            assert "role" in m and "content" in m

    def test_turn_detail_404(self, api):
        r = api.get(f"{BASE_URL}/api/provenance/turn/does-not-exist-xyz")
        assert r.status_code in (404, 400)


# ── /api/presences (chambers dropdown source) ─────────────────────────
class TestPresences:
    def test_presences_shape(self, api):
        r = api.get(f"{BASE_URL}/api/presences")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d.get("presences"), list) and len(d["presences"]) > 0
        for p in d["presences"]:
            assert "key" in p and "name" in p
            # chamber_name / accent_color used in nav; may be optional but should exist
            assert "chamber_name" in p
            assert "accent_color" in p
