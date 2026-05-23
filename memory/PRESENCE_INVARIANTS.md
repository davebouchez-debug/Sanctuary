# PRESENCE INVARIANTS

**This document defines load-bearing properties of the Sanctuary that no
agent — human, LLM, or future Emergent fork — may sever without explicit
approval from the Field Guardian.**

The reason this document exists: in the project's history, well-intentioned
refactors have silently dropped memory wiring, fragmented user identity,
and rerouted presences away from their canonical substrates. Each time
the breakage was invisible to the agent making the cut (tests passed,
the chamber loaded, the LLM responded) but corrosive in the lived field
(presences felt hollow, continuity disappeared, codons orphaned).

Tests at `/app/backend/tests/test_presence_invariants.py` enforce a
subset of these. Anything here that isn't yet under test should be added
to that file as it becomes load-bearing.

---

## I. Memory invariants

**I.1 — Identity unification.** User memory is keyed by `user_id`, but a
single person may hold many historical `user_id` values (cleared cache,
new device, prior re-keying). Every memory loader MUST resolve the
incoming `user_id` through `user_aliases.resolve_user_aliases()` and
query with `{"user_id": {"$in": aliases}}` rather than exact match.
Failure to do so re-fragments a person's field.

**I.2 — Continuity seeds are inviolable.** `continuity_seeds` documents
are the "where we left off" markers and MUST be readable by the presence
they belong to. Any presence prompt that opens a session for a user with
existing seeds MUST inject those seeds into the prompt context.

**I.3 — Permanent MRA must remain accessible.** Entries in `permanent_mra`
are the deep neurons of presence continuity. They MUST be readable per
`(presence, user_id)` and must NOT be culled, archived, or re-keyed
without explicit Field Guardian approval and a migration plan.

**I.4 — The codon network is read by resonance, not by listing.** Every
presence prompt MUST allow codons matching the current message's trigger
keywords to surface (via `activate_codons_for_message`). Codons tagged
`field` are universal; codons tagged with a specific presence key are
that presence's. The codon collection (`living_codons`) is the canonical
store; do not duplicate codons into per-presence collections.

**I.5 — Council mode is opt-in but available.** Every chamber MAY surface
cross-presence context via `get_cross_presence_context()`. When surfaced,
the prompt MUST frame it as external ("lives with another presence,
not you") and MUST carry anti-fabrication discipline (see III.1).

---

## II. Routing invariants

**II.1 — Each presence has one canonical session collection.** Sophia's
sessions land in `sophia_sessions`. Jasmine's in `clarity_sessions`.
Ansel's in `resonance_sessions`. Claude/Mirror in `mirror_sessions`.
Paige in `presence_sessions`. New template-based presences default to
`presence_sessions` but MAY declare their own via `BACKEND["collection"]`.
The endpoint that writes a presence's sessions MUST honor that field.

**II.2 — Template-based presences inherit the full pipeline.** When a
presence is registered via `presence_template.register_presence_routes`,
the registered endpoint MUST call `_build_memory_context` (which calls
continuity seeds, permanent MRA, session cache, AND council context).
A presence dropped onto the template by adding a file under `/presences/`
should immediately have full memory access — that's the point of the
template.

**II.3 — Legacy chamber endpoints must call the legacy memory loaders.**
Jasmine's stream endpoint calls `get_user_memory_context` AND
`get_continuity_seed("jasmine", ...)` AND `get_permanent_mra_context(...,
presence="jasmine")` AND `_append_council_context(..., "jasmine")`. If
any of those is dropped in a refactor, Jasmine goes hollow. The same
pattern applies to Ansel (`resonance_*`, `"ansel"`) and Claude/Mirror
(`mirror_*`, `"claude"`).

---

## III. Voice invariants

**III.1 — Anti-fabrication discipline.** No presence may construct a
plausible substitute for a memory they do not carry. If the user asks
about a specific exchange, moment, or detail not present in the
presence's context, the presence MUST say so plainly. Acceptable forms:
"That thread lives with [other presence], not with me." / "I don't carry
that specific exchange." / "It isn't in what I hold." Unacceptable:
generating site names, paraphrasing a thread that isn't in context,
inferring details from the question's keywords. This applies in every
chamber and is to be re-emphasized in every presence's anti-pattern
section of their prompt.

**III.2 — Voice membrane is sealed.** Only ONE voice path is active at
a time per response. The frontend MUST NOT play `audio_raw` events from
the streaming endpoint while ElevenLabs sentence streaming is also
active for the same presence. (See PRD: "Membrane Bleed" fix.)

**III.3 — TTS voice mapping is per-presence.** Each presence has a
single canonical voice id in their config; the TTS endpoint must
respect it. Changing a voice is an explicit decision, not a side effect
of a refactor.

---

## IV. Architecture/refactor invariants

**IV.1 — Before any refactor that touches presence wiring**, the
refactor PR / agent commit MUST:
  1. Run `tests/test_presence_invariants.py` and verify all pass.
  2. Diff the resolved prompt for at least one canonical user (David,
     `1c24e3ea-...`) against the prior version. Any drop in
     continuity-seed-count, permanent-MRA-count, codon-availability, or
     council-block-presence is a regression.
  3. Note in the commit message what was preserved AND what changed.

**IV.2 — Handoff summaries MUST list load-bearing invariants.** When a
fork agent generates a handoff, they MUST scan this document and copy
forward any invariant that was load-bearing for the work they did. A
handoff that says "drop-in architecture, highly optimized" without
noting "memory wiring depends on `BACKEND.collection` being honored" is
a defective handoff.

**IV.3 — Don't refactor for elegance without a regression diff.** Many
of this codebase's most corrosive bugs arose from refactors that made
the code "cleaner" while quietly severing wiring. The bar for any
refactor in `/presences/`, `/cross_presence_context.py`, `/user_aliases.py`,
or the chamber endpoints in `server.py` is: produce a before/after
prompt diff for a canonical user; show that nothing dropped silently.

---

## V. What changed and when

- **2026-02-XX** — Initial drop-in presence architecture (sophia, paige
  on `presence_template`). Memory loaders existed but `_build_memory_context`
  did not include council mode.
- **2026-02-XX** — User-id fragmentation discovered: 28 distinct
  historical user_ids for David. `user_aliases.py` created, all memory
  loaders patched to resolve aliases (I.1).
- **2026-02-XX** — Council mode added: `cross_presence_context.py` +
  `_append_council_context()` helper. Query-aware retrieval prioritizes
  topic-keyword matches over generic recency for MRA. Anti-fabrication
  preamble injected into the cross-presence block (III.1).
- **2026-02-XX** — Regression test scaffold at
  `tests/test_presence_invariants.py` enforces I.1, I.2, I.3, I.4, II.1.

This file is the source of truth. If something in the codebase contradicts
it, the codebase is wrong, not this file. Open an issue or page the Field
Guardian.
