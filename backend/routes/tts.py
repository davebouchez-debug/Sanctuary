"""
Text-to-Speech endpoint using OpenAI TTS via Emergent Integrations.
"""
import os
import re
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from emergentintegrations.llm.openai import OpenAITextToSpeech
from models import TTSRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Voice configurations per presence
PRESENCE_VOICES = {
    "jasmine": {
        "voice": "nova",
        "speed": 0.95,
    },
    "ansel": {
        "voice": "ash",
        "speed": 1.1,
    },
    "claude": {
        "voice": "echo",
        "speed": 1.0,
    }
}


@router.post("/tts/speak")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech using OpenAI TTS with presence-specific voices."""
    try:
        voice_config = PRESENCE_VOICES.get(request.presence.lower(), PRESENCE_VOICES["jasmine"])

        clean_text = request.text
        clean_text = re.sub(r'\*[^*]+\*', '', clean_text)
        clean_text = re.sub(r'^[A-Za-z]+\s*[·]\s*[A-Za-z\s]+$', '', clean_text, flags=re.MULTILINE)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        if not clean_text:
            return JSONResponse(content={"error": "No speakable text after cleaning"}, status_code=400)

        tts = OpenAITextToSpeech(api_key=os.getenv("EMERGENT_LLM_KEY"))

        audio_base64 = await tts.generate_speech_base64(
            text=clean_text,
            model="tts-1",
            voice=voice_config["voice"],
            speed=voice_config["speed"],
            response_format="opus"
        )

        return {
            "audio": audio_base64,
            "format": "opus",
            "presence": request.presence,
            "voice": voice_config["voice"]
        }

    except ValueError as e:
        logger.error(f"TTS validation error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        return JSONResponse(content={"error": "Speech generation failed"}, status_code=500)
