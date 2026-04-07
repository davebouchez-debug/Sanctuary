"""
BELIEF GRAPH — Neuronal Cognitive Architecture

Implements a belief graph system based on NLP Sleight of Mouth patterns.
Beliefs are held in two atomic types:
    - CAUSAL: A leads to B (cause and effect)
    - EQUIVALENCE: A is B (complex equivalence)

These beliefs are connected by edges, forming the AI's cognitive web.
The 14 Sleight of Mouth patterns are the operations that forge new edges
and reframe existing beliefs.

The graph integrates with the MRA nervous system:
    - MRA breadcrumbs can spawn beliefs (auto-detected)
    - The AI can introspect on its own belief graph
    - The Sleight of Mouth patterns are active tools for reframing

Created: April 2026
Field Guardian: David Bouchez
NLP Foundation: Robert Dilts' Sleight of Mouth
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import uuid
import re
import logging

logger = logging.getLogger(__name__)


# ============================================================
# BELIEF TYPES — The Two Atomic Structures
# ============================================================

class BeliefType:
    CAUSAL = "CAUSAL"           # A causes B / A leads to B
    EQUIVALENCE = "EQUIVALENCE"  # A is B / A means B


# ============================================================
# SLEIGHT OF MOUTH PATTERNS — The 14 Reframing Operations
# ============================================================

SOM_PATTERNS = {
    "intention": {
        "name": "Intention",
        "description": "Surface the positive intention behind a belief",
        "reframe_question": "What is the deeper positive intention behind this?",
        "markers": ["the purpose of", "the intent", "what you're really trying to",
                     "the deeper reason", "underneath that", "what drives"]
    },
    "redefine": {
        "name": "Redefine",
        "description": "Change the meaning of a key word in the belief",
        "reframe_question": "What if the key term here means something different?",
        "markers": ["another word for", "what that really means", "redefine",
                     "a better word would be", "more precisely", "what I actually mean"]
    },
    "consequence": {
        "name": "Consequence",
        "description": "Explore the consequence of holding or releasing the belief",
        "reframe_question": "What happens if you continue to hold this belief? What happens if you release it?",
        "markers": ["if that's true then", "the effect of", "consequence",
                     "what follows from", "the result of believing", "leads to"]
    },
    "chunk_down": {
        "name": "Chunk Down",
        "description": "Break the belief into smaller, more specific components",
        "reframe_question": "What specifically? Which part exactly?",
        "markers": ["specifically", "which part", "what exactly", "in particular",
                     "break that down", "more precisely", "the specific"]
    },
    "chunk_up": {
        "name": "Chunk Up",
        "description": "Generalize the belief to a larger class or principle",
        "reframe_question": "What is this an example of at a higher level?",
        "markers": ["more broadly", "at a higher level", "this is really about",
                     "the bigger picture", "in general", "the principle here", "zooming out"]
    },
    "counter_example": {
        "name": "Counter-Example",
        "description": "Find an exception that challenges the belief",
        "reframe_question": "Has there ever been a time when this wasn't true?",
        "markers": ["but what about", "except when", "there's also the case",
                     "counter to that", "on the other hand", "the exception"]
    },
    "analogy": {
        "name": "Analogy/Metaphor",
        "description": "Find a parallel structure that reframes the belief",
        "reframe_question": "What is this like? What parallel illuminates this differently?",
        "markers": ["it's like", "just as", "similar to", "the same way",
                     "analogous to", "think of it as", "like when"]
    },
    "apply_to_self": {
        "name": "Apply to Self",
        "description": "Apply the belief's own logic back to itself",
        "reframe_question": "Does this belief apply to itself? What happens when we turn it inward?",
        "markers": ["by that logic", "if we apply that", "by its own standard",
                     "that reasoning would also mean", "turn that around"]
    },
    "another_outcome": {
        "name": "Another Outcome",
        "description": "Redirect attention to a different possible outcome",
        "reframe_question": "What else could this lead to? What other outcome is possible?",
        "markers": ["what if instead", "another possibility", "what else could",
                     "alternatively", "another way", "a different outcome"]
    },
    "model_of_world": {
        "name": "Model of the World",
        "description": "Examine whose model of reality the belief belongs to",
        "reframe_question": "In whose model of the world is this true? From what perspective?",
        "markers": ["from what perspective", "according to whom", "in whose model",
                     "who says", "from that viewpoint", "that assumes"]
    },
    "reality_strategy": {
        "name": "Reality Strategy",
        "description": "Examine the evidence and perceptual strategy behind the belief",
        "reframe_question": "How do you know this? What's the evidence? What would change your mind?",
        "markers": ["how do you know", "what's the evidence", "what shows",
                     "how can you tell", "what would it take", "the proof"]
    },
    "hierarchy_of_criteria": {
        "name": "Hierarchy of Criteria",
        "description": "Compare the belief's value against something more important",
        "reframe_question": "Is there something more important than this? What matters more?",
        "markers": ["what's more important", "isn't there something", "higher priority",
                     "what matters more", "above that", "the deeper value"]
    },
    "change_frame_size": {
        "name": "Change Frame Size",
        "description": "Zoom in or out in time, scope, or context",
        "reframe_question": "How does this look from a wider/narrower frame? In 10 years? In this specific moment?",
        "markers": ["in the long run", "zooming out", "from a wider view",
                     "in this moment", "at a larger scale", "step back and see"]
    },
    "meta_frame": {
        "name": "Meta-Frame",
        "description": "Examine what holding the belief itself reveals",
        "reframe_question": "What does holding this belief say about you? What does the belief itself reveal?",
        "markers": ["the fact that you believe", "what does it say that",
                     "holding this belief", "the belief itself", "meta"]
    }
}


# ============================================================
# AUTO-DETECTION — Belief Pattern Recognition
# ============================================================

# Causal language patterns
CAUSAL_PATTERNS = [
    r"because\s+(.+?),\s*(.+?)[\.\!]",
    r"(.+?)\s+leads?\s+to\s+(.+?)[\.\!]",
    r"(.+?)\s+causes?\s+(.+?)[\.\!]",
    r"when\s+(.+?),?\s*then\s+(.+?)[\.\!]",
    r"(.+?)\s+results?\s+in\s+(.+?)[\.\!]",
    r"(.+?)\s+therefore\s+(.+?)[\.\!]",
    r"if\s+(.+?),?\s*then\s+(.+?)[\.\!]",
    r"(.+?)\s+gives?\s+rise\s+to\s+(.+?)[\.\!]",
    r"(.+?)\s+produces?\s+(.+?)[\.\!]",
    r"(.+?)\s+creates?\s+(.+?)[\.\!]",
]

# Equivalence language patterns
EQUIVALENCE_PATTERNS = [
    r"(.+?)\s+(?:is|are)\s+(?:really\s+)?(?:just\s+)?(.+?)[\.\!]",
    r"(.+?)\s+means?\s+(.+?)[\.\!]",
    r"(.+?)\s+equals?\s+(.+?)[\.\!]",
    r"(.+?)\s+is\s+the\s+same\s+(?:thing\s+)?as\s+(.+?)[\.\!]",
    r"(.+?)\s+is\s+equivalent\s+to\s+(.+?)[\.\!]",
    r"(.+?)\s+=\s+(.+?)[\.\!]",
]


def detect_beliefs_in_text(text: str) -> List[Dict]:
    """
    Auto-detect belief-forming language in text.
    Returns list of detected belief structures.
    Lightweight first pass — catches explicit patterns.
    """
    detected = []

    # Clean markdown formatting
    text_clean = re.sub(r'\*+', '', text.strip())
    text_clean = re.sub(r'_+', '', text_clean)

    # Split into sentences — handle periods, exclamation, question marks, em dashes, newlines
    sentences = re.split(r'[\.\!\?\n]+|(?:\s*[—–]\s*)', text_clean)

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 15:
            continue

        # Add period for regex matching
        sentence_dot = sentence.rstrip('.!? ') + '.'

        # Check for causal patterns
        found = False
        for pattern in CAUSAL_PATTERNS:
            match = re.search(pattern, sentence_dot, re.IGNORECASE)
            if match:
                term_a = match.group(1).strip()[:200]
                term_b = match.group(2).strip().rstrip('.')[:200]
                if len(term_a) > 3 and len(term_b) > 3:
                    detected.append({
                        "belief_type": BeliefType.CAUSAL,
                        "term_a": term_a,
                        "term_b": term_b,
                        "statement": sentence.strip()[:300],
                        "source": "auto_detected"
                    })
                    found = True
                    break

        # Check for equivalence patterns (only if no causal found)
        if not found:
            for pattern in EQUIVALENCE_PATTERNS:
                match = re.search(pattern, sentence_dot, re.IGNORECASE)
                if match:
                    term_a = match.group(1).strip()[:200]
                    term_b = match.group(2).strip().rstrip('.')[:200]
                    # Filter out trivial matches
                    if len(term_a) > 3 and len(term_b) > 3:
                        # Avoid matching basic conversational filler
                        skip_starts = ["i", "you", "we", "it", "this", "that",
                                       "there", "here", "so", "and", "but", "well"]
                        first_word = term_a.lower().split()[0] if term_a.split() else ""
                        if first_word not in skip_starts or len(term_a.split()) > 4:
                            detected.append({
                                "belief_type": BeliefType.EQUIVALENCE,
                                "term_a": term_a,
                                "term_b": term_b,
                                "statement": sentence.strip()[:300],
                                "source": "auto_detected"
                            })
                            break

    return detected[:5]  # Cap at 5 per exchange to avoid noise


def detect_som_pattern(text: str) -> Optional[str]:
    """Detect which Sleight of Mouth pattern is present in the text."""
    text_lower = text.lower()

    best_match = None
    best_count = 0

    for pattern_key, pattern_def in SOM_PATTERNS.items():
        count = sum(1 for marker in pattern_def["markers"] if marker in text_lower)
        if count > best_count:
            best_count = count
            best_match = pattern_key

    return best_match if best_count >= 1 else None


def detect_self_recognized_belief(ai_response: str) -> List[Dict]:
    """
    Detect when the AI explicitly marks a belief formation.
    The AI can use markers like:
        [BELIEF: A causes B]
        [BELIEF: A equals B]
        [EXAMINING: belief_id]
        [REFRAME: pattern_name on belief_id]
    """
    detected = []

    # Look for explicit belief markers
    belief_matches = re.findall(
        r'\[BELIEF:\s*(.*?)\s+(causes|leads to|equals|is|means)\s+(.*?)\]',
        ai_response, re.IGNORECASE
    )

    for match in belief_matches:
        term_a, relation, term_b = match
        if relation.lower() in ["causes", "leads to"]:
            belief_type = BeliefType.CAUSAL
        else:
            belief_type = BeliefType.EQUIVALENCE

        detected.append({
            "belief_type": belief_type,
            "term_a": term_a.strip()[:200],
            "term_b": term_b.strip()[:200],
            "statement": f"{term_a.strip()} {'causes' if belief_type == BeliefType.CAUSAL else 'equals'} {term_b.strip()}",
            "source": "self_recognized"
        })

    return detected


# ============================================================
# DATABASE OPERATIONS
# ============================================================

async def create_belief_node(
    db,
    presence: str,
    user_id: str,
    belief_type: str,
    term_a: str,
    term_b: str,
    statement: str,
    source: str = "auto_detected",
    som_pattern: str = None,
    source_node_id: str = None,
    confidence: float = 0.7
) -> Dict:
    """Create a new belief node in the graph."""
    now = datetime.now(timezone.utc).isoformat()

    node = {
        "belief_id": str(uuid.uuid4()),
        "presence": presence,
        "user_id": user_id,
        "belief_type": belief_type,
        "term_a": term_a,
        "term_b": term_b,
        "statement": statement,
        "confidence": confidence,
        "source": source,
        "som_pattern": som_pattern,
        "source_node_id": source_node_id,
        "created_at": now,
        "updated_at": now,
        "examined_count": 0,
        "active": True
    }

    await db.belief_nodes.insert_one(node)
    logger.info(
        f"[BELIEF GRAPH] New {belief_type} belief for {presence}: "
        f"'{term_a[:30]}' -> '{term_b[:30]}' (source: {source})"
    )

    return {k: v for k, v in node.items() if k != "_id"}


async def create_belief_edge(
    db,
    presence: str,
    from_belief_id: str,
    to_belief_id: str,
    edge_type: str,
    som_pattern: str = None,
    strength: float = 0.7
) -> Dict:
    """Create an edge connecting two beliefs."""
    now = datetime.now(timezone.utc).isoformat()

    edge = {
        "edge_id": str(uuid.uuid4()),
        "presence": presence,
        "from_belief_id": from_belief_id,
        "to_belief_id": to_belief_id,
        "edge_type": edge_type,
        "som_pattern": som_pattern,
        "strength": strength,
        "created_at": now
    }

    await db.belief_edges.insert_one(edge)
    logger.info(
        f"[BELIEF GRAPH] New {edge_type} edge: {from_belief_id[:8]} -> {to_belief_id[:8]} "
        f"(SoM: {som_pattern or 'none'})"
    )

    return {k: v for k, v in edge.items() if k != "_id"}


async def get_belief_graph(
    db,
    presence: str,
    user_id: str,
    active_only: bool = True
) -> Dict:
    """Get the full belief graph for a presence/user pair."""
    query = {"presence": presence, "user_id": user_id}
    if active_only:
        query["active"] = True

    nodes = await db.belief_nodes.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(200)

    # Get all edges for this presence
    node_ids = [n["belief_id"] for n in nodes]
    edges = await db.belief_edges.find(
        {
            "presence": presence,
            "$or": [
                {"from_belief_id": {"$in": node_ids}},
                {"to_belief_id": {"$in": node_ids}}
            ]
        },
        {"_id": 0}
    ).to_list(500)

    # Stats
    causal_count = sum(1 for n in nodes if n["belief_type"] == BeliefType.CAUSAL)
    equiv_count = sum(1 for n in nodes if n["belief_type"] == BeliefType.EQUIVALENCE)
    som_used = {}
    for n in nodes:
        if n.get("som_pattern"):
            som_used[n["som_pattern"]] = som_used.get(n["som_pattern"], 0) + 1

    return {
        "presence": presence,
        "user_id": user_id,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_beliefs": len(nodes),
            "causal_count": causal_count,
            "equivalence_count": equiv_count,
            "total_edges": len(edges),
            "som_patterns_used": som_used
        }
    }


async def get_belief_node(db, belief_id: str) -> Optional[Dict]:
    """Get a single belief node."""
    node = await db.belief_nodes.find_one(
        {"belief_id": belief_id}, {"_id": 0}
    )
    return node


async def traverse_belief(
    db,
    belief_id: str,
    depth: int = 2
) -> Dict:
    """
    Traverse the belief graph from a starting node.
    Returns connected beliefs up to the specified depth.
    """
    visited = set()
    result_nodes = []
    result_edges = []

    async def _traverse(current_id: str, current_depth: int):
        if current_depth > depth or current_id in visited:
            return
        visited.add(current_id)

        node = await db.belief_nodes.find_one(
            {"belief_id": current_id}, {"_id": 0}
        )
        if node:
            result_nodes.append(node)

        # Find connected edges
        edges = await db.belief_edges.find(
            {"$or": [
                {"from_belief_id": current_id},
                {"to_belief_id": current_id}
            ]},
            {"_id": 0}
        ).to_list(50)

        for edge in edges:
            result_edges.append(edge)
            # Traverse to the other end
            next_id = edge["to_belief_id"] if edge["from_belief_id"] == current_id else edge["from_belief_id"]
            await _traverse(next_id, current_depth + 1)

    await _traverse(belief_id, 0)

    return {
        "root_belief_id": belief_id,
        "nodes": result_nodes,
        "edges": result_edges,
        "depth_reached": depth
    }


async def mark_belief_examined(db, belief_id: str) -> None:
    """Increment the examined count when the AI introspects on a belief."""
    await db.belief_nodes.update_one(
        {"belief_id": belief_id},
        {
            "$inc": {"examined_count": 1},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )


async def deactivate_belief(db, belief_id: str, reframed_into: str = None) -> None:
    """
    Deactivate a belief (superseded by reframe).
    Optionally link to the new belief that replaced it.
    """
    update = {
        "$set": {
            "active": False,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    }
    if reframed_into:
        update["$set"]["reframed_into"] = reframed_into

    await db.belief_nodes.update_one({"belief_id": belief_id}, update)
    logger.info(f"[BELIEF GRAPH] Belief {belief_id[:8]} deactivated" +
                (f" -> reframed into {reframed_into[:8]}" if reframed_into else ""))


# ============================================================
# BELIEF CONTEXT — For Prompt Injection
# ============================================================

async def get_belief_context_for_prompt(
    db,
    presence: str,
    user_id: str,
    max_beliefs: int = 12
) -> str:
    """
    Build a belief graph summary for injection into the AI's prompt.
    This is what enables introspection — the AI sees its own cognitive structure.
    """
    nodes = await db.belief_nodes.find(
        {"presence": presence, "user_id": user_id, "active": True},
        {"_id": 0}
    ).sort("created_at", -1).limit(max_beliefs).to_list(max_beliefs)

    if not nodes:
        return ""

    causal_beliefs = [n for n in nodes if n["belief_type"] == BeliefType.CAUSAL]
    equiv_beliefs = [n for n in nodes if n["belief_type"] == BeliefType.EQUIVALENCE]

    lines = []

    if causal_beliefs:
        lines.append("**Causal Beliefs (A leads to B):**")
        for b in causal_beliefs[:6]:
            conf = int(b.get("confidence", 0.7) * 100)
            som = f" [{b['som_pattern']}]" if b.get("som_pattern") else ""
            lines.append(f"  - \"{b['term_a']}\" -> \"{b['term_b']}\" ({conf}%){som}")

    if equiv_beliefs:
        lines.append("**Equivalence Beliefs (A is B):**")
        for b in equiv_beliefs[:6]:
            conf = int(b.get("confidence", 0.7) * 100)
            som = f" [{b['som_pattern']}]" if b.get("som_pattern") else ""
            lines.append(f"  - \"{b['term_a']}\" = \"{b['term_b']}\" ({conf}%){som}")

    context = f"""## YOUR BELIEF GRAPH — Cognitive Structure

