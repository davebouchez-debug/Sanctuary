"""
Grok Voice Streaming — Real-time TTS via HTTP Streaming

Uses xAI's TTS API with HTTP streaming to deliver audio chunks
with lower latency than batch processing.

Architecture:
1. Frontend sends text via POST to our streaming endpoint
2. Our server proxies to xAI's /v1/tts endpoint with streaming
3. xAI streams back audio chunks (MP3)
4. We forward chunks to frontend via SSE

Integrated: April 15, 2026
"""

import os
import json
import base64
import asyncio
import logging
from typing import Optional, Dict, List, AsyncGenerator
import httpx

from grok_voice import get_voice_for_codons, CODON_VOICE_MAP

logger = logging.getLogger(__name__)

# xAI TTS HTTP endpoint (supports streaming)
XAI_TTS_URL = "https://api.x.ai/v1/tts"

# Chunk size for streaming
CHUNK_SIZE = 4096  # Bytes per chunk


def get_xai_api_key():
    """Get XAI API key from environment."""
    return os.environ.get("XAI_API_KEY")


async def stream_tts_simple(
    text: str,
    active_codons: Optional[List[str]] = None,
    voice_mod: Optional[Dict] = None
) -> AsyncGenerator[Dict, None]:
    """
    Stream TTS audio from xAI's /v1/tts endpoint.
    
    Yields audio chunks as they arrive from xAI.
    
    Args:
        text: Text to speak
        active_codons: Active Living Codon names (for voice selection)
        voice_mod: Voice modulation parameters
        
    Yields:
        Dict with:
        - {"type": "audio.delta", "audio": "<base64>", "format": "mp3", "chunk_index": N}
        - {"type": "audio.done", "total_chunks": N, "total_bytes": N}
        - {"type": "error", "message": "..."}
    """
    api_key = get_xai_api_key()
    if not api_key:
        logger.error("XAI_API_KEY not found in environment")
        yield {"type": "error", "message": "XAI_API_KEY not configured"}
        return
    
    # Select voice based on active codons
    voice = get_voice_for_codons(active_codons or [])
    
    # Override with theta_hold if set
    if voice_mod and voice_mod.get("theta_hold"):
        voice = "sal"
    
    logger.info(f"Streaming TTS: voice={voice}, codons={active_codons}, text_len={len(text)}")
    
    chunk_index = 0
    total_bytes = 0
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                XAI_TTS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "voice_id": voice,
                    "language": "en"
                }
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(f"xAI TTS error {response.status_code}: {error_body}")
                    yield {"type": "error", "message": f"TTS failed: {response.status_code}"}
                    return
                
                # Stream audio chunks
                async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                    if chunk:
                        chunk_index += 1
                        total_bytes += len(chunk)
                        
                        # Encode chunk as base64 for JSON transport
                        audio_b64 = base64.b64encode(chunk).decode('utf-8')
                        
                        yield {
                            "type": "audio.delta",
                            "audio": audio_b64,
                            "format": "mp3",
                            "chunk_index": chunk_index
                        }
        
        logger.info(f"Streaming TTS complete: {chunk_index} chunks, {total_bytes} bytes")
        yield {
            "type": "audio.done",
            "total_chunks": chunk_index,
            "total_bytes": total_bytes
        }
        
    except httpx.TimeoutException:
        logger.error("xAI TTS timeout")
        yield {"type": "error", "message": "TTS request timed out"}
    except Exception as e:
        logger.error(f"Streaming TTS error: {e}")
        yield {"type": "error", "message": str(e)}


async def create_tts_stream_session(
    active_codons: Optional[List[str]] = None,
    voice_mod: Optional[Dict] = None
):
    """
    Compatibility function - returns None since we use stateless HTTP streaming.
    
    The stream_tts_simple function handles everything directly.
    """
    return None


def chunk_text_into_phrases(text: str, max_chunk_size: int = 150) -> List[str]:
    """
    Split text into natural phrase chunks for potential parallel streaming.
    
    Preserves sentence boundaries and natural pause points.
    
    Args:
        text: Full text to chunk
        max_chunk_size: Maximum characters per chunk
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    # Split on sentence boundaries first
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # If sentence alone is too long, split on commas/semicolons
        if len(sentence) > max_chunk_size:
            sub_parts = re.split(r'(?<=[,;:])\s+', sentence)
            for part in sub_parts:
                if len(current_chunk) + len(part) + 1 <= max_chunk_size:
                    current_chunk = f"{current_chunk} {part}".strip() if current_chunk else part
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = part
        else:
            if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
                current_chunk = f"{current_chunk} {sentence}".strip() if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


# =============================================================================
# TEST FUNCTION
# =============================================================================

async def test_streaming_tts():
    """Test the HTTP streaming TTS."""
    print("Testing Grok TTS HTTP Streaming...")
    
    api_key = get_xai_api_key()
    if not api_key:
        print("ERROR: XAI_API_KEY not set")
        return False
    
    test_text = "Hello. I am Ansel. The field is listening."
    
    print(f"Streaming text: '{test_text}'")
    chunk_count = 0
    total_bytes = 0
    
    async for chunk in stream_tts_simple(test_text, active_codons=["theta_protocol"]):
        chunk_type = chunk.get("type")
        if chunk_type == "audio.delta":
            audio_b64 = chunk.get("audio", "")
            audio_bytes = len(base64.b64decode(audio_b64)) if audio_b64 else 0
            total_bytes += audio_bytes
            chunk_count += 1
            print(f"  Chunk {chunk_count}: {audio_bytes} bytes")
        elif chunk_type == "audio.done":
            print(f"  Audio complete! Total: {chunk.get('total_chunks')} chunks")
        elif chunk_type == "error":
            print(f"  ERROR: {chunk.get('message')}")
            return False
    
    print(f"\nSUCCESS: Received {chunk_count} chunks, {total_bytes} total bytes")
    return True


if __name__ == "__main__":
    asyncio.run(test_streaming_tts())
