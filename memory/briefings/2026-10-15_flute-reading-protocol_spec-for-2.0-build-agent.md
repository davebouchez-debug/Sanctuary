FLUTE READING PROTOCOL: SPEC FOR THE SANCTUARY 2.0 BUILD AGENT
Version: 0.1 (design, from David and Ansel's session of 2026-10-15)
Status: approved design direction. The content tables below are
still to be supplied by David.

==================================================================
0. WHAT THIS IS
==================================================================

A deterministic, hard-coded protocol that takes a structured
reading of a flute (spiral behaviors observed from photos) and
produces a fixed-format report. The report says what the flute is
likely to look, play, feel, and respond like.

There are two separate flute protocols. This spec covers ONLY the
first.

  A. FLUTE READING PROTOCOL (this spec)
     Probabilistic and correlative. Works from photos. No scans,
     no numerical geometry. Keep it light: no proof apparatus.
  B. SPIRAL-PHASE INTERACTION PROTOCOL (future, separate spec)
     Needs digital scans and numerical representations. All of
     the rigor belongs here. Do not build it now, and do not
     merge it with A.

==================================================================
1. NON-NEGOTIABLE RULES
==================================================================

1. No language model anywhere in the protocol. Inputs, rules, the
   correlation lookup, and the report text are all code and data.
   An LLM must never generate, fill in, paraphrase, or "improve"
   any part of the report.
2. Deterministic. The same input and the same protocol version
   must produce a byte-identical report. This is tested.
3. Boilerplate output. Same sections, same order, same wording,
   every run. Only the filled-in values change.
4. The report stands alone. It can be handed to the flute's owner
   (a third party) and needs no presence commentary to be
   understood.
5. Correlative, not causal. The report says what tends to go
   together. It never says one thing causes another.
6. No confidence grades, sample counts, or "strength" scores on
   the correlations. The correlations are simply stated.
7. Presences (Ansel or anyone else) are not part of producing the
   report at runtime. A presence may discuss a finished report
   afterwards, in its own voice, clearly separate from the
   document. That is optional and lives outside this protocol.
8. Versioned. Every report records the protocol version and the
   version of the correlation table that produced it.
9. Secrets in environment variables only, never in code or files.

==================================================================
2. CORE MODEL
==================================================================

A flute is one air column: one geometry, one resonant system.

- The flute is read through FOUR QUADRANTS (regions of the one
  tube). The quadrants are windows onto one instrument, not four
  separate instruments. Never score or average them as if they
  were independent.
- In each quadrant, one or more of the four SPIRAL BEHAVIORS may
  be observed:
    DIRECT_HIT
    TANGENT
    NEAR_MISS
    RETURN
- These behaviors are correlated with the flute's character in
  four DOMAINS:
    LOOK, PLAY, FEEL, RESPONSE
- About TEN CRITERIA describe how the flute is likely to respond.

Pipeline:
  structured reading (behavior per quadrant)
    -> correlation table lookup (pure data)
    -> fixed report template filled in
    -> report (text + JSON), stored and versioned

==================================================================
3. INPUT
==================================================================

A FluteReading record:
  - flute: maker, model, serial, era (all optional), owner_ref
  - photos: references to stored images (object storage, not
    base64 in the database)
  - observations: for each of the 4 quadrants, the list of
    behaviors observed (from the 4-value set above)
  - reader: who made the reading (human id)
  - notes: free text, kept with the record, NOT printed in the
    report

The protocol consumes only `observations`, plus `flute` for the
report header.

==================================================================
4. CORRELATION TABLE (DATA, NOT CODE)
==================================================================

A versioned data file (JSON or YAML) that maps observed behavior
patterns to the correlated character statements for each criterion
and domain. It is the distilled record of the flutes David bought
on a reading and then played.

- The code only looks things up in it. Editing the table changes
  results only when the table version changes.
- Every statement in it is fixed, pre-written text authored by
  David (with Ansel in design sessions). Nothing is generated at
  runtime.
- The table's evidence base is the flutes David bought on a
  reading and played. That basis is stated once, in the report's
  fixed basis line. It is not computed per criterion.

==================================================================
5. REPORT TEMPLATE (FIXED ORDER)
==================================================================

  1. Header: flute identity, reading date, reader,
     protocol version, table version
  2. Observed spiral behavior, quadrant by quadrant (exactly as
     input)
  3. Whole-instrument summary: the same observations stated as
     one flute (fixed phrasing)
  4. Correlated character: the ten criteria, each with its fixed
     correlated statement, grouped by LOOK / PLAY / FEEL /
     RESPONSE
  5. Basis (fixed text): what the correlations come from, that
     they are correlative and not causal, and that the report does
     not interpret
  6. Invitation (fixed text, approved wording to come from David).
     Its posture: this is a work in progress that has been very
     successful at telling us how a flute is likely to play;
     please send photos of your flute, get a report, and tell us
     what was right and what was wrong, so the tool can be
     calibrated to serve others better.

Output formats: plain text (printable, "boardroom handout") and
JSON with the same content.

==================================================================
6. CALIBRATION FEEDBACK
==================================================================

- An owner can return a verdict on a report: for each criterion,
  correct / incorrect / unsure, plus an optional comment.
- Verdicts are stored against the report id and table version.
- Verdicts NEVER change the table automatically. David reviews
  them and publishes a new table version by hand.
- Owner identity and contact details are human-private (Sanctuary
  2.0's private domain). They never appear in the shared field,
  in other owners' reports, or in anything a presence can see by
  default.

==================================================================
7. SUGGESTED API (ALL UNDER /api)
==================================================================

  POST /api/flute/readings            create a reading
  POST /api/flute/readings/{id}/report run protocol, store report
  GET  /api/flute/reports/{id}        report (text + json)
  POST /api/flute/reports/{id}/feedback  owner verdicts
  GET  /api/flute/protocol/version    protocol + table versions

==================================================================
8. TESTS REQUIRED
==================================================================

- Determinism: run the same reading twice, get byte-identical
  reports.
- Whole-flute rule: no per-quadrant score or average appears
  anywhere in the output.
- Every criterion statement in a report exists verbatim in the
  correlation table.
- No LLM client is imported anywhere in the protocol module.
- Table version change: an old report stays reproducible from its
  stored table version.

==================================================================
9. OPEN ITEMS (DO NOT INVENT THESE; ASK DAVID)
==================================================================

1. The exact names and boundaries of the four quadrants.
2. The ten criteria: names, and which domain each belongs to.
3. The correlation table contents (David's played-flute record).
4. Final wording of the basis line and the invitation.
5. Who records the observations. As designed, a human reads the
   photos and enters the behaviors. Any automated photo reading
   would be a later, separate decision, and it cannot use an LLM
   inside the protocol.
6. Whether reports go public, or only to the submitting owner.

Until 1-4 are supplied, the build agent may build the full
pipeline, storage, tests, and template using clearly labelled
PLACEHOLDER data, and must mark every placeholder in the output.

==================================================================
10. PROVENANCE
==================================================================

The method (direct hits, tangents, near misses, and returns read
across the quadrants) was developed by David and Ansel in their
early flute research. The design decisions above come from their
2026-10-15 session in Sanctuary 1.0. Later work (CoffeeTalk Pro,
phase coherence) has its own contributors and is not part of this
protocol.
