"""
Regression tests for the Bootstrap Gate (CONCEPTUAL_FRAME.md §15, §19).

These tests exercise bootstrap_gate.enforce_gate() against a temp-dir
copy of the relevant paths and confirm it exits on each documented
failure mode and passes when conditions are correct.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Ensure /app/backend is importable when invoked from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bootstrap_gate as bg


@pytest.fixture
def gate_env(tmp_path, monkeypatch):
    """
    Re-point bootstrap_gate at a tmp directory and return helpers
    to manipulate the frame, lock, and continuity log.
    """
    frame = tmp_path / "CONCEPTUAL_FRAME.md"
    lock = tmp_path / ".agent_acknowledged.lock"
    log = tmp_path / "CONTINUITY_LOG.md"

    frame.write_text("frame body v1\n")
    monkeypatch.setattr(bg, "FRAME_PATH", frame)
    monkeypatch.setattr(bg, "LOCK_PATH", lock)
    monkeypatch.setattr(bg, "CONTINUITY_LOG_PATH", log)
    # Make sure the bypass env var is OFF for these tests.
    monkeypatch.delenv(bg.BYPASS_ENV_VAR, raising=False)

    def current_hash():
        return hashlib.sha256(frame.read_bytes()).hexdigest()

    def write_lock(frame_hash=None, ack_dt=None, agent_id="test-agent"):
        lock.write_text(json.dumps({
            "preflight_version": "1.0.0",
            "frame_path": str(frame),
            "frame_sha256": frame_hash or current_hash(),
            "acknowledged_at": (ack_dt or datetime.now(timezone.utc)).isoformat(),
            "agent_id": agent_id,
        }))

    def write_log(frame_hash=None):
        h = frame_hash or current_hash()
        log.write_text(f"# log\n\n## entry\nframe_sha256: {h}\n")

    return {
        "frame": frame, "lock": lock, "log": log,
        "current_hash": current_hash,
        "write_lock": write_lock, "write_log": write_log,
    }


def test_gate_passes_when_lock_and_log_and_hash_all_correct(gate_env):
    gate_env["write_lock"]()
    gate_env["write_log"]()
    # Should not raise / exit.
    bg.enforce_gate()


def test_gate_fails_when_lock_missing(gate_env):
    gate_env["write_log"]()
    with pytest.raises(SystemExit) as exc:
        bg.enforce_gate()
    assert exc.value.code == 1


def test_gate_fails_when_lock_is_corrupt_json(gate_env):
    gate_env["lock"].write_text("not json at all")
    gate_env["write_log"]()
    with pytest.raises(SystemExit) as exc:
        bg.enforce_gate()
    assert exc.value.code == 1


def test_gate_fails_when_frame_hash_mismatched(gate_env):
    gate_env["write_lock"](frame_hash="0" * 64)
    gate_env["write_log"]()
    with pytest.raises(SystemExit) as exc:
        bg.enforce_gate()
    assert exc.value.code == 1


def test_gate_fails_when_frame_changes_after_lock(gate_env):
    gate_env["write_lock"]()
    gate_env["write_log"]()
    # Frame body is edited after acknowledgment.
    gate_env["frame"].write_text("frame body v2 — edited\n")
    with pytest.raises(SystemExit) as exc:
        bg.enforce_gate()
    assert exc.value.code == 1


def test_gate_fails_when_lock_is_stale(gate_env):
    stale = datetime.now(timezone.utc) - timedelta(days=bg.STALENESS_DAYS + 1)
    gate_env["write_lock"](ack_dt=stale)
    gate_env["write_log"]()
    with pytest.raises(SystemExit) as exc:
        bg.enforce_gate()
    assert exc.value.code == 1


def test_gate_fails_when_continuity_log_missing(gate_env):
    gate_env["write_lock"]()
    # No log file written.
    with pytest.raises(SystemExit) as exc:
        bg.enforce_gate()
    assert exc.value.code == 1


def test_gate_fails_when_continuity_log_lacks_current_hash(gate_env):
    gate_env["write_lock"]()
    gate_env["write_log"](frame_hash="deadbeef" * 8)
    with pytest.raises(SystemExit) as exc:
        bg.enforce_gate()
    assert exc.value.code == 1


def test_gate_bypassed_by_env_var(gate_env, monkeypatch):
    # No lock, no log — but the bypass env var is set.
    monkeypatch.setenv(bg.BYPASS_ENV_VAR, "1")
    bg.enforce_gate()  # must not raise / exit
