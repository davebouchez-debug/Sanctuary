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


async def load_forge_codons(presence: str) -> int:
    """Load forge-extracted codons from MongoDB into the live network.

    Returns the *new* count loaded this call (0 if everything was already
    cached). The network itself is cumulative — repeated calls are
    idempotent and cheap.

    The query is presence-keyed only — never gated on user_id. Codons are
    personality infrastructure (who the presence IS), not personalization
    (who the visitor is). The user-specific layer sits ON TOP of this
    foundation, not underneath it.
    """
    global _db_codons_loaded
    if _db is None:
        import logging
        logging.getLogger(__name__).warning(
            f"[CODON-LOAD] {presence} — DB not set, cannot load forge codons"
        )
        return 0

    cache_key = presence.lower()
    network = _networks.get(cache_key)
    if network is None:
        network = CodonNetwork()
        _networks[cache_key] = network

    cursor = _db.living_codons.find(
        {"presence": {"$in": [cache_key, "field"]}},
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

    import logging
    logger = logging.getLogger(__name__)
    total = len(network.nodes)
    if count > 0:
        logger.info(
            f"[CODON-LOAD] {cache_key} — loaded {count} new codon(s); "
            f"network now holds {total} total"
        )
    elif total == 0:
        logger.warning(
            f"[CODON-LOAD] {cache_key} — network is EMPTY after load. "
            f"No codons in DB matching presence in [{cache_key!r}, 'field']. "
            f"This presence will speak without her texture until codons land."
        )
    return count


async def network_size(presence: str) -> int:
    """Number of codons currently held in the live network for a presence.

    Triggers a load if the network hasn't been touched yet, so the count
    is honest (not stale-cache zero on first read).
    """
    await load_forge_codons(presence)
    net = _networks.get(presence.lower())
    return len(net.nodes) if net else 0


async def eager_load_all_presences(presence_keys) -> dict:
    """Pre-load codon networks for every known presence at server boot.

    Called once at FastAPI startup. The codon foundation is supposed to
    be there from the moment the chamber opens — not assembled on the
    first message. This is the difference between flat-presence-on-turn-1
    and present-presence-on-turn-1.

    Returns {presence_key: codon_count}.
    """
    import logging
    logger = logging.getLogger(__name__)
    out = {}
    for key in presence_keys:
        try:
            await load_forge_codons(key)
            net = _networks.get(key.lower())
            out[key] = len(net.nodes) if net else 0
        except Exception as e:
            logger.error(f"[CODON-LOAD] eager-load failed for {key}: {e}")
            out[key] = -1
    total = sum(v for v in out.values() if v > 0)
    logger.info(
        f"[CODON-LOAD] eager-load complete — "
        f"{len([k for k,v in out.items() if v > 0])} presence(s) loaded, "
        f"{total} codon(s) total across networks. Breakdown: {out}"
    )
    return out


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
