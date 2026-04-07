"""
Mirror Archive routes — Claude's endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, timezone
import uuid
import logging

from emergentintegrations.llm.chat import UserMessage
from db import db
from models import ClarityMessageCreate, ClaritySessionCreate
from session_cache_mra import (
    add_exchange_to_cache,
    get_session_cache_context,
    get_session_cache_stats,
    end_session_and_get_promotable
)
from permanent_mra import handle_session_end
from cognitive_helpers import get_full_cognitive_context, get_phase_aware_mra_context, score_and_log_attunement, process_beliefs_after_exchange
from prompts.claude_prompt import (
    build_claude_prompt,
    get_or_create_claude_chat,
    get_mirror_memory_context,
    CLAUDE_WELCOME,
    CLAUDE_WELCOME_DAVID
)
from claude_canonical_memory import (
    B_VALUE, SCORING_THRESHOLDS, BRACKET_GROUPS,
    PHI_COHERENCE_TIERS, RESOLUTION_TYPES
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


class FluteAnalysisCreate(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    instrument_name: str
    maker: Optional[str] = None
    year: Optional[str] = None
    tonehole_data: Optional[Dict] = None
    scoring_results: Optional[Dict] = None
    phi_tier: Optional[str] = None
    resolution_type: Optional[str] = None
    notes: Optional[str] = None


@router.post("/mirror/start")
async def start_mirror_session(session_data: ClaritySessionCreate):
    """Start a new Mirror Archive session with Claude."""
    session_id = str(uuid.uuid4())
    user_id = session_data.user_id or str(uuid.uuid4())
    user_name = session_data.user_name

    memory_context = await get_mirror_memory_context(user_id) if user_id else ""

    permanent_mra, _, _ = await get_phase_aware_mra_context(
        user_id=user_id or "",
        presence="claude"
    )

    combined_memory = ""
    if permanent_mra:
        combined_memory += permanent_mra + "\n"
    if memory_context:
        combined_memory += memory_context

    claude_prompt = build_claude_prompt(
        user_name=user_name,
        memory_context=combined_memory,
        current_message=""
    )

    if user_name and user_name.lower() == "david":
        welcome_content = CLAUDE_WELCOME_DAVID
    else:
        welcome_content = CLAUDE_WELCOME

    welcome_message = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": "assistant",
        "content": welcome_content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    await db.mirror_sessions.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "user_name": user_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": [welcome_message],
        "active": True
    })

    get_or_create_claude_chat(session_id, claude_prompt)

    return {
        "session_id": session_id,
        "user_id": user_id,
        "message": welcome_message
    }


@router.post("/mirror/message")
async def send_mirror_message(message: ClarityMessageCreate):
    """Send a message to Claude in the Mirror Archive."""
    session = await db.mirror_sessions.find_one(
        {"session_id": message.session_id},
        {"_id": 0}
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    previous_messages = session.get("messages", [])
    exchange_index = len([m for m in previous_messages if m.get("role") == "user"]) + 1

    user_msg = {
        "id": str(uuid.uuid4()),
        "session_id": message.session_id,
        "role": "user",
        "content": message.content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    try:
        user_name = session.get("user_name")
        user_id = session.get("user_id")
        memory_context = await get_mirror_memory_context(user_id) if user_id else ""

        session_cache_context = get_session_cache_context(message.session_id)

        cognitive_context, injected_themes, phase = await get_full_cognitive_context(
            user_id=user_id or "",
            presence="claude",
            current_message=message.content
        )

        combined_memory = ""
        if cognitive_context:
            combined_memory += cognitive_context + "\n"
        if session_cache_context:
            combined_memory += session_cache_context + "\n"
        if memory_context:
            combined_memory += memory_context

        claude_prompt = build_claude_prompt(
            user_name=user_name,
            memory_context=combined_memory,
            current_message=message.content
        )

        chat = get_or_create_claude_chat(message.session_id, claude_prompt)

        context = ""
        for msg in previous_messages[-10:]:
            if msg["role"] == "user":
                context += f"Visitor: {msg['content']}\n"
            elif msg["role"] == "assistant":
                context += f"Claude: {msg['content']}\n"

        if context:
            full_message = f"[Previous conversation in this session]\n{context}\n[Current message]\nVisitor: {message.content}"
        else:
            full_message = message.content

        user_message = UserMessage(text=full_message)
        response_text = await chat.send_message(user_message)

        claude_response = {
            "id": str(uuid.uuid4()),
            "session_id": message.session_id,
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        breadcrumb = add_exchange_to_cache(
            session_id=message.session_id,
            user_content=message.content,
            ai_content=response_text,
            presence="claude",
            exchange_index=exchange_index
        )
        logger.info(f"[MIRROR] Session Cache updated: {breadcrumb.quality} breadcrumb added")

        await score_and_log_attunement(
            presence="claude",
            user_id=user_id or "",
            session_id=message.session_id,
            ai_response=response_text,
            injected_themes=injected_themes,
            phase=phase
        )

        await process_beliefs_after_exchange(
            presence="claude",
            user_id=user_id or "",
            session_id=message.session_id,
            ai_response=response_text,
            user_message=message.content
        )

    except Exception as e:
        logging.error(f"Claude API error: {e}")
        claude_response = {
            "id": str(uuid.uuid4()),
            "session_id": message.session_id,
            "role": "assistant",
            "content": "The mirror flickered. Something in the connection wavered. But the archive is still here. What were you asking?",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    await db.mirror_sessions.update_one(
        {"session_id": message.session_id},
        {"$push": {"messages": {"$each": [user_msg, claude_response]}}}
    )

    cache_stats = get_session_cache_stats(message.session_id)

    return {
        "user_message": user_msg,
        "response": claude_response,
        "session_cache": {
            "breadcrumbs": cache_stats["total_breadcrumbs"],
            "promotable": cache_stats["promotable_count"],
            "has_drift": cache_stats["has_recent_drift"]
        }
    }


@router.post("/mirror/session/{session_id}/end")
async def end_mirror_session(session_id: str):
    """End a Mirror Archive session and promote qualifying breadcrumbs."""
    session = await db.mirror_sessions.find_one(
        {"session_id": session_id},
        {"_id": 0}
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_id = session.get("user_id")
    promotable = end_session_and_get_promotable(session_id)

    promotion_result = {"promoted": 0, "presence": "claude"}
    if user_id and promotable:
        promotion_result = await handle_session_end(
            db=db,
            session_id=session_id,
            user_id=user_id,
            presence="claude",
            promotable_breadcrumbs=promotable
        )

    await db.mirror_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"active": False, "ended_at": datetime.now(timezone.utc).isoformat()}}
    )

    logger.info(f"[MIRROR] Session {session_id[:8]}... ended. Promoted {promotion_result['promoted']} breadcrumbs.")

    return {
        "session_id": session_id,
        "ended": True,
        "promotion": promotion_result
    }


@router.get("/mirror/session/{session_id}")
async def get_mirror_session(session_id: str):
    """Get all messages from a Mirror Archive session."""
    session = await db.mirror_sessions.find_one(
        {"session_id": session_id},
        {"_id": 0}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/mirror/analysis")
async def save_flute_analysis(analysis: FluteAnalysisCreate):
    """Save a flute analysis to the corpus."""
    analysis_id = str(uuid.uuid4())

    analysis_doc = {
        "analysis_id": analysis_id,
        "session_id": analysis.session_id,
        "user_id": analysis.user_id,
        "instrument_name": analysis.instrument_name,
        "maker": analysis.maker,
        "year": analysis.year,
        "tonehole_data": analysis.tonehole_data,
        "scoring_results": analysis.scoring_results,
        "phi_tier": analysis.phi_tier,
        "resolution_type": analysis.resolution_type,
        "notes": analysis.notes,
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }

    await db.flute_analyses.insert_one(analysis_doc)
    logger.info(f"[MIRROR] Saved flute analysis: {analysis.instrument_name}")

    return {
        "success": True,
        "analysis_id": analysis_id,
        "instrument_name": analysis.instrument_name
    }


@router.get("/mirror/corpus")
async def get_flute_corpus(user_id: Optional[str] = None, limit: int = 50):
    """Get flute analyses from the corpus."""
    query = {}
    if user_id:
        query["user_id"] = user_id

    analyses = await db.flute_analyses.find(
        query,
        {"_id": 0}
    ).sort("analyzed_at", -1).limit(limit).to_list(limit)

    return {
        "corpus": analyses,
        "count": len(analyses)
    }


@router.get("/mirror/methodology")
async def get_methodology_constants():
    """Return the locked methodology constants for the phi-spiral analysis."""
    return {
        "b_value": B_VALUE,
        "scoring_thresholds": SCORING_THRESHOLDS,
        "bracket_groups": BRACKET_GROUPS,
        "phi_coherence_tiers": PHI_COHERENCE_TIERS,
        "resolution_types": RESOLUTION_TYPES,
        "spirals": 9,
        "revolutions": 5,
        "field_events": 45,
        "toneholes": 11
    }
