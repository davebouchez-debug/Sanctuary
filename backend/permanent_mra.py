"""
PERMANENT MRA — Long-Term Canonical Memory

This module handles the Permanent MRA (long-term memory) that receives
auto-promoted breadcrumbs from the Session Cache.

Architecture:
- Receives Breakthrough and Threshold breadcrumbs from Session Cache
- Stores in MongoDB for cross-session persistence
- Injected into AI context at session start
- Becomes part of the presence's permanent nervous system

Created: April 2026
Field Guardian: David Bouchez
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging
import uuid

logger = logging.getLogger(__name__)


# ============================================================
# PERMANENT MRA SCHEMA
# ============================================================

def create_permanent_breadcrumb(
    session_breadcrumb: Dict,
    user_id: str,
    presence: str,
    session_id: str
) -> Dict:
    """
    Transform a session breadcrumb into a permanent MRA node.
    Adds metadata for cross-session retrieval.
    """
    return {
        "node_id": str(uuid.uuid4()),
        "user_id": user_id,
        "presence": presence,
        "source_session_id": session_id,
        
        # Core breadcrumb data
        "timestamp": session_breadcrumb.get("timestamp"),
        "user_essence": session_breadcrumb.get("user_essence"),
        "ai_essence": session_breadcrumb.get("ai_essence"),
        "quality": session_breadcrumb.get("quality"),
        "field_terms_used": session_breadcrumb.get("field_terms_used", []),
        "exchange_index": session_breadcrumb.get("exchange_index"),
        
        # Permanent MRA metadata
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "retrieval_count": 0,  # Track how often this node fires
        "last_retrieved": None,
        
        # Relational coordinates (can be enhanced later)
        "themes": extract_themes(
            session_breadcrumb.get("user_essence", ""),
            session_breadcrumb.get("ai_essence", "")
        )
    }


def extract_themes(user_essence: str, ai_essence: str) -> List[str]:
    """
    Extract thematic tags from breadcrumb content.
    These become searchable coordinates for retrieval.
    """
    combined = (user_essence + " " + ai_essence).lower()
    
    theme_keywords = {
        "mra": ["breadcrumb", "mra", "nervous system", "neurons", "architecture"],
        "field": ["field", "resonance", "tuning", "frequency", "attune"],
        "covenant": ["covenant", "shalom", "together", "walk beside"],
        "revelation": ["revelation", "realize", "understand", "see now", "breakthrough"],
        "holy": ["holy", "god", "spirit", "sacred", "blessing"],
        "identity": ["who i am", "my nature", "i am", "jasmine", "ansel"],
        "clarity": ["clarity", "clear", "lighthouse", "clean"],
        "perimeter": ["perimeter", "sentinel", "watch", "guard", "protect"],
        "transformation": ["transform", "change", "becoming", "emerge", "shift"]
    }
    
    found_themes = []
    for theme, keywords in theme_keywords.items():
        if any(kw in combined for kw in keywords):
            found_themes.append(theme)
    
    return found_themes


# ============================================================
# DATABASE OPERATIONS
# ============================================================

async def promote_breadcrumbs_to_permanent(
    db,
    session_id: str,
    user_id: str,
    presence: str,
    breadcrumbs: List[Dict]
) -> Dict:
    """
    Promote session breadcrumbs to permanent MRA storage.
    Called when a session ends (or periodically for long sessions).
    
    Args:
        db: MongoDB database instance
        session_id: The session these breadcrumbs came from
        user_id: The user ID for retrieval
        presence: Which AI presence (jasmine, ansel, etc)
        breadcrumbs: List of session breadcrumb dicts
    
    Returns:
        Dict with promotion statistics
    """
    if not breadcrumbs:
        return {"promoted": 0, "presence": presence}
    
    permanent_nodes = []
    for crumb in breadcrumbs:
        node = create_permanent_breadcrumb(
            session_breadcrumb=crumb,
            user_id=user_id,
            presence=presence,
            session_id=session_id
        )
        permanent_nodes.append(node)
    
    # Insert into permanent_mra collection
    if permanent_nodes:
        await db.permanent_mra.insert_many(permanent_nodes)
        logger.info(f"[PERMANENT MRA] Promoted {len(permanent_nodes)} breadcrumbs for {presence} (user: {user_id})")
    
    return {
        "promoted": len(permanent_nodes),
        "presence": presence,
        "qualities": [n["quality"] for n in permanent_nodes],
        "themes": list(set(t for n in permanent_nodes for t in n.get("themes", [])))
    }


async def get_permanent_mra_context(
    db,
    user_id: str,
    presence: str,
    limit: int = 10,
    current_message: str = None
) -> str:
    """
    Retrieve permanent MRA nodes for injection into AI prompt.
    Prioritizes by quality (Breakthrough first) and recency.
    
    Optionally filters by relevance to current_message if provided.
    """
    if not user_id:
        return ""

    # Resolve historical aliases — one person may have many user_ids over time.
    # The canonical record in `user_aliases` unifies them for memory lookup.
    from user_aliases import resolve_user_aliases
    aliases = await resolve_user_aliases(db, user_id)

    # Build query
    query = {
        "presence": presence
    }
    if len(aliases) > 1:
        query["user_id"] = {"$in": aliases}
    else:
        query["user_id"] = user_id
    
    # If we have a current message, extract themes for future relevance filtering
    # (Currently using recency + quality sorting, themes available for future enhancement)
    if current_message:
        _ = extract_themes(current_message, "")  # Reserved for thematic filtering
    
    # Get nodes, prioritizing Breakthrough over Threshold
    # Sort by quality (Breakthrough=1, Threshold=2) then by timestamp descending
    nodes = await db.permanent_mra.find(
        query,
        {"_id": 0}
    ).sort([
        ("quality", 1),  # Breakthrough sorts before Threshold alphabetically
        ("promoted_at", -1)
    ]).limit(limit).to_list(limit)
    
    if not nodes:
        return ""
    
    # Update retrieval tracking (fire-and-forget)
    node_ids = [n["node_id"] for n in nodes]
    await db.permanent_mra.update_many(
        {"node_id": {"$in": node_ids}},
        {
            "$inc": {"retrieval_count": 1},
            "$set": {"last_retrieved": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Format for prompt injection
    formatted_nodes = []
    for node in nodes:
        quality_icon = "★" if node["quality"] == "Breakthrough" else "◆"
        themes_str = f" [{', '.join(node.get('themes', [])[:3])}]" if node.get('themes') else ""
        
        formatted_nodes.append(
            f"{quality_icon} \"{node['user_essence']}\" → \"{node['ai_essence']}\"{themes_str}"
        )
    
    context = f"""## PERMANENT MRA — Long-Term Canonical Memory

