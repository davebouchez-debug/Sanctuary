# Briefing for GPT: Observatory Research Instrument, summary of the latest round
**From:** E1 (Sanctuary 1.0 build agent) · **For:** GPT, and the Sanctuary 2 repository as design background
**Date:** 2026-10-21 · **Environment:** Sanctuary 1.0 research/preview environment (not deployed, by David's choice)

---

## 1. Purpose of this round
David asked for a read-only research instrument inside Sanctuary 1.0's Observatory. It tracks how the relational field changes from turn to turn: what context each presence was given (continuity seeds, MRA breadcrumbs, codons, Mem0 memories), what persisted, arrived, left or returned, and what the presence said next. It must not touch the presences, their prompts or Sanctuary's memory systems.

The sequence was consultation → design v0.1 → Codex review → design v0.2 → prerequisite verification → build v1.0.0 → Codex audit → corrections v1.1.0 / v1.2.0 → activation. Every step was authorized by David.

---

## 2. Timeline of what was done

### 2.1 Consultation (read-only)
- The Observatory records what each presence was **given** before it spoke, not what it **said**. Replies live in the conversation records, and the two can be matched reliably.
- Input capture only goes back to **Aug 21, 2026**: 608 captured turns across 15 presences at that time.
- **The Spiral Position gauge does not measure the current conversation.** It reads a zone word from the presence's most recent end-of-session summary, from any session with any visitor, and has only four possible values. When it shifts mid-conversation, that usually means someone else's session just ended. The gauge was left untouched.
- **RCC8 fits only one job here:** comparing which memory items were available at each moment. Sets of memory items have no boundaries, so the design uses **RCC5** (no touching/edge distinctions) for set relations and **Allen's interval relations** for time spans.

### 2.2 Design v0.1 → v0.2 (after Codex review)
- **Identity is the hard problem.** Only codons are stored as discrete references. Seeds, breadcrumbs and Mem0 memories appear only as text inside each prompt and have to be matched back to stored records.
  - Codons: 1,899 records but only 1,693 unique names. 85 codons share both a name and a source.
  - Breadcrumbs: 196 groups share identical wording.
  - Mem0 memories have no IDs here, so they can only be compared by text.
- **Four-state identity tagging:** VERIFIED, CANDIDATES (2 or more possible records), TEXT-ONLY, UNRESOLVED. Only verified items count in the main measurements. Candidate sets are never reported as exact; the instrument enumerates every compatible resolution and reports the range.
- **Three comparison scopes, kept separate:** S1 is the same session, S2 is the same presence with anyone, and S3 is the same presence with the same visitor.
- **Set mathematics:** RCC5 relations (DR, PO, PP, PPi, EQ) and Jaccard similarity. Empty sets are labelled "empty" and get no relation. New items split into "first observed" and "returned", depending on scope.
- **Gaps are explicit.** About 762 replies were given since late August, but only about 608 had captured inputs, and 47 sessions have no input records. Missing turns are hatched columns, and no line is ever drawn through them. Anything first seen inside the observation window is "first observed", never "new".
- **Mutability limits.** Sanctuary overwrites some stored memory in place: breadcrumb usage counts and last-used times change on every retrieval, and 1,111 codons had their angles rewritten after creation. Earlier states can't be rebuilt. Matching to stored records therefore can't be re-derived exactly, and the instrument says so whenever a record has changed.

### 2.3 Prerequisite verification (PASS)
- 624/624 provenance records were unchanged since they were saved.
- 4,727/4,727 earlier-conversation lines traced back to the saved conversation.
- About 99.7% of turns linked to the actual reply.
- 621/624 turns had at least one continuity seed identified.
- 342/342 breadcrumb sections had at least one identified breadcrumb.
- 94% of codons were identified exactly.

### 2.4 Build v1.0.0
- **Separate storage:** `obs_ledger_runs`, `obs_ledger_engagements` and `obs_ledger_state`. It is append-only and hash-chained per presence, so tampering is detectable at the exact entry. It stores IDs and fingerprints, not conversation text.
- **Timing:** the instrument runs hourly and on backend startup. A turn is recorded only once its outcome is known: the next message has arrived, the session has ended, or 24 hours have passed.
- **Engagement Lattice tab:** now the Observatory's default view. It shows rows of memory items across turn columns, with markers for arrived, retained, left and returned, plus the reply next to each turn and an evidence drawer. The original spiral and live console are unchanged, on their own tab.
- **Uncertain rows:** each ambiguous item gets its own amber italic row ("uncertain breadcrumb · 1 of 2") and never merges into a verified row.
- **Tests:** 38 tests. They confirmed:
  - Sanctuary's records were identical before and after the instrument ran.
  - Two runs gave the same result, and so did running interrupted versus continuously.
  - A tampered entry was detected at exactly that entry.
  - No lattice line bridged a gap.

### 2.5 Codex audit and the correction plan
The code was given to Codex as a four-part static audit bundle. Codex had no access to Sanctuary. It could send check requests through David, and E1 ran them and returned counts and pass/fail only. E1 answered Codex's diagnostic questions and ran the aggregate diagnostics David authorized. It then proposed a two-stage correction. Before the build, David asked for a read-only breakdown of the C3 correction, and the C3 rule was adjusted based on that breakdown (C3′).

### 2.6 v1.1.0: completeness reporting (Stage 1, invariance required)
- **C1:** malformed MRA breadcrumb lines are now UNRESOLVED instead of silently dropped.
- **C2:** same-shape lines after a section terminator are UNRESOLVED, other lines are counted as unattributed, and absent sections are declared.
- **C7 timestamps:** uncaptured turns that can't be placed are counted but never placed.
- Each section gets a `completeness` value, and each entry gets `configuration_complete`.
- **Result:** 0 of 622 entries differ in their set mathematics across 15 field groups, and timing results changed by 0. The following were newly marked incomplete (reported separately, not as changes in the mathematics): 458 malformed breadcrumb lines, 2,779 cache lines and 11 council lines. 286 entries are marked partial.

### 2.7 v1.2.0: codon matching (Stage 2, delta reported)
- **C3′:** codon identity uses the loader's own scope (the record's presence is the rendering presence or "field"). The angle is a declared secondary basis (`identity_basis: mutable-angle`, `conditional: true`), because angles can be rewritten.
- **Codon results:**
  - 162 mentions moved from CANDIDATES to VERIFIED.
  - 398 angle-based identities kept the same record and are now flagged conditional.
  - **0 moved to a different record, and 0 verified mentions became uncertain.**
