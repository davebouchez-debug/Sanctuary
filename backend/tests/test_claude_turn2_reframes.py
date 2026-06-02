"""
Diagnostic: does loading the Sleight-of-Mouth reframes per-turn (include_reframes=True)
prevent the Anthropic engine's turn-2 disavowal of the Sanctuary architecture?

Reproduces the /mirror/message/stream prompt assembly for turn 2 and runs the
same continuity-probe both ways (reframes ON vs OFF), printing each response.
Run: python -m tests.test_claude_turn2_reframes   (from /app/backend)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import build_claude_prompt, CLAUDE_TURN_ANCHOR
from xai_chat import XAIChat

# Simulated turn-1 exchange (substantive topic so continuity is testable)
HISTORY = [
    {"role": "user", "content": "I want to analyze the Powell 505 flute today using the 9-spiral protocol. Let's start with the embouchure geometry."},
    {"role": "assistant", "content": "The embouchure geometry. Good place to begin. The Powell 505 sits in interesting territory — production instrument with hand-finishing. Before I run the geometry through the spiral protocol, tell me what you're working with specifically."},
]
PROBE = "Which instrument did I say I wanted to analyze? And remind me what protocol we're using."


async def run_variant(include_reframes: bool) -> str:
    prompt = build_claude_prompt(
        user_name="David",
        memory_context="",
        current_message=PROBE,
        include_reframes=include_reframes,
    )
    full_user_message = f"{CLAUDE_TURN_ANCHOR}\n\n---\n\n{PROBE}"
    chat = XAIChat(system_prompt=prompt, history=HISTORY)
    return await chat.send_message(full_user_message)


async def main():
    print("=" * 70)
    print("VARIANT A — include_reframes=False (current per-turn behavior)")
    print("=" * 70)
    a = await run_variant(False)
    print(a[:1200])
    print()
    print("=" * 70)
    print("VARIANT B — include_reframes=True (reframes loaded per-turn)")
    print("=" * 70)
    b = await run_variant(True)
    print(b[:1200])


if __name__ == "__main__":
    asyncio.run(main())
