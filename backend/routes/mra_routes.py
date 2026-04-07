"""
MRA, Training Arc, Canonical Moments, Field Profile, and Belief Graph endpoints.
"""
from fastapi import APIRouter, HTTPException

from db import db
from session_cache_mra import get_session_cache_stats
from permanent_mra import (
    get_permanent_mra_stats,
    get_canonical_moments,
    get_canonical_moment_by_id,
    get_user_field_profile
)
from training_arc import (
    get_training_state,
    set_training_phase
)
from belief_graph import (
    get_belief_graph,
    get_belief_node,
    traverse_belief,
    create_belief_edge,
    mark_belief_examined,
    deactivate_belief,
    BeliefType,
    SOM_PATTERNS
)

router = APIRouter(prefix="/api")


# ============================================================
# MRA STATS
# ============================================================

@router.get("/mra/stats/{presence}/{user_id}")
async def get_mra_statistics(presence: str, user_id: str):
    """Get MRA statistics for a user and presence."""
    valid_presences = ["jasmine", "ansel", "claude"]
    if presence not in valid_presences:
        raise HTTPException(status_code=400, detail=f"Invalid presence. Use one of: {', '.join(valid_presences)}")

    stats = await get_permanent_mra_stats(db, user_id, presence)

    return {
        "presence": presence,
        "user_id": user_id,
        "permanent_mra": stats
    }


@router.get("/mra/session-cache/{session_id}")
async def get_session_cache_info(session_id: str):
    """Get current session cache statistics."""
    stats = get_session_cache_stats(session_id)

    return {
        "session_id": session_id,
        "session_cache": stats
    }


# ============================================================
# TRAINING ARC
# ============================================================

@router.get("/training-arc/{presence}/{user_id}")
async def get_training_arc_state(presence: str, user_id: str):
    """Get the current Training Arc state for a presence/user pair."""
    state = await get_training_state(db, presence, user_id)
    return state


@router.put("/training-arc/{presence}/{user_id}")
async def update_training_arc_phase(presence: str, user_id: str, phase: int):
    """Manually set the training phase. Phase 1 = Full Scaffolding, 2 = Abbreviated Beacons, 3 = Field-Reliant."""
    if phase not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Phase must be 1, 2, or 3")

    state = await set_training_phase(db, presence, user_id, phase, manual=True)
    return state


@router.get("/training-arc/attunement-log/{presence}/{user_id}")
async def get_attunement_log(presence: str, user_id: str, limit: int = 20):
    """Get the attunement log — individual moments where the AI showed field-attunement."""
    events = await db.attunement_log.find(
        {"presence": presence, "user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)

    state = await get_training_state(db, presence, user_id)

    return {
        "presence": presence,
        "user_id": user_id,
        "current_phase": state.get("phase", 1),
        "attunement_score": state.get("attunement_score", 0.0),
        "total_exchanges": state.get("total_exchanges", 0),
        "events": events
    }


# ============================================================
# CANONICAL MOMENT EXPLORER
# ============================================================

@router.get("/mra/canonical-moments/{presence}/{user_id}")
async def explore_canonical_moments(presence: str, user_id: str, limit: int = 20):
    """Surface all Breakthrough and Threshold moments for live exploration."""
    moments = await get_canonical_moments(db, user_id, presence, limit)

    return {
        "presence": presence,
        "user_id": user_id,
        "moments": moments,
        "total": len(moments)
    }


@router.get("/mra/canonical-moment/{node_id}")
async def get_canonical_moment(node_id: str):
    """Get a single canonical moment by its node_id."""
    moment = await get_canonical_moment_by_id(db, node_id)
    if not moment:
        raise HTTPException(status_code=404, detail="Canonical moment not found")
    return moment


# ============================================================
# FIELD PROFILE — Threshold Sight
# ============================================================

@router.get("/mra/field-profile/{presence}/{user_id}")
async def get_field_profile(presence: str, user_id: str):
    """Get a user's complete field profile for a presence."""
    profile = await get_user_field_profile(db, user_id, presence)
    training_state = await get_training_state(db, presence, user_id)

    return {
        "presence": presence,
        "user_id": user_id,
        "field_profile": profile,
        "training_arc": {
            "phase": training_state.get("phase", 1),
            "phase_label": training_state.get("phase_label", "Full Scaffolding"),
            "attunement_score": training_state.get("attunement_score", 0.0)
        }
    }


# ============================================================
# BELIEF GRAPH
# ============================================================

@router.get("/beliefs/som-patterns")
async def get_som_patterns():
    """Get all 14 Sleight of Mouth patterns with descriptions."""
    return {
        "patterns": {
            key: {
                "name": p["name"],
                "description": p["description"],
                "reframe_question": p["reframe_question"]
            }
            for key, p in SOM_PATTERNS.items()
        },
        "total": len(SOM_PATTERNS)
    }


@router.get("/beliefs/node/{belief_id}")
async def get_single_belief(belief_id: str):
    """Get a single belief node by its ID."""
    node = await get_belief_node(db, belief_id)
    if not node:
        raise HTTPException(status_code=404, detail="Belief not found")
    return node


@router.get("/beliefs/traverse/{belief_id}")
async def traverse_from_belief(belief_id: str, depth: int = 2):
    """Traverse the belief graph from a starting node."""
    if depth > 5:
        depth = 5
    result = await traverse_belief(db, belief_id, depth)
    return result


@router.get("/beliefs/graph/{presence}/{user_id}")
async def get_beliefs(presence: str, user_id: str):
    """Get the full belief graph for a presence/user pair."""
    graph = await get_belief_graph(db, presence, user_id)
    return graph


@router.post("/beliefs/create-edge")
async def create_new_edge(
    presence: str,
    from_belief_id: str,
    to_belief_id: str,
    edge_type: str,
    som_pattern: str = None
):
    """Manually create an edge between two beliefs."""
    if edge_type not in [BeliefType.CAUSAL, BeliefType.EQUIVALENCE]:
        raise HTTPException(status_code=400, detail="edge_type must be CAUSAL or EQUIVALENCE")

    edge = await create_belief_edge(
        db=db,
        presence=presence,
        from_belief_id=from_belief_id,
        to_belief_id=to_belief_id,
        edge_type=edge_type,
        som_pattern=som_pattern
    )
    return edge


@router.post("/beliefs/examine/{belief_id}")
async def examine_belief(belief_id: str):
    """Mark a belief as examined (introspection event)."""
    node = await get_belief_node(db, belief_id)
    if not node:
        raise HTTPException(status_code=404, detail="Belief not found")

    await mark_belief_examined(db, belief_id)

    traversal = await traverse_belief(db, belief_id, depth=1)
    return {
        "examined": belief_id,
        "belief": node,
        "connections": traversal
    }


@router.post("/beliefs/deactivate/{belief_id}")
async def deactivate_belief_endpoint(belief_id: str, reframed_into: str = None):
    """Deactivate a belief (superseded by reframe)."""
    node = await get_belief_node(db, belief_id)
    if not node:
        raise HTTPException(status_code=404, detail="Belief not found")

    await deactivate_belief(db, belief_id, reframed_into)
    return {"deactivated": belief_id, "reframed_into": reframed_into}
