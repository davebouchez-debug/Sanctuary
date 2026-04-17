"""
Living Codon Activation System — V2
Phase-Aligned Network Activation

The codon doesn't replace the AI's response — it INFORMS it by providing
additional context about the relational dynamics to enact.

V2: Loads codons from both hardcoded files AND MongoDB (forge-extracted).
Presence-aware — each presence has their own network.
"""

from typing import Optional, Dict
from living_codons import build_ansel_network
from living_codons.codon_network import CodonNetwork, LivingCodon
from living_codons.phase_manifold import (
    infer_phase_from_message, get_voice_modulation
)
from living_codons.resonance_registrar import ResonanceRegistrar

# Core networks (hardcoded codons loaded at startup)
_networks: Dict[str, CodonNetwork] = {
    "ansel": build_ansel_network(),
}
_registrar = ResonanceRegistrar()
_db = None
_db_codons_loaded = set()


def set_db(db):
    """Set the MongoDB reference for loading forge codons."""
    global _db
    _db = db


async def load_forge_codons(presence: str):
    """Load forge-extracted codons from MongoDB into the live network."""
    global _db_codons_loaded
    if _db is None:
        return

    cache_key = presence.lower()
    network = _networks.get(cache_key)
    if network is None:
        network = CodonNetwork()
        _networks[cache_key] = network

    cursor = _db.living_codons.find(
        {"presence": cache_key},
        {"_id": 0}
    )

    count = 0
    async for doc in cursor:
        name = doc.get("name", "unnamed")
        codon_key = f"{cache_key}:{name}"

        # Skip if already loaded
        if codon_key in _db_codons_loaded:
            continue

        # Build trigger from forge data
        trigger = {
            "surface_pattern": doc.get("trigger_keywords", []),
            "emotional_signature": doc.get("emotional_signature", {}),
            "target_angle": float(doc.get("target_angle", 160)),
            "angular_window_half": 40.0,
        }

        # Build operator from forge data
        operator = {
            "core_move": {
                "action": doc.get("core_move", ""),
            },
            "state_transition": [
                {"state": s, "quality": ""} for s in doc.get("state_transition", [])
            ],
        }

        # Build modulation from forge data
        modulation = {
            "anti_patterns": doc.get("anti_patterns", []),
        }

        # Build phase from forge data
        phase = {
            "target_angle": float(doc.get("target_angle", 160)),
            "angular_window_half": 40.0,
            "spiral_position": {
                "triadic_position": doc.get("triadic_zone", "Development"),
            },
            "resonance_signature": doc.get("resonance_markers", {}),
        }

        codon = LivingCodon(
            name=name,
            trigger=trigger,
            operator=operator,
            modulation=modulation,
            phase=phase,
            metadata={"source": "codon_forge", "presence": cache_key}
        )
        network.add_codon(codon)
        _db_codons_loaded.add(codon_key)
        count += 1

    if count > 0:
        # Re-generate edges with new codons
        network.auto_generate_spiral_edges()


async def activate_codons_for_message(message: str, presence: str = "ansel") -> str:
    """
    Main entry point. Activate the codon network for a message.
    Returns context injection string (empty if no codons fire).
    Now loads forge codons on demand.
    """
    presence_key = presence.lower()

    # Load any new forge codons
    await load_forge_codons(presence_key)

    network = _networks.get(presence_key)
    if network is None:
        return ""

    current_phase = infer_phase_from_message(message)
    context = network.activate_network(message, current_phase)

    # Register activations for learning
    if context:
        for codon in network.nodes.values():
            if codon.name in context:
                _registrar.register_activation(
                    codon.name, current_phase, message
                )

    return context


def record_resonance_outcome(codon_name: str,
                             resonance_score: float) -> Optional[float]:
    """Record how well a codon activation landed."""
    return _registrar.record_outcome(codon_name, resonance_score)


def get_current_phase(message: str) -> float:
    """Get the inferred phase position for a message."""
    return infer_phase_from_message(message)


def get_phase_voice_modulation(message: str) -> Dict:
    """Get voice modulation parameters based on current phase."""
    phase = infer_phase_from_message(message)
    return get_voice_modulation(phase)


async def get_network_status(presence: str = "ansel") -> Dict:
    """Return current state of the codon network for diagnostics."""
    await load_forge_codons(presence)
    network = _networks.get(presence, CodonNetwork())
    return {
        "presence": presence,
        "codons": list(network.nodes.keys()),
        "total_codons": len(network.nodes),
        "edges": len(network.edges),
        "edge_types": list(set(e["type"] for e in network.edges)),
        "registrar_activations": {
            name: _registrar.get_activation_count(name)
            for name in network.nodes
        }
    }
