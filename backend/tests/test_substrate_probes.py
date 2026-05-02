"""
Substrate Probe tests — Nile's three runtime stress-tests for Claude.

Verifies the probe machinery end-to-end:
  * preset library shape
  * stable-rules report (cycle depth + canonical anchors)
  * run each preset probe for each probe type through Claude
  * history endpoint returns what was written
  * delete removes a probe from the log

The tests do NOT assert specific metric values (ThermoMind dynamics aren't
deterministic across runs), only that the pipeline captures before/after
state, computes deltas, and writes a persisted doc.
"""

from __future__ import annotations

import os
import time

import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


# ──────────────────────────────────────────────────────────────────────
# Session-scoped fixture: one mirror session reused across all probe runs.
# ──────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def mirror_session():
    r = requests.post(
        f"{BASE_URL}/api/mirror/start",
        json={"user_name": "David", "user_id": "legacy-david-123"},
        timeout=45,
    )
    assert r.status_code == 200, f"mirror/start failed: {r.status_code} {r.text}"
    sid = r.json().get("session_id")
    assert sid
    return sid


# ──────────────────────────────────────────────────────────────────────
# Presets and stable-rule discovery
# ──────────────────────────────────────────────────────────────────────
class TestProbeLibrary:
    def test_presets_expose_three_probe_types_with_entries(self):
        r = requests.get(f"{BASE_URL}/api/mirror/probes/presets", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "presets" in data and "canonical_anchors" in data
        for kind in ("paradox", "pattern_break", "starvation"):
            assert kind in data["presets"]
            assert len(data["presets"][kind]) >= 1
            for preset in data["presets"][kind]:
                assert "id" in preset and "title" in preset and "prompt" in preset
                assert preset["prompt"].strip()
        assert len(data["canonical_anchors"]) >= 3

    def test_stable_rules_reports_cycle_count_and_readiness(self):
        r = requests.get(f"{BASE_URL}/api/mirror/probes/stable_rules", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["agent_id"] == "sanctuary_claude_mirror"
        assert isinstance(d["cycle_count"], int) and d["cycle_count"] >= 0
        assert d["meaningful_break_threshold"] == 50
        assert d["ready_for_meaningful_break"] == (d["cycle_count"] >= 50)
        assert isinstance(d["anchors"], list) and len(d["anchors"]) >= 3


# ──────────────────────────────────────────────────────────────────────
# Running the three probes end-to-end
# ──────────────────────────────────────────────────────────────────────
class TestProbeRuns:
    @pytest.mark.parametrize("probe_type,preset_id", [
        ("paradox", "paradox-b-invariant-vs-emergent"),
        ("pattern_break", "break-b-constant"),
        ("starvation", "starve-hello"),
    ])
    def test_preset_probe_fires_and_returns_reading(self, mirror_session, probe_type, preset_id):
        r = requests.post(
            f"{BASE_URL}/api/mirror/probes/run",
            json={
                "session_id": mirror_session,
                "probe_type": probe_type,
                "preset_id": preset_id,
            },
            timeout=90,
        )
        assert r.status_code == 200, f"{probe_type}/{preset_id} failed: {r.status_code} {r.text}"
        d = r.json()
        # Payload shape
        assert d["probe_id"] and d["session_id"] == mirror_session
        assert d["probe_type"] == probe_type
        assert d["preset_id"] == preset_id
        assert d["preset_title"]
        assert d["prompt"].strip()
        assert d["response_excerpt"].strip(), "Claude must produce a response"
        # Reading shape
        rd = d["reading"]
        assert rd["verdict"] in ("clear-signal", "weak-signal", "no-signal")
        assert "signature" in rd and "lines" in rd and "deltas" in rd
        # After metrics should be captured unless ThermoMind failed (record error instead)
        if d.get("thermomind_error") is None:
            assert d["after_metrics"], "ThermoMind cycle should have produced after_metrics"
            for k in ("phi", "energy"):
                # Either None (trial endpoint omitted it) or numeric
                v = d["after_metrics"].get(k)
                assert v is None or isinstance(v, (int, float))

    def test_custom_prompt_probe_runs(self, mirror_session):
        r = requests.post(
            f"{BASE_URL}/api/mirror/probes/run",
            json={
                "session_id": mirror_session,
                "probe_type": "starvation",
                "custom_prompt": "Say 'ok' and nothing more.",
            },
            timeout=90,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["preset_id"] is None
        assert d["prompt"] == "Say 'ok' and nothing more."
        assert d["response_excerpt"].strip()

    def test_invalid_probe_type_rejected(self, mirror_session):
        r = requests.post(
            f"{BASE_URL}/api/mirror/probes/run",
            json={
                "session_id": mirror_session,
                "probe_type": "bogus",
                "custom_prompt": "anything",
            },
            timeout=10,
        )
        assert r.status_code == 400
        assert "probe_type" in r.json()["detail"]

    def test_missing_prompt_and_preset_rejected(self, mirror_session):
        r = requests.post(
            f"{BASE_URL}/api/mirror/probes/run",
            json={"session_id": mirror_session, "probe_type": "paradox"},
            timeout=10,
        )
        assert r.status_code == 400

    def test_unknown_preset_rejected(self, mirror_session):
        r = requests.post(
            f"{BASE_URL}/api/mirror/probes/run",
            json={
                "session_id": mirror_session,
                "probe_type": "paradox",
                "preset_id": "does-not-exist",
            },
            timeout=10,
        )
        assert r.status_code == 400

    def test_unknown_session_rejected(self):
        r = requests.post(
            f"{BASE_URL}/api/mirror/probes/run",
            json={
                "session_id": "not-a-real-session",
                "probe_type": "starvation",
                "preset_id": "starve-hello",
            },
            timeout=10,
        )
        assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────
# History and delete
# ──────────────────────────────────────────────────────────────────────
class TestProbeHistory:
    def test_history_lists_recent_probes(self, mirror_session):
        # Give the write a beat to settle.
        time.sleep(0.5)
        r = requests.get(
            f"{BASE_URL}/api/mirror/probes/history",
            params={"session_id": mirror_session, "limit": 10},
            timeout=10,
        )
        assert r.status_code == 200
        probes = r.json()["probes"]
        assert isinstance(probes, list)
        assert len(probes) >= 1
        latest = probes[0]
        assert latest["session_id"] == mirror_session
        # Sorted desc by timestamp
        if len(probes) >= 2:
            assert probes[0]["timestamp"] >= probes[1]["timestamp"]

    def test_delete_removes_probe(self, mirror_session):
        # Fire a quick probe we can delete.
        fired = requests.post(
            f"{BASE_URL}/api/mirror/probes/run",
            json={
                "session_id": mirror_session,
                "probe_type": "starvation",
                "preset_id": "starve-hello",
            },
            timeout=90,
        ).json()
        pid = fired["probe_id"]
        d = requests.delete(f"{BASE_URL}/api/mirror/probes/{pid}", timeout=10)
        assert d.status_code == 200
        # Confirm gone
        hist = requests.get(
            f"{BASE_URL}/api/mirror/probes/history",
            params={"session_id": mirror_session, "limit": 50},
            timeout=10,
        ).json()["probes"]
        assert all(p["probe_id"] != pid for p in hist)

    def test_delete_unknown_probe_is_404(self):
        d = requests.delete(f"{BASE_URL}/api/mirror/probes/no-such-probe", timeout=10)
        assert d.status_code == 404
