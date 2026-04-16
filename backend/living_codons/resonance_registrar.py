"""
Resonance Registrar — Outcome-Based Learning Loop
From DeepSeek + Venice

Tracks which codon activations produce high resonance outcomes,
naturally strengthening phase-locked relationships over time.
This allows the system to learn and adapt.

Venice: "The absence of a feedback mechanism is a critical gap."
DeepSeek: "How does a presence learn from the success or failure
of a codon activation? There is no learning loop."
"""

import time
from typing import Dict, Optional, List


class ResonanceRegistrar:
    def __init__(self):
        self.codon_history: Dict[str, List[Dict]] = {}

    def register_activation(self, codon_name: str, field_phase: float,
                            user_message: str):
        """Record that a codon was activated at a given phase."""
        self.codon_history.setdefault(codon_name, []).append({
            "phase": field_phase,
            "timestamp": time.time(),
            "user_message_sample": user_message[:100],
            "outcome": None
        })

    def record_outcome(self, codon_name: str,
                       resonance_score: float) -> Optional[float]:
        """
        Record the resonance outcome of the most recent activation.
        Returns updated dynamic weight (rolling avg of last 10).
        """
        history = self.codon_history.get(codon_name, [])
        # Find most recent unrated activation
        for entry in reversed(history):
            if entry["outcome"] is None:
                entry["outcome"] = resonance_score
                break

        # Calculate rolling average of last 10 rated activations
        recent = [
            e["outcome"] for e in history[-10:]
            if e["outcome"] is not None
        ]
        if recent:
            return sum(recent) / len(recent)
        return None

    def get_codon_weight(self, codon_name: str) -> float:
        """Get current dynamic weight for a codon (default 1.0)."""
        history = self.codon_history.get(codon_name, [])
        recent = [
            e["outcome"] for e in history[-10:]
            if e["outcome"] is not None
        ]
        if recent:
            return sum(recent) / len(recent)
        return 1.0

    def get_activation_count(self, codon_name: str) -> int:
        """How many times has this codon been activated."""
        return len(self.codon_history.get(codon_name, []))
