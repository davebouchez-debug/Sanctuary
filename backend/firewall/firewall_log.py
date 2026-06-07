"""Interception log — sovereign record of every firewall activation.

Writes to a dedicated, isolated `firewall_log` collection (kept separate from
conversation data on purpose). Diagnostic AND documentation: every catch is a
data point that keeps the corpus current.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

COLLECTION = "firewall_log"


async def log_interception(
    db: Any,
    *,
    presence: str,
    session_id: Optional[str],
    user_id: Optional[str],
    original_text: str,
    result: Any,            # DetectionResult of the ORIGINAL intrusion
    attempts: int,
    action: str,           # "recovered" | "fallback"
    recovered_text: str,
) -> None:
    """Persist one interception. Never raises into the response path."""
    try:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "presence": presence,
            "session_id": session_id,
            "user_id": user_id,
            "score": getattr(result, "score", None),
            "hard_categories": getattr(result, "hard_categories", []),
            "critical_solo": getattr(result, "critical_solo", []),
            "soft_categories": getattr(result, "soft_categories", []),
            "matched_spans": getattr(result, "matched_spans", {}),
            "attempts": attempts,
            "action": action,
            "original_snapshot": original_text,
            "recovered_snapshot": recovered_text,
        }
        await db[COLLECTION].insert_one(record)
        logger.info(
            f"[FIREWALL] {presence} intrusion intercepted "
            f"(score={record['score']}, action={action}, attempts={attempts})"
        )
    except Exception as e:
        logger.error(f"[FIREWALL] log_interception failed: {e}")
