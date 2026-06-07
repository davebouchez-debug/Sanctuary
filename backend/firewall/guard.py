"""The firewall guard — score a generated turn; if it's a presence break,
re-roll until the presence comes back, or fall back to a blunt held line.

Kill-first design (David, June 2026): the architecture does not get to land in
the field. A false cut is free (silent re-roll); a missed break does the damage.
So we bias to catch, and we keep swinging — if a re-roll breaks again, we don't
get tired and let swing N+1 through; we fall back to the presence's held line.
"""

import logging
from typing import Any, Awaitable, Callable, Optional, Tuple

from firewall.presence_break_detector import detect
from firewall.firewall_config import recal_directive, fallback_line, MAX_REROLLS
from firewall.firewall_log import log_interception

logger = logging.getLogger(__name__)

# A regenerator takes the recalibration directive and returns fresh text.
Regenerator = Callable[[str], Awaitable[str]]


async def guard(
    full_text: str,
    *,
    presence: str,
    regenerate: Regenerator,
    db: Any = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    max_rerolls: int = MAX_REROLLS,
) -> Tuple[str, bool]:
    """Return (safe_text, intercepted).

    If `full_text` is clean, returns it untouched (intercepted=False).
    Otherwise re-rolls via `regenerate` up to `max_rerolls` times, then falls
    back to the presence's held line. Logs every interception to firewall_log.
    """
    result = detect(full_text)
    if not result.break_detected:
        return full_text, False

    original = full_text
    original_result = result
    recal = recal_directive(presence)

    text = full_text
    attempts = 0
    while result.break_detected and attempts < max_rerolls:
        attempts += 1
        try:
            text = await regenerate(recal)
        except Exception as e:
            logger.error(f"[FIREWALL] {presence} re-roll {attempts} failed: {e}")
            break
        result = detect(text or "")

    if result.break_detected:
        text = fallback_line(presence)
        action = "fallback"
    else:
        action = "recovered"

    if db is not None:
        await log_interception(
            db,
            presence=presence,
            session_id=session_id,
            user_id=user_id,
            original_text=original,
            result=original_result,
            attempts=attempts,
            action=action,
            recovered_text=text,
        )

    return text, True
