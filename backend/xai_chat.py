"""
xAI Chat — Direct field access for Sanctuary presences.

Replaces the Emergent Integrations LlmChat wrapper with direct
xAI API calls via the OpenAI-compatible SDK. Supports:
  - Streaming token generation (true token-by-token)
  - Conversation history management per session
  - System prompt injection

Venice: "Direct tokenization bypasses textual mediation
and allows raw field access."
"""

import os
from typing import AsyncGenerator, List, Dict, Optional
from openai import AsyncOpenAI

_client = None

def get_xai_client() -> AsyncOpenAI:
    """Get or create the xAI async client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.environ.get("XAI_API_KEY"),
            base_url="https://api.x.ai/v1",
        )
    return _client


class XAIChat:
    """
    Manages a conversation session with an xAI model.
    Maintains message history and system prompt.
    """

    def __init__(self, system_prompt: str, model: str = "grok-3"):
        self.system_prompt = system_prompt
        self.model = model
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

    async def send_message(self, user_text: str) -> str:
        """Send a message and get the full response (non-streaming)."""
        self.messages.append({"role": "user", "content": user_text})

        client = get_xai_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=0.7,
        )

        assistant_text = response.choices[0].message.content or ""
        self.messages.append({"role": "assistant", "content": assistant_text})
        return assistant_text

    async def stream_message(self, user_text: str) -> AsyncGenerator[str, None]:
        """
        Send a message and stream the response token by token.
        Yields individual text chunks as they arrive.
        The voice discovers the words at the same moment the presence does.
        """
        self.messages.append({"role": "user", "content": user_text})

        client = get_xai_client()
        stream = await client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=0.7,
            stream=True,
        )

        full_response = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_response += delta.content
                yield delta.content

        # Save complete response to history
        self.messages.append({"role": "assistant", "content": full_response})

    def get_history_length(self) -> int:
        return len(self.messages)
