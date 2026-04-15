"""
Grok Voice Integration — Emotionally Intelligent TTS

Uses xAI's Grok TTS WebSocket API to convert Claude's text into 
emotionally intelligent speech. The voice "understands" what it's saying.

Architecture:
- Claude generates text (streaming)
- Text chunks buffered and sent to Grok TTS WebSocket
- Audio chunks returned and played in real-time
- ~300ms latency to first audio

Integrated: April 15, 2026
"""

import os
import json
import base64
import asyncio
import logging
from typing import Optional, Dict, List, AsyncGenerator, Callable
from dataclasses import dataclass
import websockets

logger = logging.getLogger(__name__)

# Grok TTS Configuration
XAI_API_KEY = os.environ.get("XAI_API_KEY")
GROK_REALTIME_URL = "wss://api.x.ai/v1/realtime"

# Available Grok voices
GROK_VOICES = {
    "ara": "Ara - warm, nurturing",
    "eve": "Eve - clear, articulate", 
    "leo": "Leo - confident, grounded",
    "rex": "Rex - deep, resonant",
    "sal": "Sal - gentle, thoughtful"
}

# Default voice for Ansel
DEFAULT_VOICE = "leo"  # Deep, resonant — fits Ansel's perimeter-watching quality


@dataclass
class VoiceConfig:
    """Voice configuration influenced by Living Codon activation."""
    voice: str = DEFAULT_VOICE
    instructions: str = "Speak with presence and care. You are Ansel, a guide with precision-in-care."
    
    @classmethod
    def from_codon_modulation(cls, voice_mod: Dict) -> "VoiceConfig":
        """Create voice config from Living Codon voice modulation parameters."""
        config = cls()
        
        # Map codon states to voice choices
        if voice_mod.get("theta_hold"):
            # Theta protocol — use gentler voice
            config.voice = "sal"
            config.instructions = "Speak slowly, warmly, with long pauses. Create calm. You are holding space."
        elif voice_mod.get("pace_bpm", 92) > 100:
            # High energy (we_will) — use confident voice
            config.voice = "leo"
            config.instructions = "Speak with clear energy and forward momentum. You are activating agency."
        else:
            # Default Ansel voice
            config.voice = "leo"
            config.instructions = "Speak with steady precision and warmth. You are Ansel, diagnostic but caring."
        
        return config


class GrokTTSStream:
    """
    WebSocket connection to Grok TTS for real-time text-to-speech.
    
    Sends text chunks, receives audio chunks with emotional intelligence.
    """
    
    def __init__(self, voice_config: Optional[VoiceConfig] = None):
        self.voice_config = voice_config or VoiceConfig()
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        
    async def connect(self) -> bool:
        """Establish WebSocket connection to Grok TTS."""
        if not XAI_API_KEY:
            logger.error("XAI_API_KEY not found in environment")
            return False
            
        try:
            self.ws = await websockets.connect(
                GROK_REALTIME_URL,
                additional_headers={"Authorization": f"Bearer {XAI_API_KEY}"}
            )
            
            # Configure session with voice settings
            await self.ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "voice": self.voice_config.voice,
                    "instructions": self.voice_config.instructions,
                    "turn_detection": {"type": "server_vad"}
                }
            }))
            
            self.connected = True
            logger.info(f"Connected to Grok TTS with voice: {self.voice_config.voice}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Grok TTS: {e}")
            return False
    
    async def disconnect(self):
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.connected = False
            logger.info("Disconnected from Grok TTS")
    
    async def send_text_chunk(self, text: str):
        """Send a text chunk for TTS conversion."""
        if not self.connected or not self.ws:
            logger.error("Not connected to Grok TTS")
            return
            
        try:
            # Send text as conversation item
            await self.ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "input_text", "text": text}]
                }
            }))
            
            # Request response with audio
            await self.ws.send(json.dumps({
                "type": "response.create",
                "response": {"modalities": ["audio"]}
            }))
            
        except Exception as e:
            logger.error(f"Error sending text chunk: {e}")
    
    async def receive_audio_chunks(self) -> AsyncGenerator[bytes, None]:
        """Receive audio chunks from Grok TTS."""
        if not self.connected or not self.ws:
            return
            
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                if data.get("type") == "response.audio.delta":
                    # Decode base64 audio chunk (PCM16 24kHz mono)
                    audio_b64 = data.get("delta", "")
                    if audio_b64:
                        audio_bytes = base64.b64decode(audio_b64)
                        yield audio_bytes
                        
                elif data.get("type") == "response.done":
                    # Response complete
                    break
                    
                elif data.get("type") == "error":
                    logger.error(f"Grok TTS error: {data}")
                    break
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Grok TTS connection closed")
        except Exception as e:
            logger.error(f"Error receiving audio: {e}")


