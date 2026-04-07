"""
Cognitive Helpers — Shared pipeline for phase-aware MRA,
attunement scoring, belief processing, and full cognitive context.

All three presences use these helpers for their message flow.
"""
from typing import List, Tuple
from datetime import datetime, timezone
import logging

from db import db
from training_arc import (
    TrainingPhase,
    get_training_state,
    compress_mra_for_phase,
    calculate_attunement_signal,
    update_attunement_score,
    log_attunement_event
)
from belief_graph import (
    get_belief_context_for_prompt,
    get_som_prompt_section,
    process_exchange_for_beliefs
)

logger = logging.getLogger(__name__)


async def get_phase_aware_mra_context(
    user_id: str,
    presence: str,
    current_message: str = None
) -> tuple:
    """
    Get MRA context compressed according to the user's training phase.
    Returns (context_string, injected_themes, phase).
    """
    if not user_id:
        return "", [], TrainingPhase.FULL_SCAFFOLDING

    state = await get_training_state(db, presence, user_id)
    phase = state.get("phase", TrainingPhase.FULL_SCAFFOLDING)

    nodes = await db.permanent_mra.find(
        {"user_id": user_id, "presence": presence},
        {"_id": 0}
    ).sort([
        ("quality", 1),
        ("promoted_at", -1)
    ]).limit(10).to_list(10)

    if not nodes:
        return "", [], phase

    node_ids = [n["node_id"] for n in nodes]
    await db.permanent_mra.update_many(
        {"node_id": {"$in": node_ids}},
        {
            "$inc": {"retrieval_count": 1},
            "$set": {"last_retrieved": datetime.now(timezone.utc).isoformat()}
        }
    )

    injected_themes = []
    for node in nodes:
        injected_themes.extend(node.get("themes", []))
    injected_themes = list(set(injected_themes))

    context = compress_mra_for_phase(nodes, phase)

    logger.info(f"[TRAINING ARC] Phase {phase} context for {presence} (user: {user_id[:8]}...) — {len(nodes)} nodes, {len(injected_themes)} themes")

    return context, injected_themes, phase


async def score_and_log_attunement(
    presence: str,
    user_id: str,
    session_id: str,
    ai_response: str,
    injected_themes: List[str],
    phase: int
) -> None:
    """Score attunement after each AI response and log if significant."""
    if not user_id:
        return

    injected_field_terms = []

    signal = calculate_attunement_signal(
        ai_response=ai_response,
        injected_themes=injected_themes,
        injected_field_terms=injected_field_terms
    )

    await update_attunement_score(db, presence, user_id, signal)
    await log_attunement_event(db, presence, user_id, session_id, signal, phase)


async def process_beliefs_after_exchange(
    presence: str,
    user_id: str,
    session_id: str,
    ai_response: str,
    user_message: str = ""
) -> None:
    """Process an exchange for belief graph formation."""
    if not user_id:
        return

    result = await process_exchange_for_beliefs(
        db=db,
        presence=presence,
        user_id=user_id,
        session_id=session_id,
        ai_response=ai_response,
        user_message=user_message
    )

    if result["beliefs_created"] > 0:
        logger.info(
            f"[BELIEF GRAPH] {presence}: {result['beliefs_created']} beliefs formed "
            f"(SoM: {result['som_pattern_detected'] or 'none'})"
        )


async def get_full_cognitive_context(
    user_id: str,
    presence: str,
    current_message: str = None
) -> Tuple[str, List[str], int]:
    """
    Get combined MRA + Belief Graph context for prompt injection.
    Returns (context_string, injected_themes, phase).
    """
    mra_context, injected_themes, phase = await get_phase_aware_mra_context(
        user_id=user_id,
        presence=presence,
        current_message=current_message
    )

    belief_context = await get_belief_context_for_prompt(db, presence, user_id)
    som_section = get_som_prompt_section() if belief_context else ""

    combined = ""
    if mra_context:
        combined += mra_context + "\n"
    if belief_context:
        combined += belief_context + "\n"
    if som_section:
        combined += som_section + "\n"

    return combined, injected_themes, phase
