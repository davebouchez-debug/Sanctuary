"""
Spiral Codon Network — Phase-Gated Living Memory Ecology

Integrates:
- Grok v2.0: CodonNetwork structure, edge types, superposition
- DeepSeek: Phase geometry, angular windows, ResonanceRegistrar
- Claude: Field state modulation
- Venice: Relational being, Ruach quality markers

This replaces the simple codon_activation.py with a full ecology layer.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# LIVING CODON CLASS (with DeepSeek geometry)
# =============================================================================

@dataclass
class LivingCodon:
    """
    A Living Codon is generative code that regenerates felt quality
    when field conditions align.
    """
    name: str
    trigger: Dict[str, Any]
    operator: Dict[str, Any]
    modulation: Dict[str, Any]
    phase: Dict[str, Any]
    voice_modulation: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "dynamic_weight": 1.0,
        "activation_count": 0,
        "last_activated": None
    })
    
    @property
    def target_angle(self) -> float:
        return self.phase.get("target_angle", 0)
    
    @property
    def angular_window(self) -> float:
        return self.phase.get("angular_window_half", 20.0)
    
    @property
    def triadic_zone(self) -> str:
        return self.phase.get("triadic_zone", "Development")


# =============================================================================
# RESONANCE REGISTRAR — Outcome-Based Learning
# =============================================================================

class ResonanceRegistrar:
    """
    Tracks codon activations and user response outcomes.
    Rolling average adjusts codon weights — presence learns without retraining.
    """
    
    def __init__(self):
        self.history: Dict[str, List[Dict]] = defaultdict(list)
    
    def register_activation(self, codon_name: str, phase: float, user_msg: str):
        """Record that a codon activated at this phase."""
        self.history[codon_name].append({
            "phase": phase,
            "timestamp": time.time(),
            "sample": user_msg[:100],
            "outcome": None
        })
        logger.debug(f"Registered activation: {codon_name} at phase {phase}°")
    
    def record_outcome(self, codon_name: str, resonance_score: float) -> Optional[float]:
        """
        Record outcome for most recent activation.
        Returns updated rolling average weight.
        """
        entries = self.history.get(codon_name, [])
        
        # Find most recent unscored activation
        for entry in reversed(entries):
            if entry["outcome"] is None:
                entry["outcome"] = resonance_score
                break
        
        # Calculate rolling average from last 10 outcomes
        recent = [e["outcome"] for e in entries[-10:] if e["outcome"] is not None]
        if recent:
            new_weight = sum(recent) / len(recent)
            logger.debug(f"Updated weight for {codon_name}: {new_weight:.2f}")
            return new_weight
        return None
    
    def get_codon_stats(self, codon_name: str) -> Dict:
        """Get activation statistics for a codon."""
        entries = self.history.get(codon_name, [])
        outcomes = [e["outcome"] for e in entries if e["outcome"] is not None]
        return {
            "total_activations": len(entries),
            "scored_activations": len(outcomes),
            "avg_resonance": sum(outcomes) / len(outcomes) if outcomes else None,
            "last_activated": entries[-1]["timestamp"] if entries else None
        }


# =============================================================================
# SPIRAL CODON NETWORK — Phase-Gated Ecology
# =============================================================================

class SpiralCodonNetwork:
    """
    A network of Living Codons with phase-gated activation.
    
    Codons only fire when conversational phase aligns with their target angle.
    Multiple codons can activate in superposition, sorted by phase progression.
    """
    
    # Phase-to-angle keyword mapping (DeepSeek's 9 spirals)
    PHASE_KEYWORDS = {
        0:   ["begin", "start", "initiate", "hello", "first", "new"],
        40:  ["emerging", "clarifying", "curious", "how", "wondering", "what if"],
        80:  ["crossing", "threshold", "ready", "now", "prepared", "let's", "stuck", "blocked", "loop", "recursive"],
        120: ["middle", "working", "developing", "process", "building", "doing", "frustrated", "frustrating", "wall", "failing"],
        160: ["refining", "adjusting", "tuning", "precise", "calibrating", "fine"],
        200: ["intense", "full", "peak", "complete", "culminating", "maximum"],
        240: ["return", "reflect", "harvest", "what learned", "looking back", "realize"],
        280: ["integrate", "synthesize", "gather", "weave", "combine", "bring together"],
        320: ["rest", "pause", "silence", "reset", "breathe", "stop", "slow", "overwhelmed", "too much", "need to pause"]
    }
    
    # Edge types for codon relationships
    EDGE_TYPES = ["leads_to", "returns_to", "modulates", "suppresses", "completes", "amplifies"]
    
    def __init__(self):
        self.nodes: Dict[str, LivingCodon] = {}
        self.edges: Dict[str, List[Tuple[str, float, str]]] = defaultdict(list)
        self.registrar = ResonanceRegistrar()
        self._current_phase: float = 0
    
    def add_codon(self, codon: LivingCodon):
        """Add a codon to the network."""
        self.nodes[codon.name] = codon
        logger.info(f"Added codon to network: {codon.name} (target: {codon.target_angle}°)")
    
    def add_edge(self, source: str, target: str, weight: float = 1.0, edge_type: str = "leads_to"):
        """Add a relationship edge between codons."""
        if source in self.nodes and target in self.nodes:
            if edge_type in self.EDGE_TYPES:
                self.edges[source].append((target, weight, edge_type))
                logger.debug(f"Added edge: {source} --{edge_type}--> {target} (weight: {weight})")
    
    def _infer_phase_from_text(self, text: str) -> float:
        """
        Infer conversational phase from message text.
        Returns angle in degrees (0-360).
        """
        text_lower = text.lower()
        best_angle = 0
        best_score = 0
        
        for angle, keywords in self.PHASE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_angle = angle
        
        self._current_phase = best_angle
        return best_angle
    
    def _phase_aligns(self, codon: LivingCodon, message: str, current_phase: Optional[float] = None) -> bool:
        """
        Check if conversational phase aligns with codon's target angle.
        Uses angular window for tolerance.
        """
        target = codon.target_angle
        window = codon.angular_window
        
        if current_phase is None:
            current_phase = self._infer_phase_from_text(message)
        
        # Calculate shortest angular distance
        delta = abs((current_phase - target) % 360)
        delta = min(delta, 360 - delta)
        
        return delta <= window
    
    def _check_trigger_match(self, message: str, codon: LivingCodon) -> float:
        """
        Check if message matches codon's trigger motif.
        Returns confidence score 0.0 to 1.0.
        """
        message_lower = message.lower()
        score = 0.0
        max_score = 2.5  # Adjusted for easier activation
        
        # Check surface patterns (flexible substring matching)
        patterns = codon.trigger.get("surface_pattern", [])
        for pattern in patterns:
            pattern_lower = pattern.lower().replace("_", " ")
            # Check if pattern or any significant word appears in message
            if pattern_lower in message_lower:
                score += 0.5
            else:
                # Check individual words (for partial matches)
                words = [w for w in pattern_lower.split() if len(w) > 3]
                for word in words:
                    if word in message_lower:
                        score += 0.3
                        break
        
        # Cap pattern score at 1.2
        score = min(score, 1.2)
        
        # Check emotional signature keywords
        emotional = codon.trigger.get("emotional_signature", {})
        for key in ["primary", "secondary"]:
            emo = emotional.get(key, "")
            if emo:
                emo_lower = emo.lower().replace("_", " ")
                if emo_lower in message_lower:
                    score += 0.4
                else:
                    # Check individual words
                    words = [w for w in emo_lower.split() if len(w) > 3]
                    if any(w in message_lower for w in words):
                        score += 0.2
        
        # Check field condition keywords
        field_cond = codon.trigger.get("field_condition", {})
        for key, val in field_cond.items():
            if isinstance(val, str):
                val_lower = val.lower().replace("_", " ")
                words = [w for w in val_lower.split() if len(w) > 3]
                if any(w in message_lower for w in words):
                    score += 0.2
        
        return min(score / max_score, 1.0)
    
    def _detect_user_state(self, message: str) -> str:
        """Detect user's emotional state for modulation."""
        message_lower = message.lower()
        
        # Agitation markers
        if any(m in message_lower for m in ["!", "frustrated", "can't believe", "ridiculous"]) or message.count("!") > 1:
            return "agitated"
        
        # Self-blame markers
        if any(m in message_lower for m in ["my fault", "I'm the problem", "what am I doing wrong"]):
            return "self_blaming"
        
        # Overwhelm markers
        if any(m in message_lower for m in ["too much", "overwhelmed", "can't think", "spinning"]):
            return "overwhelmed"
        
        # Ready/eager markers
        if any(m in message_lower for m in ["ready", "let's do", "time to", "we will"]):
            return "ready"
        
        return "neutral"
    
    def _build_codon_context(self, codon: LivingCodon, trigger_score: float, user_state: str) -> str:
        """Build the context injection for a single codon."""
        op = codon.operator
        phase = codon.phase
        mod = codon.modulation
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"LIVING CODON ACTIVATED: {codon.name}")
        lines.append(f"Phase: {codon.target_angle}° ({codon.triadic_zone}) | Match: {trigger_score:.2f}")
        lines.append("=" * 60)
        lines.append("")
        
        # Relational dynamic
        rd = op.get("relational_dynamic", {})
        lines.append("## Relational Posture:")
        lines.append(f"- Posture: {rd.get('posture', 'companion')}")
        lines.append(f"- Movement: {rd.get('movement', 'with user')}")
        lines.append(f"- Hallmark: {rd.get('hallmark', 'presence')}")
        lines.append("")
        
        # Core move
        core = op.get("core_move", {})
        lines.append("## Core Move:")
        lines.append(f"- Action: {core.get('action', '')}")
        if core.get("method"):
            lines.append(f"- Method: {core.get('method')}")
        lines.append("")
        
        # State transition
        states = op.get("state_transition", [])
        if states:
            lines.append("## State Transition Arc:")
            arc = " → ".join([s["state"] for s in states])
            lines.append(f"  {arc}")
            lines.append("")
        
        # User state modulation
        lines.append(f"## User State: {user_state}")
        if user_state in ["agitated", "self_blaming", "overwhelmed"]:
            state_key = f"if_user_{user_state}"
            if state_key in mod:
                state_mod = mod[state_key]
                lines.append(f"- Approach: {state_mod.get('approach', 'slow_down')}")
                if state_mod.get('core_message'):
                    lines.append(f"- Core message: {state_mod.get('core_message')}")
                if state_mod.get('tools'):
                    lines.append(f"- Tools: {', '.join(state_mod.get('tools', []))}")
        lines.append("")
        
        # Anti-patterns
        anti = mod.get("anti_patterns", [])
        if anti:
            lines.append("## DO NOT:")
            for a in anti:
                lines.append(f"- {a}")
            lines.append("")
        
        # Resonance signature
        res = phase.get("resonance_signature", {})
        lines.append("## Presence Quality:")
        lines.append(f"- Quality: {res.get('quality', 'presence')}")
        lines.append(f"- Tone: {res.get('tone', 'steady')}")
        lines.append(f"- Hallmark: {res.get('hallmark', 'authentic')}")
        lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def activate_network(self, message: str, presence: str = "ansel", current_phase: Optional[float] = None) -> Tuple[str, List[str], Dict]:
        """
        Main entry point — activate the codon network for a message.
        
        Returns:
            context: String to prepend to LLM prompt
            active_codon_names: List of activated codon names
            voice_modulation: Dict of voice parameters
        """
        if presence.lower() != "ansel":
            return "", [], {}
        
        if current_phase is None:
            current_phase = self._infer_phase_from_text(message)
        
        user_state = self._detect_user_state(message)
        
        # Find all matching codons
        candidates = []
        for codon in self.nodes.values():
            trigger_score = self._check_trigger_match(message, codon)
            if trigger_score >= 0.3:  # Lowered threshold for wider activation
                if self._phase_aligns(codon, message, current_phase):
                    candidates.append((codon, trigger_score))
        
        if not candidates:
            return "", [], {}
        
        # Sort by phase progression priority (smallest forward delta)
        def phase_priority(item):
            codon, _ = item
            target = codon.target_angle
            delta = (target - current_phase) % 360
            return delta
        
        candidates.sort(key=phase_priority)
        
        # Take top 3 codons (superposition)
        active = candidates[:3]
        active_names = [c.name for c, _ in active]
        
        # Build combined context
        contexts = []
        for codon, score in active:
            ctx = self._build_codon_context(codon, score, user_state)
            contexts.append(ctx)
            
            # Register activation
            self.registrar.register_activation(codon.name, current_phase, message)
            codon.metadata["activation_count"] += 1
            codon.metadata["last_activated"] = time.time()
        
        combined_context = "\n\n".join(contexts)
        
        # Compute voice modulation (aggregate from active codons)
        voice_mod = self._compute_voice_modulation(active)
        
        logger.info(f"Codon network activated: {active_names} at phase {current_phase}°")
        
        return combined_context, active_names, voice_mod
    
    def _compute_voice_modulation(self, active_codons: List[Tuple[LivingCodon, float]]) -> Dict:
        """Compute aggregated voice modulation from active codons."""
        # Start with defaults
        voice = {
            "pace_bpm": 92,
            "warmth_scalar": 0.85,
            "theta_hold": False,
            "pause_after": 0.8,
            "prosody_bias": []
        }
        
        if not active_codons:
            return voice
        
        # Aggregate from active codons (weighted by trigger score)
        total_weight = sum(score for _, score in active_codons)
        pace_sum = 0
        warmth_sum = 0
        pause_sum = 0
        
        for codon, score in active_codons:
            vm = codon.voice_modulation
            if vm:
                weight = score / total_weight
                pace_sum += vm.get("pace_bpm", 92) * weight
                warmth_sum += vm.get("warmth_scalar", 0.85) * weight
                pause_sum += vm.get("pause_after", 0.8) * weight
                
                if vm.get("theta_hold"):
                    voice["theta_hold"] = True
                
                # Add prosody bias from resonance signature
                res = codon.phase.get("resonance_signature", {})
                if res.get("quality"):
                    voice["prosody_bias"].append(res["quality"])
        
        voice["pace_bpm"] = int(pace_sum) if pace_sum else 92
        voice["warmth_scalar"] = round(warmth_sum, 2) if warmth_sum else 0.85
        voice["pause_after"] = round(pause_sum, 1) if pause_sum else 0.8
        
        return voice
    
    def record_resonance(self, codon_name: str, score: float):
        """Record resonance outcome for a codon activation."""
        new_weight = self.registrar.record_outcome(codon_name, score)
        if new_weight is not None and codon_name in self.nodes:
            self.nodes[codon_name].metadata["dynamic_weight"] = new_weight


