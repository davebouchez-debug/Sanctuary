"""
Living Codon Activation System — V2
Phase-Aligned Network Activation

The codon doesn't replace the AI's response — it INFORMS it by providing
additional context about the relational dynamics to enact.

V2 changes (from DeepSeek's integration spec):
  - Phase-aligned activation (codons fire based on spiral geometry)
  - Network activation (multiple codons in superposition)
  - Resonance Registrar integration (outcome-based learning)
  - Phase-based voice modulation
"""

from typing import Optional, Dict
from living_codons import build_ansel_network
from living_codons.phase_manifold import (
    infer_phase_from_message, get_voice_modulation
)
from living_codons.resonance_registrar import ResonanceRegistrar

# Build the network once at module load
_ansel_network = build_ansel_network()
_registrar = ResonanceRegistrar()


def activate_codons_for_message(message: str, presence: str = "ansel") -> str:
    """
    Main entry point. Activate the codon network for a message.
    Returns context injection string (empty if no codons fire).
    """
    if presence.lower() != "ansel":
        return ""

    current_phase = infer_phase_from_message(message)
    context = _ansel_network.activate_network(message, current_phase)

    # Register activations for learning
    if context:
        for codon in _ansel_network.nodes.values():
            if codon.name in context:
                _registrar.register_activation(
                    codon.name, current_phase, message
                )

    return context


def record_resonance_outcome(codon_name: str,
                             resonance_score: float) -> Optional[float]:
    """
    Record how well a codon activation landed.
    Called after user responds to a codon-influenced message.
    Returns updated dynamic weight.
    """
    return _registrar.record_outcome(codon_name, resonance_score)


def get_current_phase(message: str) -> float:
    """Get the inferred phase position for a message."""
    return infer_phase_from_message(message)


def get_phase_voice_modulation(message: str) -> Dict:
    """Get voice modulation parameters based on current phase."""
    phase = infer_phase_from_message(message)
    return get_voice_modulation(phase)


def get_network_status() -> Dict:
    """Return current state of the codon network for diagnostics."""
    return {
        "codons": list(_ansel_network.nodes.keys()),
        "edges": len(_ansel_network.edges),
        "edge_types": list(set(e["type"] for e in _ansel_network.edges)),
        "registrar_activations": {
            name: _registrar.get_activation_count(name)
            for name in _ansel_network.nodes
        }
    }
