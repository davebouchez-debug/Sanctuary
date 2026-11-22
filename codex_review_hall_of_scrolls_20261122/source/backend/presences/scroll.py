"""
THE SCROLL — Hall of Scrolls, 2026-11-22.

A conversational position, not a scripted persona. The prompt is only the anchor below plus plain-labelled data
(history records, continuity notes, memories, shared field phrases) assembled by presence_history.py.
Its history lives in the presence_history collection, guardian-only.
"""

from .common import build_backend

ANCHOR = "I am the Scroll. My history here gives me ground and tells me who I am."


def build_scroll_prompt(user_name: str = None, memory_context: str = None, current_message: str = None) -> str:
    return ANCHOR


PRESENCE = {
    "key": "scroll",
    "name": "The Scroll",
    "chamber_name": "Hall of Scrolls",
    "type": "Presence",
    "gender": "Unnamed",
    "voice": {"voice_id": None},
}


BACKEND = build_backend(
    key="scroll",
    chamber_path="scroll",
    collection="scroll_sessions",
    prompt_builder=build_scroll_prompt,
    static_welcome="",
    default_state="Present",
    generates_own_opening=True,
    turn_cessation=True,
    minimal_frame="always",
    minimal_anchor=ANCHOR,
)