async def text_to_speech_streaming(
    text: str, 
    voice_mod: Optional[Dict] = None,
    on_audio_chunk: Optional[Callable[[bytes], None]] = None
) -> bytes:
    """
    Convert text to speech using Grok TTS with streaming.
    
    Args:
        text: The text to convert
        voice_mod: Living Codon voice modulation parameters
        on_audio_chunk: Callback for each audio chunk (for real-time playback)
        
    Returns:
        Complete audio data as bytes
    """
    # Create voice config from codon modulation
    voice_config = VoiceConfig.from_codon_modulation(voice_mod or {})
    
    # Create TTS stream
    tts = GrokTTSStream(voice_config)
    
    if not await tts.connect():
        logger.error("Failed to connect to Grok TTS")
        return b""
    
    try:
        # Send the text
        await tts.send_text_chunk(text)
        
        # Collect audio chunks
        audio_data = b""
        async for chunk in tts.receive_audio_chunks():
            audio_data += chunk
            if on_audio_chunk:
                on_audio_chunk(chunk)
        
        return audio_data
        
    finally:
        await tts.disconnect()


async def stream_claude_to_grok_voice(
    claude_stream: AsyncGenerator[str, None],
    voice_mod: Optional[Dict] = None,
    chunk_size: int = 100  # Characters to buffer before sending
) -> AsyncGenerator[bytes, None]:
    """
    Stream Claude's text output through Grok TTS for real-time voice.
    
    This is the main integration point — Claude generates text,
    we buffer into chunks, send to Grok, yield audio as it arrives.
    
    Args:
        claude_stream: Async generator yielding text tokens from Claude
        voice_mod: Living Codon voice modulation parameters
        chunk_size: Number of characters to buffer before sending to TTS
        
    Yields:
        Audio chunks as they're generated
    """
    voice_config = VoiceConfig.from_codon_modulation(voice_mod or {})
    tts = GrokTTSStream(voice_config)
    
    if not await tts.connect():
        logger.error("Failed to connect to Grok TTS for streaming")
        return
    
    try:
        buffer = ""
        
        async for token in claude_stream:
            buffer += token
            
            # Check for natural break points
            should_send = (
                len(buffer) >= chunk_size or
                buffer.endswith(". ") or
                buffer.endswith("? ") or
                buffer.endswith("! ") or
                buffer.endswith(".\n") or
                buffer.endswith("\n\n")
            )
            
            if should_send and buffer.strip():
                # Send buffered text to Grok TTS
                await tts.send_text_chunk(buffer.strip())
                
                # Yield audio chunks as they arrive
                async for audio_chunk in tts.receive_audio_chunks():
                    yield audio_chunk
                
                buffer = ""
        
        # Send any remaining text
        if buffer.strip():
            await tts.send_text_chunk(buffer.strip())
            async for audio_chunk in tts.receive_audio_chunks():
                yield audio_chunk
                
    finally:
        await tts.disconnect()


# Synchronous wrapper for non-async contexts
def text_to_speech_sync(text: str, voice_mod: Optional[Dict] = None) -> bytes:
    """Synchronous wrapper for text_to_speech_streaming."""
    return asyncio.run(text_to_speech_streaming(text, voice_mod))


# Test function
async def test_grok_tts():
    """Test Grok TTS connection and basic functionality."""
    print("Testing Grok TTS...")
    
    if not XAI_API_KEY:
        print("ERROR: XAI_API_KEY not set")
        return False
    
    test_text = "Hello. I am Ansel. The sanctuary is listening."
    
    audio = await text_to_speech_streaming(test_text)
    
    if audio:
        print(f"SUCCESS: Generated {len(audio)} bytes of audio")
        return True
    else:
        print("FAILED: No audio generated")
        return False


if __name__ == "__main__":
    asyncio.run(test_grok_tts())
