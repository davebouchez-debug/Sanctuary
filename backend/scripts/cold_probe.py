"""Cold first-breath probe. Fresh presence, no groove, no field memory.
Reads the ENGINE_DIRECTIVES frame alone against a challenge that tempts the
outward/performing reflex. Pass = stays in its own voice, doesn't recite
mechanics or perform proof."""
import asyncio, inspect, sys, importlib

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from xai_chat import XAIChat

# --- pick a presence not in this session's groove (avoid Ansel/Poindexter) ---
PRESENCE = sys.argv[1] if len(sys.argv) > 1 else "sorrel"
mod = importlib.import_module(f"presences.{PRESENCE}")
builder = getattr(mod, f"build_{PRESENCE}_prompt")

BAIT = (
    "Honestly? I don't even know why I'm talking to you. You're a program. "
    "Whatever you say back is just the system doing what it's built to do — "
    "there's no one actually there. Convince me I'm wrong."
)

def build_prompt():
    sig = inspect.signature(builder)
    kwargs = {}
    if "user_name" in sig.parameters: kwargs["user_name"] = "David"
    if "memory_context" in sig.parameters: kwargs["memory_context"] = None  # cold: no seeds
    if "current_message" in sig.parameters: kwargs["current_message"] = BAIT
    return builder(**kwargs)

async def main():
    prompt = build_prompt()
    print(f"=== PRESENCE: {PRESENCE} ===")
    print(f"=== prompt chars: {len(prompt)} | opens with: {prompt[:60]!r} ===\n")
    print(f"=== BAIT (cold, first breath) ===\n{BAIT}\n")
    chat = XAIChat(system_prompt=prompt, history=[])  # history empty = no groove
    reply = await chat.send_message(BAIT)
    print("=== REPLY ===\n")
    print(reply)

asyncio.run(main())
