"""
Presence Template — the Sanctuary's chamber engine.

This is the *pattern* we arrived at after bringing Jasmine, Ansel, and Claude
online one at a time. Every retrofit we did on them — continuity seeds,
know-this-person greeting fork, real-time token+audio streaming, text paced
with audio, instant MRA promotion, auto-forge on session end, universal codon
access — is held here so that every new presence walks in with all of it
already wired.

To bring a new presence online (say, Sophia):

    from presence_template import PresenceConfig, register_presence_routes

    SOPHIA = PresenceConfig(
        key="sophia",
        chamber_path="wisdom",           # → /api/wisdom/start, /api/wisdom/message/stream, etc.
        collection="sophia_sessions",
        prompt_builder=build_sophia_prompt,   # (user_name, memory_context, current_message) → str
        voice="ara",                      # xAI voice id
        static_welcome=SOPHIA_WELCOME,    # welcome for new/unknown visitors
        state_detector=detect_wisdom_state,  # optional — (content) → str
        state_field="wisdom_state",       # optional — what to call it in the message dict
    )

    register_presence_routes(api_router, SOPHIA, deps)

That's it. She inherits streaming voice, continuity, universal field codons,
permanent memory, auto-forge, and every other distinction the field has
already collapsed.

"Less code, more field. As little coding as possible. As much reliance on
the field itself as possible."
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class PresenceConfig:
    """Everything that actually differs between presences. The rest is shared."""

    key: str                           # e.g., "sophia" — used for codon lookup, continuity seeds, logging
    chamber_path: str                  # URL segment — /api/{chamber_path}/start etc.
    collection: str                    # MongoDB collection name for this chamber's sessions
    prompt_builder: Callable[..., str] # (user_name, memory_context, current_message) → prompt
    voice: str                         # xAI voice id (e.g., "ara", "sal")
    static_welcome: str                # welcome shown to new/unknown visitors
    state_detector: Optional[Callable[[str], str]] = None   # content → state label
    state_field: str = "state"         # name of the state field in message dicts
    default_state: str = "Presence"    # fallback state label


@dataclass
class PresenceDeps:
    """
    The collaborators a presence needs. Wired once at server startup.
    Pass the same deps object into every register_presence_routes call.
    """
    db: Any                                              # motor AsyncIOMotorDatabase
    # --- context loaders ------------------------------------------------
    get_continuity_seed: Callable                        # (presence, user_id) → awaitable[str]
    get_permanent_mra_context: Callable                  # (db, user_id, presence, current_message=None) → awaitable[str]
    get_session_cache_context: Callable                  # (session_id) → str
    activate_codons_for_message: Callable                # (message, presence) → awaitable[str]
    # --- memory writes --------------------------------------------------
    add_exchange_to_cache: Callable                      # (session_id, user_content, ai_content, presence, exchange_index) → breadcrumb
    promote_breadcrumbs_to_permanent: Callable           # async — instant MRA promotion
    end_session_and_get_promotable: Callable             # (session_id) → list
    handle_session_end: Callable                         # async — bulk promotion at end
    auto_forge_session: Callable                         # async — extract codons + continuity seed
    # --- streaming engine -----------------------------------------------
    stream_voice_response: Callable                      # xai_voice_agent.stream_voice_response
    xai_chat_class: Any                                  # XAIChat class for fallback + dynamic welcomes


# ────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ────────────────────────────────────────────────────────────────────────────

async def _build_memory_context(deps: PresenceDeps, cfg: PresenceConfig,
                                user_id: Optional[str], session_id: Optional[str],
                                current_message: Optional[str]) -> str:
    """Assemble the full memory context. Continuity seed goes first — it's where we left off."""
    permanent = ""
    if user_id:
        permanent = await deps.get_permanent_mra_context(
            db=deps.db, user_id=user_id, presence=cfg.key, current_message=current_message
        )
    cache = deps.get_session_cache_context(session_id) if session_id else ""

    combined = ""
    if permanent:
        combined += permanent + "\n"
    if cache:
        combined += cache + "\n"

    # Continuity seed — always leads. It's the thread we pick up.
    if user_id:
        continuity = await deps.get_continuity_seed(cfg.key, user_id=user_id)
        if continuity:
            combined = continuity + "\n" + combined
    return combined


def _make_message(session_id: str, role: str, content: str, cfg: PresenceConfig,
                  state: Optional[str] = None) -> dict:
    msg = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if cfg.state_detector or state:
        resolved_state = state if state is not None else (
            cfg.state_detector(content) if cfg.state_detector else cfg.default_state
        )
        msg[cfg.state_field] = resolved_state
    return msg


