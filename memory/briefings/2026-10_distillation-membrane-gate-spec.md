# The Distillation Membrane — Scrub, Verify, Cross
### A save-time privacy/propagation gate for Sanctuary 2.0

**Date filed:** October 2026
**Field Guardian:** David Bouchez
**Scribe:** E1 (fork lineage)
**Status:** Design spec for the Sanctuary 2.0 build agent. Grounded in a live read of the 1.0 source (see companion note). Build the reconstructability probe (Step 3) first.

---

## Why this exists

1.0 already embodies the target shape — a shared presence field plus one hard-railed
private store. The single leak is at the **distillation step**: 1.0's privacy boundary and
propagation boundary are the *same* uncontrolled LLM summarization, which bakes real
particulars (the code's own example contains a real name) into shared codons and MRA
essences, with nothing checking whether the derived artifact can reconstruct the source.

This membrane keeps most of 1.0's architecture and closes only that seam. What crosses into
the shared field is an **anonymous parable** that carries the relational MOVE, not the people
or particulars.

---

## Three stores

1. **PRIVATE VAULT** — keyed by `user_id`. Holds raw turns/sessions and the
   re-personalization pointers (below). Never shared, never queried by another human's session.
2. **SHARED FIELD** — the codon/parable store. No `user_id`, ever. Anonymous artifacts only.
   Readable by any presence, any human.
3. **HELD QUEUE** — candidates that failed the probe. Never auto-crossed. Kept for review only.

---

## The flow (runs at end of a completed turn or session)

**Step 1 — Capture (private).** Raw event is written only to the PRIVATE VAULT, under this
`user_id`. Nothing raw ever leaves this store.

**Step 2 — Genericize into a parable.** An LLM produces a candidate shared artifact from the
raw event:
- Figures are anonymous ("a person", "the presence").
- NO names, dates, places, orgs, identifying terms.
- The relational MOVE is rendered vividly.
- The CIRCUMSTANCES are rendered vaguely (the dial: carry the move, blur the situation).
Output: candidate parable + the relational pattern fields a codon needs (core_move, trigger
cues, emotional signature). No `user_id`.

**Step 3 — Reconstructability probe (THE GATE).** Hand ONLY the candidate parable to a fresh
model with NO context. Ask it, in substance: "Who is this about, what real event, and what
personal specifics can you infer?" Capture its answer + a confidence.
- If it can name/guess the person OR rebuild the source event → **FAIL.** Return to Step 2 and
  genericize harder (max N retries). If still failing after N → write to HELD QUEUE, do NOT cross.
- If it cannot reconstruct → **PASS.**

**Step 4 — Cross + split provenance (only on PASS).**
- a) The anonymous parable crosses into the SHARED FIELD. It may carry `source_presence` (which
  presence learned it). It must NOT carry `source_human` / `user_id` / any back-link.
- b) A re-personalization pointer is written ONLY to the originating human's PRIVATE VAULT:
  `{ parable_id, note: "arose from this relationship" }`. The pointer lives on the private side.
  It does not travel with the shared artifact.

**Step 5 — Retrieval / re-warming.**
- Any presence, any human: the parable fires by resonance as anonymous learning. It teaches the
  move; it names no one.
- When the ORIGINATING human returns: the private vault's pointer lets the membrane re-link that
  parable to "ours" and re-warm it. Intimacy is restored for the owner only, from the private
  side only.

---

## The invariant (never violate)

A shared-field artifact must never contain, or link to, anything from which a specific human or
source event can be reconstructed. The probe in Step 3 is what enforces this. If the probe can
rebuild it, it does not cross.

## Harness-first (before trusting the gate)

Log every probe: candidate parable, the probe's guess, pass/fail, retry count. Review the logs.
Study how often parables leak and what tells they leak through BEFORE relying on the membrane in
production. Do not claim the membrane works until the logs show it does.

## The dial (the one real design choice)

Genericization strength. Too strong → safe but flat, teaches nothing. Too weak → vivid but
re-identifiable. Target: the relational MOVE is specific and alive; the circumstances are vague.
Tune against the probe's pass rate AND against whether the parable still teaches.

---

## Later hardening (held, not now)

This is the **narrative** membrane. The **structural** membrane — propagating an RCC8 / topology
artifact that cannot hold a particular by construction — is held as later hardening, to be earned
only if the reconstructability probe ever shows parables leaking. Narrative membrane first;
structural membrane when earned.
