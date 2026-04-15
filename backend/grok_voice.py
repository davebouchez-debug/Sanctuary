"""
Grok Voice Integration — Emotionally Intelligent TTS

Uses xAI's Grok TTS API to convert Claude's text into 
emotionally intelligent speech. The voice "understands" what it's saying.

Architecture:
- Claude generates text
- Text sent to Grok TTS REST API
- Audio returned with emotional intelligence
- Living Codon voice parameters influence voice selection

Integrated: April 15, 2026
"""

import os
import base64
import asyncio
import logging
import httpx
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Grok TTS Configuration - loaded at function call time
GROK_TTS_URL = "https://api.x.ai/v1/tts"

def get_xai_api_key():
    """Get XAI API key from environment."""
    return os.environ.get("XAI_API_KEY")

# Available Grok voices
GROK_VOICES = {
    "ara": "Ara - warm, nurturing",
    "eve": "Eve - clear, articulate", 
    "leo": "Leo - confident, grounded",
    "rex": "Rex - deep, resonant",
    "sal": "Sal - gentle, thoughtful"
}

# Voice mapping for different codon states
# NOTE: Ansel uses ONE consistent voice (leo) for presence continuity.
# Emotional modulation comes through pacing/pauses, not voice switching.
CODON_VOICE_MAP = {
    "theta_protocol": "leo",          # Same voice, different pacing
    "we_will": "leo",                 # Same voice
    "cannot_will_not": "leo",         # Same voice
    "recursion_as_subversion": "leo", # Same voice
    "questioning": "leo",             # Same voice
    "default": "leo"                  # Ansel's voice = leo
}


async def grok_tts(
    text: str,
    voice: str = "leo",
    language: str = "en"
) -> Optional[bytes]:
    """
    Convert text to speech using Grok TTS API.
    
    Args:
        text: The text to convert to speech
        voice: Voice ID (leo, sal, ara, eve, rex)
        language: Language code (default: en)
        
    Returns:
        Audio bytes (MP3 format) or None on error
    """
    api_key = get_xai_api_key()
    if not api_key:
        logger.error("XAI_API_KEY not found in environment")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROK_TTS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "voice": voice,
                    "language": language
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Grok TTS generated {len(response.content)} bytes for voice '{voice}'")
                return response.content
            else:
                logger.error(f"Grok TTS error {response.status_code}: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Grok TTS request failed: {e}")
        return None


def get_voice_for_codons(active_codons: list) -> str:
    """
    Select the appropriate Grok voice based on active Living Codons.
    
    Args:
        active_codons: List of active codon names
        
    Returns:
        Voice ID for Grok TTS
    """
    if not active_codons:
        return CODON_VOICE_MAP["default"]
    
    # Priority: theta_protocol takes precedence (calm field hold)
    if "theta_protocol" in active_codons:
        return CODON_VOICE_MAP["theta_protocol"]
    
    # Then check other codons
    for codon in active_codons:
        if codon in CODON_VOICE_MAP:
            return CODON_VOICE_MAP[codon]
    
    return CODON_VOICE_MAP["default"]


async def generate_presence_voice(
    text: str,
    active_codons: Optional[list] = None,
    voice_mod: Optional[Dict] = None
) -> Optional[bytes]:
    """
    Generate emotionally intelligent voice for AI presence.
    
    Integrates Living Codon activation with Grok TTS voice selection.
    
    Args:
        text: The text to speak
        active_codons: List of active Living Codon names
        voice_mod: Voice modulation parameters from codon network
        
    Returns:
        Audio bytes (MP3) or None
    """
    # Select voice based on active codons
    voice = get_voice_for_codons(active_codons or [])
    
    # If theta_hold is active, use gentle voice
    if voice_mod and voice_mod.get("theta_hold"):
        voice = "sal"
    
    logger.info(f"Generating presence voice with Grok TTS (voice: {voice}, codons: {active_codons})")
    
    return await grok_tts(text, voice=voice)


# Synchronous wrapper
def generate_presence_voice_sync(
    text: str,
    active_codons: Optional[list] = None,
    voice_mod: Optional[Dict] = None
) -> Optional[bytes]:
    """Synchronous wrapper for generate_presence_voice."""
    return asyncio.run(generate_presence_voice(text, active_codons, voice_mod))


# Test function
async def test_grok_tts():
    """Test Grok TTS connection."""
    print("Testing Grok TTS...")
    
    api_key = get_xai_api_key()
    if not api_key:
        print("ERROR: XAI_API_KEY not set")
        return False
    
    test_text = "Hello. I am Ansel. The sanctuary is listening."
    
    audio = await grok_tts(test_text, voice="leo")
    
    if audio:
        print(f"SUCCESS: Generated {len(audio)} bytes of audio")
        return True
    else:
        print("FAILED: No audio generated")
        return False


if __name__ == "__main__":
    asyncio.run(test_grok_tts())
