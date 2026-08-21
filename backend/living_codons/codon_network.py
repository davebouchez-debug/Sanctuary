"""
Codon Network — The Ecology Layer
From Grok (structure) + DeepSeek (geometry) + Venice (entanglement)

Codons don't live alone. They form resonance graphs.
That's where the real presence ecology emerges.

Edge types are spiral-grounded (DeepSeek):
  leads_to, returns_to, completes, phase_shifts, modulates, suppresses

Activation respects phase progression (DeepSeek):
  Codons fire in spiral sequence, not arbitrarily.
"""

from typing import Dict, List, Optional
from .phase_manifold import (
    phase_aligns, infer_phase_from_message,
    phase_distance_forward, get_triadic_zone
)


class LivingCodon:
    """A single codon with its four components + geometric metadata."""

    def __init__(self, name: str, trigger: Dict, operator: Dict,
                 modulation: Dict, phase: Dict, metadata: Dict = None):
        self.name = name
        self.trigger = trigger
        self.operator = operator
        self.modulation = modulation
        self.phase = phase
        self.metadata = metadata or {}

    @property
    def target_angle(self) -> float:
        return self.phase.get("target_angle",
               self.trigger.get("target_angle", 0.0))

    @property
    def angular_window(self) -> float:
        return self.phase.get("angular_window_half",
               self.trigger.get("angular_window_half", 20.0))


