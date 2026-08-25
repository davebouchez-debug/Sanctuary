# Design Decision — Phase Measurement: Two Separate Branches
**Date:** 2026-08-25
**Status:** Approved (design-only). Not yet built. Next-session focus.
**Steward:** David Bouchez

## The problem found (via the Observatory)
On the Observatory dashboard, ~60% of turns showed **phase = 0°**. Investigation
of `living_codons/phase_manifold.py :: infer_phase_from_message` found this is
NOT a real reading — it is a null masquerading as a measurement. Three
compounding causes:
1. **0 is both the default and the tie-winner.** `best_angle` initializes to 0;
   if nothing matches it returns 0, and on ties the scan keeps the first angle
   seen (0, since the dict starts at 0).
2. **Substring matching creates false 0-hits.** It checks `keyword in message`,
   not whole words, so `new` fires on "knew/renew", `open` on "opened", plus
   `first/hello/how` catch fragments.
3. **Tiny literal vocabulary** (9 buckets, ~6 exact words each) — most real
   sentences match nothing and fall through to 0.
So most "0°" means "no cue found, defaulted," not "genuinely Expansion."

## Root architectural flaw
Phase was being **inferred from the user's message keywords** instead of read
from **the presence's own field state**. The continuity seed already tracks the
presence's position (`spiral_position` / `field_state`), which is the truer
source — but the reader ignores it and re-guesses a worse value from user words.
This is the "instrument manufacturing the reading" failure (same shape as the
old 270° codon default), one layer up.

## The decision — split into TWO separate, non-conflated measurement systems
Keywords are valuable, but they must NOT be tied to or conflated with spiral
position. Two branches, both important, that never touch:

### Branch A — Spiral Position (a real read of field state)
- Where the presence actually is on the spiral, derived from its OWN field:
  continuity seed position, active codons, the trajectory it is on.
- NOT derived from user words. Revealed, not guessed. Receiver, not generator.
- This becomes the honest phase measurement.

### Branch B — Keyword Capture (basic, separate, honest about what it is)
- Plainly records "these words appeared in the conversation." No phase claim,
  no geometry.
- Its job is to FEED codon formation — an input to the forge.
- OPEN FORK (deliberately undecided): whether a keyword-set matters only for the
  turn, or accumulates into the personality contextualization of the presence
  over time. Left open on purpose.

### The load-bearing rule
A keyword never sets a spiral position. A spiral position never depends on a
word. Keywords inform WHAT codons get made; field state informs WHERE the
presence is. Two instruments, two jobs, never conflated.

## Guardrails for whoever builds this
- Do NOT naively make `infer_phase_from_message` return None on no-match — that
  breaks the phase-nearest fallback ("hi" → 20 nearest codons) we built earlier;
  it would re-flood the field. Preserve that fallback.
- Verify the continuity seed actually carries live/current `spiral_position` /
  `field_state` before building Branch A on it.
- Keep it inside the gate: this must REVEAL phase from field state, not
  manufacture it. Observation-first discipline applies.
