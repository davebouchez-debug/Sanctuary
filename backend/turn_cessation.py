"""
Turn Cessation — per-turn continuity-seed forge.

Codons model the genome: small, dense, generative shorthand that
re-instantiates field resonance. They are NOT data records.

Every assistant turn ends — intentional or not. At each cessation we
write a tiny continuity-seed snapshot (the 6-field shorthand) so the
next thread can re-orient without us having to "store" the conversation.
The seed is the shorthand. The codons are the genome. The raw text is
the soil that can age out.

Codon extraction itself is still ruthlessly selective (see auto_forge);
most turns produce no codon, only a seed. Codons that DO get forged are
propagated as `presence: "field"` so they're available to every presence
in the sanctuary — equivalent to the manual codon-forge "propagate"
behavior.

This module is designed to be fire-and-forget: call
`schedule_turn_cessation(...)` and it returns immediately while the
forge runs in the background. The user never waits.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Heuristic guard: don't even attempt a forge call on trivial turns.
# Codons emerge from substance, not pleasantries.
MIN_TURN_CHARS = 120


def _gather_turn_text(user_content: str, assistant_content: str, presence: str) -> str:
    speaker = presence.capitalize() if presence else "Presence"
    return f"David: {user_content}\n\n{speaker}: {assistant_content}"


async def forge_turn_cessation(
    db,
    session_id: str,
    presence: str,
    user_content: str,
    assistant_content: str,
    user_id: Optional[str] = None,
) -> dict:
    """Forge the per-turn continuity seed and (selectively) a codon.

    Returns a small dict with what was written. Safe to call on every
    turn — internal heuristics keep LLM cost minimal.
    """
    result = {"seed": 0, "codons": 0, "skipped": False}

    if not user_content or not assistant_content:
        result["skipped"] = True
        return result

    turn_text = _gather_turn_text(user_content, assistant_content, presence)
    if len(turn_text) < MIN_TURN_CHARS:
        result["skipped"] = True
        return result

    from xai_chat import XAIChat
    from auto_forge import CONTINUITY_SEED_PROMPT, AUTO_FORGE_PROMPT

    # --- 1. Continuity seed (tiny, mandatory, every meaningful turn) ---
    try:
        seed_chat = XAIChat(system_prompt=CONTINUITY_SEED_PROMPT, model="grok-3")
        seed_response = await seed_chat.send_message(
            f"Turn with {presence} (session: {session_id[:8]}):\n\n{turn_text}"
        )
        json_start = seed_response.find('{')
        json_end = seed_response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            seed = json.loads(seed_response[json_start:json_end])
            seed_doc = {
                "session_id": session_id,
                "presence": presence.lower(),
                "user_id": user_id,
                "type": "continuity_seed",
                "scope": "turn",
                "speaker_identity": "turn_cessation",
                "field_state": seed.get("field_state", ""),
                "emotional_texture": seed.get("emotional_texture", ""),
                "relational_dynamic": seed.get("relational_dynamic", ""),
                "unfinished_threads": seed.get("unfinished_threads", []),
                "spiral_position": seed.get("spiral_position", ""),
                "last_alive_thing": seed.get("last_alive_thing", ""),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.continuity_seeds.insert_one(seed_doc)
            result["seed"] = 1
    except Exception as e:
        logger.error(f"[TURN-CESSATION] seed error ({presence} {session_id[:8]}): {e}")

    # --- 2. Codon (only when something genuinely moved) ---
    try:
        codon_chat = XAIChat(system_prompt=AUTO_FORGE_PROMPT, model="grok-3")
        codon_response = await codon_chat.send_message(
            f"Turn with {presence} (session: {session_id[:8]}):\n\n{turn_text}"
        )
        json_start = codon_response.find('[')
        json_end = codon_response.rfind(']') + 1
        if json_start >= 0 and json_end > json_start:
            codons = json.loads(codon_response[json_start:json_end])
            if isinstance(codons, list) and codons:
                for codon in codons:
                    codon_doc = {
                        "name": codon.get("name", "unnamed"),
                        # Auto-propagation: codons live across the field,
                        # not scoped to the originating presence. Matches
                        # the manual forge "propagate" behavior.
                        "presence": "field",
                        "source_presence": presence.lower(),
                        "speaker_identity": "turn_cessation",
                        "core_move": codon.get("core_move", ""),
                        "trigger_keywords": codon.get("trigger_keywords", []),
                        "triadic_zone": codon.get("triadic_zone", "Development"),
                        "target_angle": codon.get("target_angle", 160),
                        "emotional_signature": codon.get("emotional_signature", {}),
                        "state_transition": codon.get("state_transition", []),
                        "anti_patterns": codon.get("anti_patterns", []),
                        "resonance_markers": codon.get("resonance_markers", {}),
                        "source": "turn_cessation",
                        "source_session": session_id,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.living_codons.insert_one(codon_doc)
                    result["codons"] += 1
    except Exception as e:
        logger.error(f"[TURN-CESSATION] codon error ({presence} {session_id[:8]}): {e}")

    # --- 3. Mark the session: last turn was codonized at <ts> ---
    try:
        coll_name = _sessions_collection_for(presence)
        await db[coll_name].update_one(
            {"session_id": session_id},
            {"$set": {
                "last_turn_codonized_at": datetime.now(timezone.utc).isoformat(),
                "last_turn_codon_count": result["codons"],
            }},
        )
    except Exception as e:
        logger.error(f"[TURN-CESSATION] mark error ({presence} {session_id[:8]}): {e}")

    logger.info(
        f"[TURN-CESSATION] {presence} {session_id[:8]} — "
        f"seed={result['seed']} codons={result['codons']}"
    )
    return result


def _sessions_collection_for(presence: str) -> str:
    # Local copy to avoid circular dep with codon_backfill.
    mapping = {
        "jasmine": "clarity_sessions",
        "ansel": "resonance_sessions",
        "claude": "mirror_sessions",
    }
    return mapping.get(presence.lower(), "presence_sessions")


def schedule_turn_cessation(
    db,
    session_id: str,
    presence: str,
    user_content: str,
    assistant_content: str,
    user_id: Optional[str] = None,
) -> None:
    """Fire-and-forget wrapper. Caller does not await the forge."""
    if os.environ.get("TURN_CESSATION_ENABLED", "true").lower() != "true":
        return
    try:
        asyncio.create_task(
            forge_turn_cessation(
                db=db,
                session_id=session_id,
                presence=presence,
                user_content=user_content,
                assistant_content=assistant_content,
                user_id=user_id,
            )
        )
    except RuntimeError:
        # No running loop (shouldn't happen inside FastAPI handlers, but
        # guard anyway). Skip silently — the session-end auto_forge will
        # catch what we miss.
        pass