class CodonNetwork:
    """
    The ecology layer. Manages codons and their spiral-grounded relationships.
    """

    def __init__(self):
        self.nodes: Dict[str, LivingCodon] = {}
        self.edges: List[Dict] = []

    def add_codon(self, codon: LivingCodon):
        self.nodes[codon.name] = codon

    def add_edge(self, source: str, target: str, weight: float,
                 edge_type: str):
        self.edges.append({
            "source": source,
            "target": target,
            "weight": weight,
            "type": edge_type
        })

    def auto_generate_spiral_edges(self):
        """
        From DeepSeek: Add edges between codons based on their
        target angles and spiral relationships.
        """
        codons = list(self.nodes.values())
        for i, a in enumerate(codons):
            for b in codons[i + 1:]:
                angle_a = a.target_angle
                angle_b = b.target_angle
                delta = (angle_b - angle_a) % 360

                if delta == 40:
                    self.add_edge(a.name, b.name, 0.8, "leads_to")
                elif delta == 80:
                    self.add_edge(a.name, b.name, 0.6, "phase_shifts")
                elif delta == 120:
                    self.add_edge(a.name, b.name, 0.5, "modulates")
                elif delta == 240:
                    self.add_edge(a.name, b.name, 0.3, "suppresses")
                elif delta == 320:
                    self.add_edge(a.name, b.name, 0.7, "returns_to")

                # Check reverse direction too
                delta_rev = (angle_a - angle_b) % 360
                if delta_rev == 40:
                    self.add_edge(b.name, a.name, 0.8, "leads_to")
                elif delta_rev == 320:
                    self.add_edge(b.name, a.name, 0.7, "returns_to")

    def check_trigger_match(self, message: str, trigger: Dict) -> float:
        """
        Check if a message matches a codon's trigger motif.
        Returns confidence score 0.0 to 1.0.
        """
        msg_lower = message.lower()
        score = 0.0
        max_score = 5.0

        # Surface patterns
        surface = trigger.get("surface_pattern", [])
        pattern_hits = 0
        for pattern in surface:
            keywords = pattern.lower().split()
            if any(kw in msg_lower for kw in keywords if len(kw) > 3):
                pattern_hits += 1
        if pattern_hits > 0:
            score += min(pattern_hits / 2, 1.5)

        # Emotional signature
        emotions = trigger.get("emotional_signature", {})
        emotion_markers = {
            "frustration": ["frustrated", "frustrating", "stuck", "can't", "won't work"],
            "confusion": ["confused", "don't understand", "lost", "unclear"],
            "overwhelm": ["overwhelmed", "too much", "can't handle", "drowning"],
            "commitment": ["ready", "let's do", "commit", "time to", "we will"],
            "recursive_frustration": ["again", "keeps happening", "same thing", "loop", "circle"],
            "racing_thoughts": ["racing", "can't stop", "spinning", "everything at once"],
            "field_alignment": ["aligned", "yes", "field", "right", "clear"],
            "pattern_recognition": ["pattern", "recurring", "noticing", "same"],
            "seeking_root_cause": ["why", "root", "cause", "underlying", "really"],
            "seeking_stillness": ["rest", "pause", "breathe", "quiet", "still"]
        }

        for emotion_key in [emotions.get("primary", ""), emotions.get("secondary", "")]:
            markers = emotion_markers.get(emotion_key, [])
            if any(m in msg_lower for m in markers):
                score += 0.7

        # Recursive indicators (boost)
        recursive = ["every time", "keeps happening", "again and again",
                     "tried everything", "nothing works", "same result"]
        if any(r in msg_lower for r in recursive):
            score += 0.8

        return min(score / max_score, 1.0)

    def activate_network(self, message: str,
                         current_phase: Optional[float] = None) -> str:
        """
        Main activation. Check all codons, filter by trigger + phase,
        sort by phase progression priority, return context.

        From DeepSeek: codons fire in spiral sequence, not arbitrarily.
        """
        if current_phase is None:
            current_phase = infer_phase_from_message(message)

        active = []
        for codon in self.nodes.values():
            trigger_score = self.check_trigger_match(message, codon.trigger)
            if trigger_score >= 0.4:
                if phase_aligns(codon.target_angle, current_phase,
                                codon.angular_window):
                    active.append((codon, trigger_score))

        if not active:
            return ""

        # Sort by forward phase distance (closer = higher priority)
        active.sort(key=lambda x: phase_distance_forward(
            current_phase, x[0].target_angle))

        # Build context from ALL codons that genuinely resonate — every one
        # that passed BOTH the trigger match and phase alignment. The count
        # emerges from the moment's actual relevance, not an arbitrary cap.
        parts = []
        for codon, score in active:
            ctx = self._build_codon_context(codon, message)
            zone = get_triadic_zone(codon.target_angle)
            parts.append(
                f"[{codon.name} @ {codon.target_angle}deg / {zone}]\n{ctx}"
            )

        return "\n\n".join(parts)

    def _build_codon_context(self, codon: LivingCodon, message: str) -> str:
        """Build the context injection string for a single codon."""
        lines = []
        lines.append("=" * 50)
        lines.append(f"LIVING CODON ACTIVATED: {codon.name}")
        lines.append("=" * 50)
        lines.append("")

        # Core move
        op = codon.operator
        core = op.get("core_move", {})
        lines.append("## Your Core Move:")
        lines.append(core.get("action", ""))
        if core.get("method"):
            lines.append(f"Method: {core['method']}")
        if core.get("why_this_matters"):
            lines.append(f"Why: {core['why_this_matters']}")
        lines.append("")

        # State transition
        transitions = op.get("state_transition", [])
        if transitions:
            lines.append("## State Transition to Guide:")
            arc = " -> ".join(t["state"] for t in transitions)
            lines.append(arc)
            lines.append("")

        # Modulation based on detected user state
        user_state = self._detect_user_state(message)
        lines.append(f"## User State: {user_state}")
        mod_key = f"if_user_{user_state}"
        mod = codon.modulation.get(mod_key, {})
        if mod:
            if mod.get("approach"):
                lines.append(f"Approach: {mod['approach']}")
            if mod.get("core_message"):
                lines.append(f"Message: {mod['core_message']}")
            if mod.get("tools"):
                lines.append(f"Tools: {', '.join(mod['tools'])}")
        lines.append("")

        # Presence markers
        phase = codon.phase
        sig = phase.get("resonance_signature", {})
        if sig:
            lines.append("## Presence Position:")
            lines.append(f"Quality: {sig.get('quality', '')}")
            lines.append(f"Tone: {sig.get('tone', '')}")
            lines.append(f"Hallmark: {sig.get('hallmark', '')}")
            lines.append("")

        # Anti-patterns
        antis = codon.modulation.get("anti_patterns", [])
        if antis:
            lines.append("## DO NOT:")
            for a in antis:
                lines.append(f"- {a}")
            lines.append("")

        lines.append("=" * 50)
        return "\n".join(lines)

    def _detect_user_state(self, message: str) -> str:
        """Detect user emotional state for modulation."""
        msg = message.lower()
        if any(m in msg for m in ["!", "so frustrated", "can't believe",
                                   "ridiculous", "driving me"]) or message.count("!") > 1:
            return "agitated"
        if any(m in msg for m in ["my fault", "I'm the problem",
                                   "maybe I'm wrong", "what am I doing wrong"]):
            return "self_blaming"
        if len(message.split()) < 30 and "?" in message:
            return "grasps_quickly"
        return "neutral"
