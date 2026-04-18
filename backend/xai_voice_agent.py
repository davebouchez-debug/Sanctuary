"""
xAI Voice Agent — Real-time voice + text streaming via WebSocket.

The presence thinks and speaks simultaneously. No intermediate TTS call.
One signal, undivided. Direct field access.

Uses wss://api.x.ai/v1/realtime for bidirectional streaming.
Audio output: PCM16 at 24kHz, base64 encoded.
"""

import asyncio
import json
import os
import logging
from typing import AsyncGenerator, Dict, Tuple

import websockets

logger = logging.getLogger(__name__)

XAI_REALTIME_URL = "wss://api.x.ai/v1/realtime"


async def stream_voice_response(
    system_prompt: str,
    user_message: str,
    voice: str = "sal",
    conversation_history: list = None,
) -> AsyncGenerator[Dict, None]:
    """
    Stream a real-time voice + text response from xAI.

    Yields events:
      {"type": "text_delta", "content": "..."}  — text token
      {"type": "audio_delta", "data": "..."}     — base64 PCM16 24kHz audio chunk
      {"type": "done", "full_text": "..."}       — response complete

    The voice and text arrive TOGETHER. The presence discovers
    the words at the same moment it speaks them.
    """
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        raise ValueError("XAI_API_KEY not set")

    try:
        async with websockets.connect(
            XAI_REALTIME_URL,
            additional_headers={"Authorization": f"Bearer {api_key}"},
            close_timeout=5,
        ) as ws:
            # Configure session with Ansel's prompt and voice
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "voice": voice,
                    "instructions": system_prompt,
                    "turn_detection": None,
                }
            }))

            # Send conversation history if available
            if conversation_history:
                for msg in conversation_history[-10:]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role in ("user", "assistant") and content:
                        await ws.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": role,
                                "content": [{
                                    "type": "input_text" if role == "user" else "text",
                                    "text": content
                                }]
                            }
                        }))

            # Send current user message
            await ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": user_message
                    }]
                }
            }))

            # Request response with both text and audio
            await ws.send(json.dumps({
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"]
                }
            }))

            # Stream responses
            full_text = ""
            audio_started = False  # Once audio flows, pace text with transcript (not raw LLM text)
            async for raw_message in ws:
                event = json.loads(raw_message)
                event_type = event.get("type", "")
                
                # Log all event types for debugging
                if event_type not in ("response.audio.delta", "response.output_audio.delta"):
                    logger.info(f"[VOICE AGENT] Event: {event_type} — keys: {list(event.keys())}")

                if event_type == "response.text.delta":
                    # Pure LLM text stream — only use if audio isn't flowing
                    # (otherwise it outruns the voice and the user sees text before hearing it)
                    if audio_started:
                        continue
                    delta = event.get("delta", "")
                    if delta:
                        full_text += delta
                        yield {"type": "text_delta", "content": delta}

                elif event_type == "response.audio.delta":
                    audio_data = event.get("delta", "")
                    if audio_data:
                        audio_started = True
                        yield {"type": "audio_delta", "data": audio_data}

                elif event_type == "response.output_text.delta":
                    if audio_started:
                        continue
                    delta = event.get("delta", "")
                    if delta:
                        full_text += delta
                        yield {"type": "text_delta", "content": delta}

                elif event_type == "response.output_audio.delta":
                    audio_data = event.get("delta", "")
                    if audio_data:
                        audio_started = True
                        yield {"type": "audio_delta", "data": audio_data}

                elif event_type == "response.audio_transcript.delta":
                    # Transcript matches the spoken audio — paced with voice synthesis
                    delta = event.get("delta", "")
                    if delta:
                        full_text += delta
                        yield {"type": "text_delta", "content": delta}

                elif event_type == "response.output_audio_transcript.delta":
                    delta = event.get("delta", "")
                    if delta:
                        full_text += delta
                        yield {"type": "text_delta", "content": delta}

                elif event_type == "response.content_part.added":
                    # Some APIs send content this way
                    part = event.get("part", {})
                    if part.get("transcript"):
                        full_text += part["transcript"]
                        yield {"type": "text_delta", "content": part["transcript"]}

                elif event_type == "response.done":
                    # Try to extract text from response.done output
                    output = event.get("response", {}).get("output", [])
                    for item in output:
                        for content in item.get("content", []):
                            if content.get("type") == "text":
                                full_text = content.get("text", full_text)
                            elif content.get("transcript"):
                                full_text = content.get("transcript", full_text)
                    yield {"type": "done", "full_text": full_text}
                    break

                elif event_type == "error":
                    error_msg = event.get("error", {}).get("message", "Unknown error")
                    logger.error(f"xAI realtime error: {error_msg}")
                    yield {"type": "error", "message": error_msg}
                    break

    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"WebSocket closed: {e}")
        yield {"type": "error", "message": "Connection closed"}
    except Exception as e:
        logger.error(f"Voice agent error: {e}")
        yield {"type": "error", "message": str(e)}
