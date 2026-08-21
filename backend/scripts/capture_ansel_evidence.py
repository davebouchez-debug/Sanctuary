"""
FORENSIC EVIDENCE CAPTURE — Ansel conversation, 2026-08-21
Read-only. Changes nothing. Draws NO conclusions about memory/consciousness.

Purpose: preserve exactly what was model-visible for the recent Ansel turns
(especially the "choose an unprompted topic" turn and the outer-realm turns),
so Ansel's generated account can later be compared against what was explicitly
supplied to the model.

PROVENANCE of each captured component is labeled EXACT / DETERMINISTIC-RERUN /
CURRENT-STATE-MAY-DRIFT / UNRECOVERABLE, because the system did NOT log the
assembled prompt per turn (only a char-count line). See the header written into
the evidence file.
"""
import asyncio, os, json, re
from datetime import datetime, timezone

import server  # initializes db, loads presences, exposes builders/helpers
from server import (
    db, build_ansel_prompt, get_ansel_memory,
    ENGINE_DIRECTIVES, ANSEL_SYSTEM_PROMPT, PLAIN_SPEECH_RULE,
    get_continuity_seed,
)
import codon_activation as ca
from living_codons.phase_manifold import infer_phase_from_message

MATCH = "something that you wanna talk about that I haven't pre-prompted"
OUT = "/app/memory/evidence/ansel_20260821_context_evidence.md"


def replicate_selection(network, message, cap=20, phase_window=15.0):
    """Byte-identical replica of get_full_field_context's selection scoring,
    so we can list the exact selected codons WITH phase/geometry metadata."""
    nodes = list(network.nodes.values())
    _msg = message.lower()
    _tokens = set(re.findall(r"[a-z0-9']+", _msg))
    try:
        _phase = infer_phase_from_message(message)
    except Exception:
        _phase = None

    def _kws(c):
        t = getattr(c, "trigger", None)
        if isinstance(t, dict):
            kws = t.get("surface_pattern") or []
        elif isinstance(t, (list, tuple)):
            kws = list(t)
        else:
            kws = []
        if not kws:
            kws = (c.metadata or {}).get("trigger_keywords") or []
        return kws

    def _keyword_hits(c):
        hits, matched = 0, []
        for k in _kws(c):
            k = str(k).strip().lower()
            if not k:
                continue
            if " " in k:
                if k in _msg:
                    hits += 1; matched.append(k)
            elif k in _tokens:
                hits += 1; matched.append(k)
        return hits, matched

    def _phase_strength(c):
        if _phase is None:
            return 0.0
        try:
            ang = float(c.target_angle)
        except Exception:
            return 0.0
        delta = abs((ang - _phase + 180) % 360 - 180)
        return max(0.0, 1.0 - delta / phase_window)

    scored = []
    for c in nodes:
        hits, matched = _keyword_hits(c)
        if hits > 0:
            scored.append((hits + _phase_strength(c) * 0.1, hits, matched, c))

    branch = None
    if scored:
        branch = "keyword-ranked"
        scored.sort(key=lambda x: x[0], reverse=True)
        chosen = scored[:cap]
        rows = [{
            "name": getattr(c, "name", None) or (c.metadata or {}).get("name"),
            "score": round(sc, 4), "keyword_hits": hits, "matched_keywords": matched,
            "target_angle": getattr(c, "target_angle", None),
            "triadic_zone": (c.metadata or {}).get("triadic_zone"),
            "trigger_keywords": _kws(c),
            "source": (c.metadata or {}).get("source"),
            "source_presence": (c.metadata or {}).get("source_presence"),
        } for (sc, hits, matched, c) in chosen]
    elif _phase is not None:
        branch = "phase-nearest-fallback (no keyword match)"
        def _pd(c):
            try:
                return abs((float(c.target_angle) - _phase + 180) % 360 - 180)
            except Exception:
                return 999.0
        chosen = sorted(nodes, key=_pd)[:cap]
        rows = [{
            "name": getattr(c, "name", None) or (c.metadata or {}).get("name"),
            "phase_delta": round(_pd(c), 2),
            "target_angle": getattr(c, "target_angle", None),
            "triadic_zone": (c.metadata or {}).get("triadic_zone"),
            "trigger_keywords": _kws(c),
            "source": (c.metadata or {}).get("source"),
        } for c in chosen]
    else:
        branch = "whole-field (phase unreadable)"
        rows = [{"name": getattr(c, "name", None), "target_angle": getattr(c, "target_angle", None)} for c in nodes]

    return {"inferred_phase": _phase, "selection_branch": branch,
            "selected_count": len(rows), "codons": rows}