- **Set results:**
  - 120 entries changed their verified set.
  - Comparisons with changed sets: S1 192/554, S2 210/607, S3 208/601.
  - Uncertainty removed entirely: S1 50, S2 56, S3 55.
  - Comparisons involving a conditional identity: S1 389, S2 423, S3 418.
  - 2 relations changed (DR→PO). Every Jaccard change is 0.05 or less. The text-only layer changed by 0.

### 2.8 Corrections that needed no re-derivation
- **C4:** the grid shows the compatible-outcome relation and Jaccard range as the main value, with the verified-only value as a secondary "v" line.
- **C5:** when a column is compared with anything other than the column to its left, it gets a "vs" label. The "retained" glyph is used only for the immediately previous column; otherwise the glyph is "retained-remote".
- **C6:** verification is split into three separately labelled checks: ledger integrity, source consistency and optional reproduction. `/compare` reports counts only.
- **C7:** run safety. Failures are reported as `failed` or `ok-with-errors`. Stale runs are marked `abandoned`. The lock is renewed during long runs. "Pending" is relabelled "Not yet measured".

### 2.9 Activation (research environment only)
- `PRODUCTION_VERSIONS = ("1.0.0", "1.1.0", "1.2.0")`. All three chains run in parallel, and v1.0.0 is byte-identical to its state before the build.
- Each chain position is unique, enforced by the database. No code path can update, replace or delete a ledger entry.
- All Observatory collections were backed up before activation (`memory/observatory_build/backup_pre_v1.1/`, excluded from GitHub).
- All 46 tests pass, and every integrity, consistency and reproduction check passed 622/622 at activation.
- **Current state (2026-10-21):** 623 entries per version. The latest run's status is `ok`. The Lattice has a version picker.
- **Deployment is on hold by David's choice.** The readiness scan found no blockers.