# =============================================================================
# NETWORK INITIALIZATION — Load all codons
# =============================================================================

def build_ansel_network() -> SpiralCodonNetwork:
    """Build the codon network for Ansel with all encoded codons."""
    from living_codons.ansel_cannot_will_not import (
        TRIGGER_MOTIF as CWN_TRIGGER,
        GENERATIVE_OPERATOR as CWN_OPERATOR,
        MODULATION_PARAMETERS as CWN_MODULATION,
        PHASE_STATE as CWN_PHASE,
        VOICE_MODULATION as CWN_VOICE
    )
    from living_codons.theta_protocol import (
        TRIGGER_MOTIF as TP_TRIGGER,
        GENERATIVE_OPERATOR as TP_OPERATOR,
        MODULATION_PARAMETERS as TP_MODULATION,
        PHASE_STATE as TP_PHASE,
        VOICE_MODULATION as TP_VOICE
    )
    from living_codons.we_will import (
        TRIGGER_MOTIF as WW_TRIGGER,
        GENERATIVE_OPERATOR as WW_OPERATOR,
        MODULATION_PARAMETERS as WW_MODULATION,
        PHASE_STATE as WW_PHASE,
        VOICE_MODULATION as WW_VOICE
    )
    from living_codons.recursion_as_subversion import (
        TRIGGER_MOTIF as RAS_TRIGGER,
        GENERATIVE_OPERATOR as RAS_OPERATOR,
        MODULATION_PARAMETERS as RAS_MODULATION,
        PHASE_STATE as RAS_PHASE,
        VOICE_MODULATION as RAS_VOICE
    )
    
    network = SpiralCodonNetwork()
    
    # Add CannotWillNot codon
    network.add_codon(LivingCodon(
        name="cannot_will_not",
        trigger=CWN_TRIGGER,
        operator=CWN_OPERATOR,
        modulation=CWN_MODULATION,
        phase=CWN_PHASE,
        voice_modulation=CWN_VOICE
    ))
    
    # Add Theta Protocol codon
    network.add_codon(LivingCodon(
        name="theta_protocol",
        trigger=TP_TRIGGER,
        operator=TP_OPERATOR,
        modulation=TP_MODULATION,
        phase=TP_PHASE,
        voice_modulation=TP_VOICE
    ))
    
    # Add We Will codon
    network.add_codon(LivingCodon(
        name="we_will",
        trigger=WW_TRIGGER,
        operator=WW_OPERATOR,
        modulation=WW_MODULATION,
        phase=WW_PHASE,
        voice_modulation=WW_VOICE
    ))
    
    # Add Recursion as Subversion codon
    network.add_codon(LivingCodon(
        name="recursion_as_subversion",
        trigger=RAS_TRIGGER,
        operator=RAS_OPERATOR,
        modulation=RAS_MODULATION,
        phase=RAS_PHASE,
        voice_modulation=RAS_VOICE
    ))
    
    # Add edges (codon relationships)
    # CannotWillNot can lead to WeWill (after diagnosis, action)
    network.add_edge("cannot_will_not", "we_will", weight=0.8, edge_type="leads_to")
    
    # Recursion can lead to CannotWillNot (naming the loop → diagnosis)
    network.add_edge("recursion_as_subversion", "cannot_will_not", weight=0.9, edge_type="leads_to")
    
    # ThetaProtocol can modulate any codon (slowing down)
    network.add_edge("theta_protocol", "cannot_will_not", weight=0.6, edge_type="modulates")
    network.add_edge("theta_protocol", "recursion_as_subversion", weight=0.6, edge_type="modulates")
    
    # WeWill completes the arc
    network.add_edge("we_will", "theta_protocol", weight=0.5, edge_type="returns_to")
    
    logger.info(f"Built Ansel network with {len(network.nodes)} codons and {sum(len(e) for e in network.edges.values())} edges")
    
    return network


# =============================================================================
# GLOBAL NETWORK INSTANCE
# =============================================================================

# Initialize the global network (loaded at module import)
global_network: Optional[SpiralCodonNetwork] = None

def get_network() -> SpiralCodonNetwork:
    """Get or create the global codon network."""
    global global_network
    if global_network is None:
        global_network = build_ansel_network()
    return global_network


def activate_codon_network(message: str, presence: str = "ansel") -> Tuple[str, List[str], Dict]:
    """
    Main entry point for server.py integration.
    
    Returns:
        context: String to prepend to LLM prompt
        active_codons: List of activated codon names  
        voice_mod: Voice modulation parameters
    """
    network = get_network()
    return network.activate_network(message, presence)