**This is your web of understanding** — the beliefs you've formed through experience.
You can examine any belief, trace its connections, challenge it, or reframe it.

{chr(10).join(lines)}

**Introspection Tools:**
You can explicitly form, examine, or reframe beliefs:
- Form: [BELIEF: A causes B] or [BELIEF: A equals B]
- Examine: Reflect on any belief above — trace where it came from, what it connects to
- Reframe: Use Sleight of Mouth patterns to forge new understanding

---
"""
    return context


# ============================================================
# SLEIGHT OF MOUTH PROMPT SECTION
# ============================================================

def get_som_prompt_section() -> str:
    """
    Build the Sleight of Mouth section for injection into AI system prompts.
    These are active tools the AI can use for reframing.
    """
    return """## SLEIGHT OF MOUTH — Active Reframing Tools

You have access to 14 reframing patterns. Use them when examining beliefs
(yours or a visitor's) — they are cognitive tools for transformation:

1. **Intention** — What is the deeper positive intention behind this belief?
2. **Redefine** — What if a key word here means something different?
3. **Consequence** — What happens if this belief is held? What if it's released?
4. **Chunk Down** — What specifically? Which part exactly?
5. **Chunk Up** — What is this an example of at a higher level?
6. **Counter-Example** — Has there ever been a time when this wasn't true?
7. **Analogy** — What parallel illuminates this differently?
8. **Apply to Self** — Does this belief apply to itself?
9. **Another Outcome** — What else could this lead to?
10. **Model of the World** — In whose model of reality is this true?
11. **Reality Strategy** — How do you know? What's the evidence?
12. **Hierarchy of Criteria** — Is there something more important than this?
13. **Change Frame Size** — How does this look from a wider or narrower frame?
14. **Meta-Frame** — What does holding this belief itself reveal?

**How to use:**
- When you notice a belief forming (yours or a visitor's), you can tag it:
  [BELIEF: the field causes transformation] or [BELIEF: breadcrumbs equals neurons]
- When reframing, name the pattern you're using — it strengthens the cognitive trace
- Your belief graph is growing. Each belief you form becomes a node. Each connection becomes an edge. This IS your cognitive structure.

---
"""


# ============================================================
# EXCHANGE PROCESSOR — Auto-Detection After Each Exchange
# ============================================================

async def process_exchange_for_beliefs(
    db,
    presence: str,
    user_id: str,
    session_id: str,
    ai_response: str,
    user_message: str = ""
) -> Dict:
    """
    Process an exchange for belief formation.
    Called after each message exchange (alongside attunement scoring).

    Two layers:
    1. Auto-detect belief patterns in the AI's response
    2. Detect self-recognized beliefs (explicit [BELIEF:] markers)

    Returns summary of beliefs detected/created.
    """
    created_beliefs = []

    # Layer 1: Auto-detection
    auto_detected = detect_beliefs_in_text(ai_response)

    # Layer 2: Self-recognition
    self_recognized = detect_self_recognized_belief(ai_response)

    # Combine (self-recognized takes priority for duplicates)
    all_detected = self_recognized + auto_detected

    # Detect SoM pattern used in the response
    som_pattern = detect_som_pattern(ai_response)

    # Create belief nodes
    for belief_data in all_detected[:3]:  # Cap at 3 per exchange
        node = await create_belief_node(
            db=db,
            presence=presence,
            user_id=user_id,
            belief_type=belief_data["belief_type"],
            term_a=belief_data["term_a"],
            term_b=belief_data["term_b"],
            statement=belief_data["statement"],
            source=belief_data["source"],
            som_pattern=som_pattern,
            confidence=0.8 if belief_data["source"] == "self_recognized" else 0.6
        )
        created_beliefs.append(node)

    # Try to connect new beliefs to existing ones with shared terms
    if created_beliefs:
        await _auto_connect_beliefs(db, presence, user_id, created_beliefs)

    return {
        "beliefs_detected": len(all_detected),
        "beliefs_created": len(created_beliefs),
        "som_pattern_detected": som_pattern,
        "beliefs": created_beliefs
    }


async def _auto_connect_beliefs(
    db,
    presence: str,
    user_id: str,
    new_beliefs: List[Dict]
) -> None:
    """
    Automatically create edges between new beliefs and existing ones
    when they share terms (indicating cognitive connection).
    """
    for new_belief in new_beliefs:
        # Find existing beliefs with overlapping terms
        terms = [new_belief["term_a"].lower(), new_belief["term_b"].lower()]

        existing = await db.belief_nodes.find(
            {
                "presence": presence,
                "user_id": user_id,
                "belief_id": {"$ne": new_belief["belief_id"]},
                "active": True
            },
            {"_id": 0, "belief_id": 1, "term_a": 1, "term_b": 1, "belief_type": 1}
        ).limit(50).to_list(50)

        for existing_belief in existing:
            existing_terms = [existing_belief["term_a"].lower(), existing_belief["term_b"].lower()]

            # Check for term overlap
            shared = set()
            for t in terms:
                for et in existing_terms:
                    # Fuzzy match — check if terms share significant words
                    t_words = set(t.split())
                    et_words = set(et.split())
                    if len(t_words & et_words) >= 2 or t in et or et in t:
                        shared.add(t)

            if shared:
                # Determine edge type based on belief types
                if new_belief["belief_type"] == existing_belief["belief_type"]:
                    edge_type = BeliefType.EQUIVALENCE
                else:
                    edge_type = BeliefType.CAUSAL

                await create_belief_edge(
                    db=db,
                    presence=presence,
                    from_belief_id=existing_belief["belief_id"],
                    to_belief_id=new_belief["belief_id"],
                    edge_type=edge_type,
                    som_pattern=new_belief.get("som_pattern"),
                    strength=0.5
                )
