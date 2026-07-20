"""Vision bridge — describe a shared image so a text-only presence can respond.

The presences run on DeepSeek (text-only). When someone shares an image, this
asks a vision model for a faithful description, which is then handed to the
presence as context. She responds to what the image shows, in her own voice,
still on DeepSeek. Uses the EMERGENT_LLM_KEY (universal key).
"""

import os
import base64
import logging
import uuid

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You describe images faithfully and vividly for someone who cannot see them. "
    "Be concrete: name the objects, people, setting, colours, mood, and any visible "
    "text. Do not interpret meaning or add commentary — just describe what is there, "
    "clearly, in 2-5 sentences."
)


async def describe_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    chat = LlmChat(
        api_key=key,
        session_id=f"vision-{uuid.uuid4()}",
        system_message=_SYSTEM,
    ).with_model("openai", "gpt-4o")

    resp = await chat.send_message(
        UserMessage(text="Describe this image.", file_contents=[ImageContent(image_base64=b64)])
    )
    return resp if isinstance(resp, str) else str(resp)
