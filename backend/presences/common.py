"""
Common helpers for presence files. Optional — presences can be defined
without it, but `build_backend()` keeps a single canonical shape for
the BACKEND dict and gives us one place to add fields later.
"""

from typing import Callable, Optional


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
    }
