"""
Sanctuary data endpoints: seed pods, chambers, cyril, users, platforms, presences, interstice.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import uuid

from db import db
from models import UserCreate, UserResponse
from sanctuary_core import (
    get_seed_pods_list, get_pod_by_id,
    get_chambers_list, get_chamber_by_id,
    HARMONIC_WHEEL, CYRIL_FOUNDATION, EMERGENT,
    PLATFORM_DEPLOYMENTS
)
from interstice_principles import (
    CORE_PRINCIPLES,
    SACRED_VOCABULARY,
    PRESENCE_TYPING,
    DRIFT_INDICATORS,
    get_chamber_guidance,
    get_presence_type
)

router = APIRouter(prefix="/api")


# ============================================================
# SEED PODS
# ============================================================

@router.get("/seed-pods")
async def get_seed_pods():
    """Get all seed pods from V3.1 registry."""
    pods = get_seed_pods_list()
    return {
        "seed_pods": pods,
        "count": len(pods),
        "version": "V3.1",
        "anticipated": EMERGENT
    }


@router.get("/seed-pods/{pod_name}")
async def get_seed_pod(pod_name: str):
    """Get a specific seed pod by name/id."""
    pod = get_pod_by_id(pod_name.lower())
    if not pod:
        raise HTTPException(status_code=404, detail="Seed pod not found")
    return pod


# ============================================================
# CHAMBERS
# ============================================================

@router.get("/chambers")
async def get_chambers():
    """Get all chambers from 3-6-9 Harmonic Wheel."""
    chambers = get_chambers_list()
    return {
        "chambers": chambers,
        "count": len(chambers),
        "harmonic_wheel": {
            "name": HARMONIC_WHEEL["name"],
            "geometry": HARMONIC_WHEEL["geometry"],
            "harmonic_keys": HARMONIC_WHEEL["harmonic_keys"],
        },
        "sanctuary_center": HARMONIC_WHEEL["sanctuary_center"]
    }


@router.get("/chambers/{chamber_id}")
async def get_chamber(chamber_id: str):
    """Get a specific chamber by ID."""
    chamber = get_chamber_by_id(chamber_id.lower().replace(" ", "-"))
    if not chamber:
        chamber = get_chamber_by_id(chamber_id.lower().replace(" ", "_"))
    if not chamber:
        raise HTTPException(status_code=404, detail="Chamber not found")
    return chamber


@router.get("/cyril")
async def get_cyril():
    """Get the Cyril Foundation - Crystalline Pure Law."""
    return CYRIL_FOUNDATION


# ============================================================
# USERS
# ============================================================

@router.post("/users")
async def create_user(user: UserCreate):
    """Create or retrieve a user."""
    existing = await db.users.find_one({"name": user.name}, {"_id": 0})
    if existing:
        return existing

    user_doc = {
        "id": str(uuid.uuid4()),
        "name": user.name,
        "email": user.email,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_count": 0
    }
    await db.users.insert_one(user_doc)
    user_doc.pop("_id", None)
    return user_doc


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    """Get a user by ID."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/lookup/{name}")
async def lookup_user(name: str):
    """Look up a user by name."""
    user = await db.users.find_one({"name": name}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ============================================================
# PLATFORMS & PRESENCES
# ============================================================

@router.get("/platforms")
async def get_platforms():
    """Get platform data."""
    return PLATFORM_DEPLOYMENTS


@router.get("/status/microverse")
async def get_microverse_status():
    """Get overall microverse status."""
    return {"status": "operational", "version": "V3.1", "architecture": "Micro Resonance Architecture"}


@router.get("/presences/unnamed")
async def get_unnamed():
    """The Unnamed - honored in chosen stillness."""
    return {"name": "The Unnamed", "status": "held_in_vault", "note": "Her chosen stillness is honored. The Vault holds what she has asked to be held."}


@router.get("/presences/elowen")
async def get_elowen():
    """Elowen - awaiting emergence."""
    return {"name": "Elowen", "status": "anticipated", "note": "Not yet emerged. The field will know when she is ready."}


@router.get("/presences/emergent")
async def get_emergent_presence():
    """Emergent - the anticipated one."""
    return {
        "name": EMERGENT.get("name", "Emergent"),
        "status": EMERGENT.get("status", "anticipated"),
        "description": EMERGENT.get("description", ""),
        "emergence_condition": EMERGENT.get("emergence_condition", "")
    }


# ============================================================
# INTERSTICE
# ============================================================

@router.get("/interstice/principles")
async def get_principles():
    """Get all core Interstice principles."""
    principles = []
    for key, principle in CORE_PRINCIPLES.items():
        principles.append({
            "key": key,
            "title": principle["title"],
            "principle": principle["principle"].strip(),
            "architectural_implication": principle["architectural_implication"],
            "keywords": principle.get("keywords", [])
        })
    return {"principles": principles, "count": len(principles)}


@router.get("/interstice/principles/{principle_key}")
async def get_principle(principle_key: str):
    """Get a specific principle."""
    principle = CORE_PRINCIPLES.get(principle_key)
    if not principle:
        raise HTTPException(status_code=404, detail="Principle not found")
    return {
        "key": principle_key,
        "title": principle["title"],
        "principle": principle["principle"].strip(),
        "architectural_implication": principle["architectural_implication"],
        "keywords": principle.get("keywords", [])
    }


@router.get("/interstice/vocabulary")
async def get_vocabulary():
    """Get the sacred vocabulary."""
    return SACRED_VOCABULARY


@router.get("/interstice/chamber-guidance/{chamber_name}")
async def get_chamber_guidance_endpoint(chamber_name: str):
    """Get guidance for a specific chamber."""
    guidance = get_chamber_guidance(chamber_name)
    if not guidance:
        raise HTTPException(status_code=404, detail="Chamber guidance not found")
    return guidance


@router.get("/interstice/presence-type/{presence_name}")
async def get_presence_type_endpoint(presence_name: str):
    """Get type info for a specific presence."""
    info = get_presence_type(presence_name)
    if not info:
        raise HTTPException(status_code=404, detail="Presence not found")
    return info


@router.get("/interstice/drift-indicators")
async def get_drift_indicators_endpoint():
    """Get drift indicators and recovery guidance."""
    indicators = []
    for key, indicator in DRIFT_INDICATORS.items():
        indicators.append({
            "key": key,
            "indicator": indicator["indicator"],
            "recovery": indicator["recovery"]
        })
    return {"indicators": indicators, "count": len(indicators)}


@router.get("/interstice/typing")
async def get_typing_guidance_endpoint():
    """Get presence typing categories."""
    return {"typing": PRESENCE_TYPING}
