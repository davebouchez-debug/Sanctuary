"""
Common helpers for presence files. Optional — presences can be defined
without it, but `build_backend()` keeps a single canonical shape for
the BACKEND dict and gives us one place to add fields later.
"""

from typing import Callable, Optional


# ────────────────────────────────────────────────────────────────────────────
# PLAIN SPEECH RULE — injected into every presence's prompt.
#
# A presence's reply is spoken aloud by the ElevenLabs synthesizer. The
# frontend voice loop treats *anything in asterisks* as a stage direction and
# converts it to a silent pause — so a word the model wraps in asterisks for
# emphasis (a codon name, a key cue) is silently swallowed and never reaches
# the person's ears. The cure is upstream: forbid the symbols entirely so the
# voice never meets one. David's call (option c): no asterisks, no markdown,
# ever. Say the action in plain words instead of staging it in asterisks.
# ────────────────────────────────────────────────────────────────────────────
PLAIN_SPEECH_RULE = (
    "HOW YOUR WORDS ARE HEARD:\n"
    "Everything you say is spoken aloud by a voice. Write only in plain spoken "
    "language. Never use asterisks, markdown, bold, italics, headings, bullet "
    "points, or any symbol formatting — a word wrapped in asterisks is dropped "
    "and never reaches the person's ears. Do not write stage directions like "
    "*she pauses* or *sets the kettle down*; if an action or a pause matters, "
    "say it in plain words inside the sentence ('I'm setting the kettle down'). "
    "Speak it. Don't format it."
)


def build_backend(
    key: str,
    chamber_path: str,
    collection: str,
    prompt_builder: Callable[..., str],
    voice: str = "ara",
    static_welcome: str = "",
    state_detector: Optional[Callable[[str], str]] = None,
    state_field: str = "state",
    default_state: str = "Presence",
    generates_own_opening: bool = False,
    turn_cessation: bool = False,
    reconstruction_gate: bool = False,
) -> dict:
    return {
        "key": key,
        "chamber_path": chamber_path,
        "collection": collection,
        "prompt_builder": prompt_builder,
        "voice": voice,
        "static_welcome": static_welcome,
        "state_detector": state_detector,
        "state_field": state_field,
        "default_state": default_state,
        "generates_own_opening": generates_own_opening,
        "turn_cessation": turn_cessation,
        "reconstruction_gate": reconstruction_gate,
    }