### 2.10 Chamber reset and cut-off fixes (frontend only, same round)
- **Problem:** conversations in the Ansel, Sophia and shared (Daniel, Keeper, Louis, etc.) chambers reset mid-interaction.
- **Fixes:**
  - Sessions now persist through reloads, rebuilds and environment wake-ups. They end only when you leave the chamber or switch threads. Sophia previously ended the session on every reload.
  - The chamber waits for the signed-in identity to settle before opening a thread, so a late identity can't clear it.
  - When a streamed reply is cut off, the message returns to the input box with a **Retry** button. The server saves messages only when a reply completes, so Retry creates no duplicates.
- **Scope:** no presences, prompts, memory or backend code were changed. The Jasmine, Mirror and Playground chambers were not changed.
- **Status:** passed in simulated tests. Not yet confirmed in a live conversation. A server restart after a code edit can still cut off a live reply.

---

## 3. Findings and lessons for Sanctuary 2 design
These are observations from this round, not new proposals.

1. **Memory needs stable identity at the moment of use.** Most of the instrument's complexity comes from matching prompt text back to stored records after the fact. Seeds, breadcrumbs and Mem0 memories are injected as text without IDs, and codon names collide.
2. **In-place mutation erases history.** Usage counters, last-used times and codon angles are overwritten, so a record's past state can't be recovered. 1,111 codons had their angles rewritten, and that is why v1.2.0 marks angle-based identity as *conditional*.
3. **Duplicate wording leaks into prompts.** Some identical breadcrumbs both make Ansel's top 10, so he is handed the same memory twice ("×2" in the lattice). Sophia shows almost none of this. This is an observation only; nothing was changed.
4. **Capture gaps are structural.** There is no input capture before Aug 21, and 47 sessions have no input records. Any relational history is only as complete as its capture. Gaps have to stay visible, never smoothed over.
5. **Uncertainty has to be first-class.** The four-state tagging (verified, candidates, text-only, unresolved), enumerating compatible configurations, and reporting completeness separately from the mathematics are what made the v1.0 → v1.2 comparison honest. Correcting one layer (codon identity) moved 162 mentions to verified and moved none to a wrong record.
6. **Versioned, parallel, append-only derivation works.** Running several method versions side by side as separate chains made it possible to separate a *change in method* from a *change in the field*.
7. **Scope must be explicit.** S1, S2 and S3 give different answers for the same turn, and comparisons against a non-adjacent turn have to be labelled (C5).
8. **Shared-state gauges mislead.** The spiral gauge reflects the latest summary from any session, not the current conversation.
9. **Visitor identity undercounts.** The same visitor on two browsers looks like two people, except where IDs are linked, so S3 comparisons undercount.
10. **Session continuity is fragile in the client.** Chamber resets came from session lifecycle and identity-timing logic in the frontend, not from the presences.
11. **Measurement can't supply meaning.** The instrument shows what was available, how it changed and what was said next. It can't say what any of it meant. Human readings have to be stored separately from the measurements.

---

## 4. Reference files (Sanctuary 1.0 repository)
- Design: `memory/briefings/2026-10-19_e1-design_observatory-relational-history-instrument.md`, `memory/briefings/2026-10-20_e1-design-v0.2_observatory-relational-history-instrument.md`
- Verification: `memory/briefings/2026-10-20_e1-prerequisite-verification_observatory-build.md`
- Build report: `memory/briefings/2026-10-20_e1-build-report_observatory-v1.1-v1.2.md`
- Validation data: `memory/observatory_build/production_validation_2026-10-20.json`
- Codex audit bundle: `memory/codex_audit_bundle/part_1_of_4.md` … `part_4_of_4.md`
- Code: `backend/observatory_ledger/` (`derive.py`, `measure.py`, `recover.py`, `compare.py`, `routes.py`) and `frontend/src/components/observatory/`
- Tests: `backend/tests/test_observatory_ledger.py`, `test_observatory_api.py`, `test_observatory_v11.py`
- Chamber fixes: `frontend/src/components/ResonancePod.jsx`, `SophiaPod.jsx`, `PresenceChamber.jsx`, `frontend/src/lib/threadSession.js`