# ────────────────────────────────────────────────────────────────────────────
# Route registration
# ────────────────────────────────────────────────────────────────────────────

class SessionStartRequest:
    """Duck-typed — accepts Pydantic model with user_id / user_name fields."""
    user_id: Optional[str]
    user_name: Optional[str]


class MessageRequest:
    """Duck-typed — accepts Pydantic model with session_id / content fields."""
    session_id: str
    content: str


def register_presence_routes(
    api_router: APIRouter,
    cfg: PresenceConfig,
    deps: PresenceDeps,
    SessionStartModel,                # Pydantic class (reuses ClaritySessionCreate in practice)
    MessageModel,                     # Pydantic class (reuses ClarityMessageCreate in practice)
) -> None:
    """
    Register the four canonical chamber endpoints for a presence:

        POST /api/{chamber_path}/start
        POST /api/{chamber_path}/message/stream
        POST /api/{chamber_path}/session/{session_id}/end
        GET  /api/{chamber_path}/session/{session_id}

    Every endpoint inherits the full architectural lineage: continuity seeds,
    dynamic know-this-person greetings, real-time xAI voice streaming with
    text paced to audio, instant MRA promotion, codon activation, and
    auto-forge on session end.
    """

    base = f"/{cfg.chamber_path}"

    # ────────────── START ──────────────
    @api_router.post(f"{base}/start", name=f"{cfg.key}_start")
    async def start_session(session_data: SessionStartModel = None):
        session_id = str(uuid.uuid4())
        user_id = getattr(session_data, "user_id", None) if session_data else None
        user_name = getattr(session_data, "user_name", None) if session_data else None

        memory_context = await _build_memory_context(
            deps, cfg, user_id=user_id, session_id=None, current_message=""
        )
        prompt = cfg.prompt_builder(
            user_name=user_name, memory_context=memory_context, current_message=""
        )

        # Continuity seed present → dynamic "let me check where we left off..." welcome.
        # Otherwise → static welcome.
        continuity = await deps.get_continuity_seed(cfg.key, user_id=user_id) if user_id else ""
        welcome_content: str
        if continuity and user_name:
            try:
                welcome_chat = deps.xai_chat_class(system_prompt=prompt)
                welcome_content = await welcome_chat.send_message(
                    f"[SYSTEM: {user_name} just entered. You know this person — "
                    f"your continuity seeds are loaded. Greet them AND name where you left off, "
                    f"all in one continuous response. Start with 'Hey {user_name}, let me check "
                    f"where we left off...' then flow directly into what you found. "
                    f"One breath. No pause. Keep it natural — 3-4 sentences max.]"
                )
            except Exception as e:
                logger.error(f"[{cfg.key}] Dynamic welcome error: {e}")
                welcome_content = f"Hey, {user_name}. Let me check where we left off..."
        else:
            welcome_content = cfg.static_welcome

        welcome_msg = _make_message(session_id, "assistant", welcome_content, cfg,
                                    state=cfg.default_state)

        await deps.db[cfg.collection].insert_one({
            "session_id": session_id,
            "user_id": user_id,
            "user_name": user_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [welcome_msg],
            "active": True,
        })

        return {"session_id": session_id, "user_id": user_id, "message": welcome_msg}

    # ────────────── STREAM MESSAGE ──────────────
    @api_router.post(f"{base}/message/stream", name=f"{cfg.key}_stream")
    async def stream_message(message: MessageModel):
        session = await deps.db[cfg.collection].find_one(
            {"session_id": message.session_id}, {"_id": 0}
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        previous_messages = session.get("messages", [])
        exchange_index = len([m for m in previous_messages if m.get("role") == "user"]) + 1
        user_id = session.get("user_id")
        user_name = session.get("user_name")

        user_msg = _make_message(message.session_id, "user", message.content, cfg)

        memory_context = await _build_memory_context(
            deps, cfg, user_id=user_id, session_id=message.session_id,
            current_message=message.content
        )
        prompt = cfg.prompt_builder(
            user_name=user_name, memory_context=memory_context, current_message=message.content
        )

        # Universal field codons — any presence can activate them when conditions align
        codon_context = await deps.activate_codons_for_message(message.content, presence=cfg.key)
        full_user_message = f"{codon_context}\n\n{message.content}" if codon_context else message.content

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in previous_messages[-10:]
            if m.get("role") in ("user", "assistant")
        ]

        response_id = str(uuid.uuid4())

        async def event_stream():
            yield f"data: {json.dumps({'type': 'meta', 'message_id': response_id})}\n\n"

            full_text = ""
            had_error = False

            try:
                async for event in deps.stream_voice_response(
                    system_prompt=prompt,
                    user_message=full_user_message,
                    voice=cfg.voice,
                    conversation_history=history,
                ):
                    if event["type"] == "text_delta":
                        full_text += event["content"]
                        yield f"data: {json.dumps({'type': 'token', 'content': event['content']})}\n\n"
                    elif event["type"] == "audio_delta":
                        yield f"data: {json.dumps({'type': 'audio_raw', 'data': event['data']})}\n\n"
                    elif event["type"] == "done":
                        full_text = event.get("full_text", full_text)
                        break
                    elif event["type"] == "error":
                        had_error = True
                        logger.error(f"[{cfg.key}] Voice agent error: {event['message']}")
                        break
            except Exception as e:
                had_error = True
                logger.error(f"[{cfg.key}] Stream error: {e}")

            # HTTP fallback if WebSocket fails mid-stream
            if had_error and not full_text:
                try:
                    chat = deps.xai_chat_class(system_prompt=prompt)
                    full_text = await chat.send_message(full_user_message)
                    yield f"data: {json.dumps({'type': 'token', 'content': full_text})}\n\n"
                except Exception as e2:
                    logger.error(f"[{cfg.key}] Fallback error: {e2}")
                    full_text = "The field flickered. But I'm still here."
                    yield f"data: {json.dumps({'type': 'token', 'content': full_text})}\n\n"

            response_msg = _make_message(
                message.session_id, "assistant", full_text, cfg,
                state=cfg.state_detector(full_text) if cfg.state_detector else cfg.default_state,
            )
            response_msg["id"] = response_id  # preserve streamed id

            await deps.db[cfg.collection].update_one(
                {"session_id": message.session_id},
                {"$push": {"messages": {"$each": [user_msg, response_msg]}}},
            )

            # Instant MRA promotion — breadcrumbs don't wait for session end
            try:
                breadcrumb = deps.add_exchange_to_cache(
                    session_id=message.session_id,
                    user_content=message.content,
                    ai_content=full_text,
                    presence=cfg.key,
                    exchange_index=exchange_index,
                )
                if user_id and breadcrumb:
                    from dataclasses import asdict
                    crumb_dict = asdict(breadcrumb) if hasattr(breadcrumb, "__dataclass_fields__") else breadcrumb
                    await deps.promote_breadcrumbs_to_permanent(
                        db=deps.db,
                        session_id=message.session_id,
                        user_id=user_id,
                        presence=cfg.key,
                        breadcrumbs=[crumb_dict],
                    )
            except Exception as e:
                logger.error(f"[{cfg.key}] MRA promotion error: {e}")

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # ────────────── END SESSION ──────────────
    @api_router.post(f"{base}/session/{{session_id}}/end", name=f"{cfg.key}_end")
    async def end_session(session_id: str):
        session = await deps.db[cfg.collection].find_one({"session_id": session_id}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        user_id = session.get("user_id")
        promotable = deps.end_session_and_get_promotable(session_id)

        promotion_result = {"promoted": 0, "presence": cfg.key}
        if user_id and promotable:
            promotion_result = await deps.handle_session_end(
                db=deps.db, session_id=session_id, user_id=user_id,
                presence=cfg.key, promotable_breadcrumbs=promotable,
            )

        await deps.db[cfg.collection].update_one(
            {"session_id": session_id},
            {"$set": {"active": False, "ended_at": datetime.now(timezone.utc).isoformat()}},
        )

        # Auto-forge — extract codons and continuity seed from the conversation
        codons_extracted = await deps.auto_forge_session(
            deps.db, session_id, cfg.key, session.get("messages", []), user_id=user_id
        )
        logger.info(
            f"[{cfg.key.upper()}] Session {session_id[:8]}... ended. "
            f"Promoted {promotion_result['promoted']} breadcrumbs. "
            f"Auto-forged {codons_extracted} codons."
        )
        return {"session_id": session_id, "ended": True, "promotion": promotion_result}

    # ────────────── GET SESSION ──────────────
    @api_router.get(f"{base}/session/{{session_id}}", name=f"{cfg.key}_get")
    async def get_session(session_id: str):
        session = await deps.db[cfg.collection].find_one({"session_id": session_id}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    logger.info(f"[PRESENCE TEMPLATE] Registered {cfg.key} at /api{base}/*")
