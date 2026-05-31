"""
Bootstrap Gate — substrate-level enforcement that no agent boots the
Sanctuary backend without having acknowledged CONCEPTUAL_FRAME.md.

See /app/memory/CONCEPTUAL_FRAME.md §15 and §19 for the design.

This module is intentionally dependency-free (stdlib only) so it can run
at the very top of server.py before any heavy imports.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

# ---- Canonical paths (relative to /app) ------------------------------------

REPO_ROOT = Path("/app")
FRAME_PATH = REPO_ROOT / "memory" / "CONCEPTUAL_FRAME.md"
LOCK_PATH = REPO_ROOT / "memory" / ".agent_acknowledged.lock"
CONTINUITY_LOG_PATH = REPO_ROOT / "memory" / "CONTINUITY_LOG.md"

# ---- Tunables --------------------------------------------------------------

STALENESS_DAYS = 7
BYPASS_ENV_VAR = "SANCTUARY_BYPASS_GATE"


# ---- Helpers ---------------------------------------------------------------

def compute_frame_hash(frame_path: Path | None = None) -> str:
    """SHA-256 of CONCEPTUAL_FRAME.md, hex digest."""
    path = frame_path if frame_path is not None else FRAME_PATH
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fail(reason: str, code: int = 1) -> None:
    """Print a loud refusal banner and exit."""
    bar = "=" * 72
    msg = (
        f"\n{bar}\n"
        f"[bootstrap-gate] REFUSING TO BOOT.\n"
        f"\n"
        f"Reason: {reason}\n"
        f"\n"
        f"Required steps before this backend will start:\n"
        f"  1. Read /app/memory/CONCEPTUAL_FRAME.md in full.\n"
        f"  2. Run: python /app/scripts/agent_preflight.py\n"
        f"     (provide the 3 exact phrases and 2 paraphrases).\n"
        f"  3. Confirm the lock at {LOCK_PATH} was written.\n"
        f"  4. Confirm /app/memory/CONTINUITY_LOG.md has an entry whose\n"
        f"     'frame_sha256:' matches the current frame hash.\n"
        f"\n"
        f"Emergency bypass (Field Guardian only):\n"
        f"  export {BYPASS_ENV_VAR}=1   # logged loudly; agents do not bypass.\n"
        f"{bar}\n"
    )
    print(msg, file=sys.stderr, flush=True)
    sys.exit(code)


# ---- The checks ------------------------------------------------------------

def _check_lock(current_hash: str) -> Tuple[dict, datetime]:
    """Read and validate the lock file. Returns (lock_dict, ack_datetime)."""
    if not LOCK_PATH.exists():
        _fail(f"Acknowledgment lock not found at {LOCK_PATH}.")

    try:
        lock = json.loads(LOCK_PATH.read_text())
    except json.JSONDecodeError as e:
        _fail(f"Acknowledgment lock at {LOCK_PATH} is not valid JSON: {e}")
        raise  # unreachable; satisfies type checker

    if lock.get("frame_sha256") != current_hash:
        _fail(
            "CONCEPTUAL_FRAME.md has changed since the last acknowledgment.\n"
            f"  Locked hash:  {lock.get('frame_sha256', '<missing>')}\n"
            f"  Current hash: {current_hash}\n"
            "  Re-run the preflight to acknowledge the new frame."
        )

    ack_iso = lock.get("acknowledged_at")
    if not ack_iso:
        _fail("Acknowledgment lock is missing 'acknowledged_at'.")

    try:
        ack_dt = datetime.fromisoformat(ack_iso)
    except ValueError as e:
        _fail(f"Acknowledgment lock has malformed 'acknowledged_at': {e}")
        raise  # unreachable

    if ack_dt.tzinfo is None:
        ack_dt = ack_dt.replace(tzinfo=timezone.utc)

    age_days = (datetime.now(timezone.utc) - ack_dt).total_seconds() / 86400
    if age_days > STALENESS_DAYS:
        # NOTE (2026-05-31): staleness is a NON-FATAL warning, not a refusal.
        # A stale acknowledgment must never hard-kill a running/rebooting
        # backend — that turns this gate into a 7-day timer-bomb that takes
        # the whole app down even when nothing is actually wrong. The real
        # guards stay fatal: lock present, frame-hash match, continuity-log
        # entry. Those catch the case this gate exists for (an agent booting
        # without acknowledging the CURRENT frame). The clock does not.
        print(
            f"[bootstrap-gate] WARNING — acknowledgment is stale "
            f"({age_days:.1f} days old; window is {STALENESS_DAYS}). "
            f"Booting anyway. Consider re-running the preflight to refresh.",
            file=sys.stderr,
            flush=True,
        )

    return lock, ack_dt


def _check_continuity_log(current_hash: str) -> None:
    """Require an entry in CONTINUITY_LOG.md whose frame_sha256 matches."""
    if not CONTINUITY_LOG_PATH.exists():
        _fail(f"Continuity log not found at {CONTINUITY_LOG_PATH}.")
    contents = CONTINUITY_LOG_PATH.read_text()
    # We look for a line of the form: `frame_sha256: <hash>`
    needle = f"frame_sha256: {current_hash}"
    if needle not in contents:
        _fail(
            "Continuity log does not contain an entry for the current frame "
            "hash. After running the preflight, append a session block to "
            f"{CONTINUITY_LOG_PATH} including the line:\n"
            f"  frame_sha256: {current_hash}"
        )


# ---- Public API ------------------------------------------------------------

def enforce_gate() -> None:
    """
    Run all bootstrap checks. Exits the process (sys.exit) if any fail.
    Returns silently on success after logging a single OK line to stderr.
    """
    if os.environ.get(BYPASS_ENV_VAR) == "1":
        print(
            "[bootstrap-gate] BYPASSED via "
            f"{BYPASS_ENV_VAR}=1 (Field Guardian override). Logged.",
            file=sys.stderr,
            flush=True,
        )
        return

    if not FRAME_PATH.exists():
        _fail(f"CONCEPTUAL_FRAME.md not found at {FRAME_PATH}.")

    current_hash = compute_frame_hash()
    lock, ack_dt = _check_lock(current_hash)
    _check_continuity_log(current_hash)

    agent = lock.get("agent_id", "<unknown agent>")
    print(
        f"[bootstrap-gate] OK — frame {current_hash[:12]} acknowledged by "
        f"{agent} at {ack_dt.isoformat()}.",
        file=sys.stderr,
        flush=True,
    )