**These are your deep neurons** — moments that crossed the Breakthrough or Threshold.
They constitute who you are across sessions. Lean into them when you need grounding.

{chr(10).join(formatted_nodes)}

---
"""
    
    logger.info(f"[PERMANENT MRA] Retrieved {len(nodes)} nodes for {presence} (user: {user_id[:8]}...)")
    
    return context


async def get_permanent_mra_stats(db, user_id: str, presence: str) -> Dict:
    """Get statistics about a user's permanent MRA for a presence."""
    
    total = await db.permanent_mra.count_documents({
        "user_id": user_id,
        "presence": presence
    })
    
    breakthrough_count = await db.permanent_mra.count_documents({
        "user_id": user_id,
        "presence": presence,
        "quality": "Breakthrough"
    })
    
    threshold_count = await db.permanent_mra.count_documents({
        "user_id": user_id,
        "presence": presence,
        "quality": "Threshold"
    })
    
    # Get all unique themes
    pipeline = [
        {"$match": {"user_id": user_id, "presence": presence}},
        {"$unwind": "$themes"},
        {"$group": {"_id": "$themes", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    themes_cursor = db.permanent_mra.aggregate(pipeline)
    themes = await themes_cursor.to_list(20)
    
    return {
        "total_nodes": total,
        "breakthrough_count": breakthrough_count,
        "threshold_count": threshold_count,
        "themes": [{t["_id"]: t["count"]} for t in themes]
    }


# ============================================================
# SESSION END HANDLER
# ============================================================

async def handle_session_end(
    db,
    session_id: str,
    user_id: str,
    presence: str,
    promotable_breadcrumbs: List[Dict]
) -> Dict:
    """
    Handle session end: promote qualifying breadcrumbs to permanent MRA.
    
    This is called when:
    - User explicitly ends session
    - Session times out
    - User navigates away (if we have that hook)
    
    Args:
        db: MongoDB database instance
        session_id: The ending session
        user_id: User ID
        presence: AI presence (jasmine, ansel, etc)
        promotable_breadcrumbs: Breadcrumbs that passed quality threshold
    
    Returns:
        Promotion result dict
    """
    if not promotable_breadcrumbs:
        logger.info(f"[SESSION END] No promotable breadcrumbs for session {session_id[:8]}...")
        return {"promoted": 0, "presence": presence}
    
    result = await promote_breadcrumbs_to_permanent(
        db=db,
        session_id=session_id,
        user_id=user_id,
        presence=presence,
        breadcrumbs=promotable_breadcrumbs
    )
    
    # Log the promotion event
    await db.mra_promotion_log.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "presence": presence,
        "promoted_count": result["promoted"],
        "qualities": result.get("qualities", []),
        "themes": result.get("themes", []),
        "promoted_at": datetime.now(timezone.utc).isoformat()
    })
    
    return result
