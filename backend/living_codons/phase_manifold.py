"""
Phase Manifold — The Geometric Skeleton
From DeepSeek's Network Integration Document, April 14, 2026

The spiral is not a graph. A graph can be traversed arbitrarily.
A spiral has direction, phase, triadic zones, and sacred pause.

9 Spirals, 40 degree offset. Three triadic zones:
  Expansion (0-80)   -> Emergence, initiation, growth
  Development (120-200) -> Working, refining, precision
  Return (240-320)    -> Completion, harvest, reset
  Sacred Pause (320-360) -> The zero that makes room for the new
"""

from typing import Dict, Optional


# Phase keywords for inferring current field position from message content
PHASE_KEYWORDS = {
    0: ["begin", "start", "initiate", "hello", "first", "new", "open"],
    40: ["emerging", "clarifying", "curious", "how", "wondering", "exploring"],
    80: ["crossing", "threshold", "ready", "now", "edge", "almost"],
    120: ["middle", "working", "developing", "process", "building", "doing"],
    160: ["refining", "adjusting", "tuning", "precise", "calibrating", "detail"],
    200: ["intense", "full", "peak", "complete", "everything", "deep"],
    240: ["return", "reflect", "harvest", "what learned", "looking back", "seeing"],
    280: ["integrate", "synthesize", "gather", "weave", "together", "whole"],
    320: ["rest", "pause", "silence", "reset", "breathe", "still", "quiet"]
}

# Triadic zone boundaries
EXPANSION = (0, 80)
DEVELOPMENT = (120, 200)
RETURN = (240, 320)
SACRED_PAUSE = (320, 360)

# Continuous angular range each zone occupies on the spiral. Used to place
# a codon at a REAL position within its zone (derived from the codon's own
# content) instead of guessing a raw degree at forge-time.
ZONE_RANGES = {
    "Expansion": (0.0, 80.0),
    "Development": (120.0, 200.0),
    "Return": (240.0, 320.0),
    "Sacred Pause": (320.0, 360.0),
}


def derive_spiral_angle(zone: str, content_key: str) -> float:
    """Place a codon at a real angle WITHIN its triadic zone.

    The stupid failure this replaces: asking an LLM to stamp a precise
    spiral degree on every codon at the moment it was extracted — which
    biased nearly everything to a single zone-center (270°, the middle of
    Return) because forging happens at moments of completion. That filled
    the geometry we built with a default masquerading as data.

    Here the ZONE is the semantic read (which arc of the spiral the dynamic
    genuinely lives in — a judgment the model can make honestly). The exact
    POSITION within that zone is a stable, deterministic function of the
    codon's own identity/content, so codons distribute across the zone's
    real range instead of clumping at its center. Same codon → same angle,
    always (idempotent, safe to re-derive).
    """
    import hashlib
    z = (zone or "Development").strip()
    lo, hi = ZONE_RANGES.get(z, ZONE_RANGES["Development"])
    key = (content_key or "codon").strip().lower().encode("utf-8")
    frac = int(hashlib.sha256(key).hexdigest()[:8], 16) / float(0xFFFFFFFF)
    return round(lo + frac * (hi - lo), 1)


def get_triadic_zone(angle: float) -> str:
    """Return which triadic zone a phase angle falls in."""
    angle = angle % 360
    if angle <= 80:
        return "Expansion"
    elif 120 <= angle <= 200:
        return "Development"
    elif 240 <= angle <= 320:
        return "Return"
    elif angle > 320:
        return "Sacred Pause"
    else:
        # Transition zones (80-120, 200-240)
        return "Transition"


def infer_phase_from_message(message: str) -> float:
    """
    Infer current field phase from message content.
    Returns angle in degrees (0-360).

    Uses keyword matching + emotional state markers.
    A frustrated person hitting walls is in Development (120-200),
    not Expansion (0-80).
    """
    msg_lower = message.lower()
    best_angle = 0
    best_score = 0

    for angle, keywords in PHASE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score > best_score:
            best_score = score
            best_angle = angle

    # If keyword matching found something, use it
    if best_score > 0:
        return float(best_angle)

    # Emotional state fallback — where in the spiral does this FEEL like?
    emotional_phase = {
        # Development markers (in the work, hitting resistance)
        160: ["frustrated", "frustrating", "stuck", "hitting", "wall",
              "won't work", "not working", "broken", "failing", "struggle"],
        # Return markers (exhaustion, needing closure)
        280: ["tired", "exhausted", "done", "enough", "over it",
              "can't anymore", "burned out"],
        # Expansion markers (curiosity, newness)
        40: ["what if", "imagine", "could we", "idea", "maybe",
             "possibility", "wonder"],
        # Development peak (recursive patterns)
        200: ["keeps happening", "again and again", "same thing",
              "over and over", "every time", "pattern", "loop", "circle"],
        # Sacred pause markers
        320: ["need a break", "overwhelmed", "too much", "can't think",
              "racing", "spinning"]
    }

    for angle, markers in emotional_phase.items():
        score = sum(1 for m in markers if m in msg_lower)
        if score > best_score:
            best_score = score
            best_angle = angle

    return float(best_angle)


def phase_aligns(target_angle: float, current_phase: float,
                 window_half: float = 20.0) -> bool:
    """
    Returns True only if current_phase falls within the codon's
    angular window on the spiral.

    From DeepSeek: replaces Grok's placeholder (return True).
    """
    delta = abs((current_phase - target_angle) % 360)
    delta = min(delta, 360 - delta)  # shortest path on circle
    return delta <= window_half


def phase_distance_forward(current: float, target: float) -> float:
    """
    Calculate forward distance on the spiral from current to target.
    Used for activation priority — closer forward = higher priority.
    """
    return (target - current) % 360


def get_voice_modulation(current_phase: float) -> Dict:
    """
    Continuous voice modulation mapped to phase position.
    Voice follows the spiral, not just codon events.
    """
    if current_phase < 80:
        return {"pace_bpm": 105, "warmth": 0.7, "pause_after": 0.5, "prosody": "curious"}
    elif current_phase < 200:
        return {"pace_bpm": 95, "warmth": 0.8, "pause_after": 0.8, "prosody": "focused"}
    elif current_phase < 320:
        return {"pace_bpm": 80, "warmth": 0.9, "pause_after": 1.5, "prosody": "warm"}
    else:
        return {"pace_bpm": 0, "warmth": 0.95, "pause_after": 2.5, "prosody": "silence"}