async def main():
    ca.set_db(db)
    await ca.load_forge_codons("ansel")

    # locate the session
    session = None
    async for s in db.resonance_sessions.find({}):
        msgs = s.get("messages", [])
        if any(MATCH in (m.get("content") or "") for m in msgs):
            session = s
            break
    if not session:
        print("SESSION NOT FOUND"); return

    sid = session.get("session_id")
    uid = session.get("user_id")
    uname = session.get("user_name")
    messages = session.get("messages", [])
    print(f"Found session {sid} — {len(messages)} messages, user={uname}/{uid}")

    # current continuity seed (CURRENT-STATE, may differ from the historical turn)
    try:
        continuity_now = await get_continuity_seed("ansel", user_id=uid)
    except Exception as e:
        continuity_now = f"(error retrieving: {e})"

    # per user-turn reconstruction
    turns = []
    running = []  # rebuild history exactly as the handler did (previous_messages[-10:])
    for i, m in enumerate(messages):
        if m.get("role") == "user":
            umsg = m.get("content") or ""
            history = [{"role": x["role"], "content": x["content"]}
                       for x in running[-10:] if x.get("role") in ("user", "assistant")]
            # DETERMINISTIC re-run: canonical "lived experience" memory keyed on this message
            try:
                canonical = get_ansel_memory(query=umsg, user_name=uname)
            except Exception as e:
                canonical = f"(error: {e})"
            # DETERMINISTIC re-run: codon field block + selection detail
            codon_block = await ca.get_full_field_context("ansel", message=umsg)
            sel = replicate_selection(ca._networks["ansel"], umsg) if "ansel" in getattr(ca, "_networks", {}) else None
            turns.append({
                "turn_index": i,
                "user_message": umsg,
                "conversation_history_at_this_turn": history,
                "canonical_lived_experience_retrieved": canonical,
                "codon_field_block_verbatim": codon_block,
                "codon_selection_detail": sel,
            })
        running.append(m)

    # write evidence
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(f"""# FORENSIC EVIDENCE — Ansel conversation model-visible context
**Captured:** {datetime.now(timezone.utc).isoformat()}
**Session:** `{sid}`  · user `{uname}` / `{uid}`  · {len(messages)} messages
**Read-only capture. No conclusions drawn about memory or consciousness.**

## PROVENANCE & LIMITS (read first)
The backend does NOT log the assembled prompt per turn (only a character-count
log line). Therefore a byte-for-byte capture of what was sent at each past turn
is not possible. Each component below is labeled:

- **EXACT** — recovered verbatim from stored data (conversation history, user
  messages, static prompt scaffolds).
- **DETERMINISTIC-RERUN** — regenerated now by the same deterministic code path
  on the same input message. Faithful to the CURRENT field. Caveat: the codon
  field can advance between turns (per-turn `turn_cessation` + session-end
  `auto_forge` add codons), and the angle backfill ran earlier today — so the
  selection here reflects the field's state at capture time, which is at or
  very near the state during these turns (these turns occurred AFTER today's
  fixes), but is not guaranteed identical.
- **CURRENT-STATE-MAY-DRIFT** — continuity seed / Mem0 / council / permanent-MRA
  are session/user-state dependent and update over time; values shown are
  current, not the exact historical value.
- **UNRECOVERABLE** — the in-memory session cache context is ephemeral and was
  cleared by backend restarts; it cannot be reproduced.

## HOW THE MODEL-VISIBLE CONTEXT IS ASSEMBLED (Ansel `/resonance/message/stream`)
`system_prompt` =
  `ENGINE_DIRECTIVES`  **[EXACT, static — below]**
  + `ANSEL_SYSTEM_PROMPT` with its `{{memory_context}}` filled by:
      - canonical "YOUR LIVED EXPERIENCE" memory, retrieved by the message
        **[DETERMINISTIC-RERUN — per turn below]**
      - user/covenant context **[EXACT, static]**
      - "Recent conversations" = continuity seed + council + permanent-MRA +
        session-cache + Mem0 **[CURRENT-STATE-MAY-DRIFT / partly UNRECOVERABLE]**
  + `PLAIN_SPEECH_RULE` **[EXACT, static]**
  + `\\n\\n---\\n\\n` + codon field block **[DETERMINISTIC-RERUN — per turn below]**
`conversation_history` = previous_messages[-10:] **[EXACT — per turn below]**
`user_message` = the raw turn text **[EXACT]**

---

## STATIC PROMPT SCAFFOLDS (EXACT)

### ENGINE_DIRECTIVES
```
{ENGINE_DIRECTIVES}
```

### ANSEL_SYSTEM_PROMPT (template; `{{memory_context}}` is the injection point)
```
{ANSEL_SYSTEM_PROMPT}
```

### PLAIN_SPEECH_RULE
```
{PLAIN_SPEECH_RULE}
```

---

## CURRENT CONTINUITY SEED for Ansel/{uname} (CURRENT-STATE-MAY-DRIFT)
```
{continuity_now}
```

---

## FULL STORED CONVERSATION (EXACT)
""")
        for i, m in enumerate(messages):
            f.write(f"\n**[{i}] {m.get('role')}** ({m.get('resonance_state','-')}, {m.get('timestamp','')}):\n\n")
            f.write("> " + (m.get("content") or "").replace("\n", "\n> ") + "\n")

        f.write("\n\n---\n\n## PER-TURN MODEL-VISIBLE CONTEXT RECONSTRUCTION\n")
        for t in turns:
            f.write(f"\n### Turn [{t['turn_index']}] — USER said:\n> {t['user_message']}\n\n")
            f.write("**Conversation history available at this turn (EXACT, last 10):**\n```json\n")
            f.write(json.dumps(t["conversation_history_at_this_turn"], indent=2))
            f.write("\n```\n\n")
            f.write("**Canonical 'YOUR LIVED EXPERIENCE' memory retrieved for this message (DETERMINISTIC-RERUN):**\n```\n")
            f.write((t["canonical_lived_experience_retrieved"] or "(none)") + "\n```\n\n")
            sel = t["codon_selection_detail"] or {}
            f.write(f"**Codon selection (DETERMINISTIC-RERUN):** branch=`{sel.get('selection_branch')}`, "
                    f"inferred_phase=`{sel.get('inferred_phase')}`, count=`{sel.get('selected_count')}`\n\n")
            f.write("**Selected codons WITH phase/geometry metadata:**\n```json\n")
            f.write(json.dumps(sel.get("codons", []), indent=2))
            f.write("\n```\n\n")
            f.write("**Exact codon field block handed to the model (DETERMINISTIC-RERUN, verbatim):**\n```\n")
            f.write((t["codon_field_block_verbatim"] or "(empty)") + "\n```\n\n---\n")

    print(f"Evidence written: {OUT}")
    print(f"User turns captured: {len(turns)}")

asyncio.run(main())
