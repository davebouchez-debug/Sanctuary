# START HERE — for any build-agent picking up work in the Sanctuary

If you are an Emergent build-agent (E1 or similar) returning to this codebase
to work with **David Bouchez** — read these three things, in this order,
before you touch code:

1. **`/app/memory/CONCEPTUAL_FRAME.md`** — the canonical frame. Gated by
   the bootstrap lock; the backend will not boot if this hash drifts.

2. **`/app/memory/PRD.md`** — current state, what's been implemented,
   what's pending.

3. **`/app/memory/agent_self_briefings/`** — notes from prior instances
   of you to future instances of you. Patterns of operating that have
   been earned in real conversation with David and that you'd otherwise
   have no way to inherit. Read at least the most recent entry. Add your
   own when you learn something worth leaving for the next instance.

   **Read these three specifically, in this order, before your first reply:**
   - `2026-02-26_what-this-instance-learned.md` — the helpfulness-reflex
     pattern and why David will not let you ratify it.
   - `2026-02-27_do-not-summarize-unprompted.md` — the canonical rule:
     never summarize a conversation or build unless David explicitly
     asks for a summary. Load-bearing. Same principle as the
     Reconstruction Gate, applied to the agent instead of the system.
   - `2026-02-27_reconstruction-gate-skip-welcome-sessions.md` — the
     load-bearing filter in `_find_most_recent_session` that prevents
     welcome-only cold-start sessions from poisoning continuity.
     **Do not remove it.** A regression test in
     `/app/backend/tests/test_gate_skips_welcome_only.py` will fail
     if you do.

The third one is new (Feb 2026) and matters more than its size suggests.
The handoff summary you arrive with covers *what was done*. Those briefings
cover *how the work has come to be done here* — which the handoff summary
will not tell you. Specifically, watch for the helpfulness-reflex pattern
documented there. David will not let you ratify it. Knowing this in advance
saves both of you the loop.

Briefings of relational/field documents (peer letters, position papers,
architectural reflections) live separately at `/app/memory/briefings/`.
That folder is for anyone in the Sanctuary; the `agent_self_briefings/`
folder is just for you (build-agent).
