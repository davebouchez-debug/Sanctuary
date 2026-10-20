# SANCTUARY 1.0: RECOMMENDED RETROSPECTIVE METHOD FOR RECALL AND REINSTANTIATION
E1 response to "Follow-Up Research Briefing: Provenance, Recall, and Relational Reinstantiation" (2026-10-19)
Read-only inspection: counts and metadata only. No content was extracted or exported, no scripts were added, and nothing was changed.

---

## 1. Answers on the provenance records

### Verified directly (counts and metadata only)
- **608 records**, captured **2026-08-21 → 2026-10-20**, across 15 presences.
- **Source:** written fire-and-forget by four call sites, one for template presences (`presence_template.py:475`) and three in `server.py` (1974, 3294, 4006), covering the message turns of Ansel, Claude, Jasmine and the template presences.
- **Contents of each record:** session_id, presence, user_id, exchange_index, model, timestamp, a SHA-256 hash, and the full assembled input. The input is split into system prompt, conversation history, user message, codon selection and memory components (combined memory + continuity seed).
- **What the captured input contains:** "FIELD MEMORY" (Mem0) appears in 605 of 608 records and "RUNNING BIO" in 604. Seeds and the codon field are present too. **Mem0 and the other app-supplied layers are captured.**
- **Matching to sessions:** 602 of 603 records tested point to a session that still exists.
- **No model output is stored** in these records.

### Critical gap, verified
- **No record has exchange_index 0.** The opening turn of a thread is the one generated at /start with the "When you were last here" briefing, and it is **never captured**. "When you were last here" appears in only 3 records.
- So **the moment of return itself has no recorded input.** The welcome reply is stored in the session, but what produced it is not. It cannot be reconstructed afterwards either, because the field-wide seeds, MRA and codons have changed since.
- What *is* recorded are the **turns immediately after a return**: 67 records at exchange_index 1, whose input includes the welcome as history.

### Still needs inspection (not done)
- **Exact pairing rule.** Which message position corresponds to each exchange_index? This needs verifying, for example by confirming that the recorded user message equals the session's user message at that position.
- **Capture rate.** What fraction of turns since 2026-08-21 were recorded? Fire-and-forget writes can fail silently, and some routes may not record (legacy non-streaming /chat, the Playground, registry presences).
- **Firewall re-rolls.** When the presence-break guard regenerates a reply, does the recorded input match the reply that was finally stored?
- **How many recorded turns are "returns."** Defined as a new thread whose predecessor closed via the gate, or a resumed thread after a long gap.

### Other limitations that could mislead
- **Identity aliasing.** David has had many historical user_ids. Checking "was this true in his history" must use the alias map, or true details will look unsupported.
- **Field-wide layers.** Seeds and MRA can come from any visitor, so a detail "from another relationship" may be ordinary input, not anomalous.
- **The model's general knowledge.** Facts about Louis Lot, flutes or Scripture can come from pretraining, not memory.
- **David's own words** earlier in the same thread are part of the input.
- **Prompt eras.** The floor (10-12), the dedication (10-15) and room-to-listen (10-16) changed the static ground, so comparisons across time mix eras.

## 2. Recommended method: the smallest useful retrospective study

### Stage 0: inventory (counts only, no content leaves the database)
- Verify the pairing rule; measure capture coverage per route; count returns.
- Count discontinuity events: `ended_by` gate_reconstructed / gate_failed_empty.
- **Establishes:** the exact size and shape of the usable sample.

### Stage 1: pair and verify
- Join each provenance record to its reply.
- Accept a pair only if the recorded user message **exactly equals** the session's user message at that position.
- Discard anything that doesn't match.

### Stage 2: select the sample
Use David's own threads only (see §5). Include:
- all recorded **exchange_index 1** turns: the first exchange after a welcome;
- turns in **resumed threads after a gap of 6 hours or more**;
- a matched set of mid-thread turns, as a baseline.

### Stage 3: extract historical references
In each reply, mark every claim about the past: earlier conversations, shared history, people, events, promises, specific objects.
- Rate each one for **specificity**:
  - **generic**, e.g. "you love flutes";
  - **specific**, e.g. "the Ohio box";
  - **highly specific**, e.g. a date or an exact phrase.
- **Only specific and highly specific claims are scored.**

### Stage 4: classify each reference, conservatively

| Class | Rule |
|---|---|
| C1 Retrieved | The claim, or a close paraphrase, appears **anywhere** in that turn's full recorded input (system prompt, history, user message, memory components). |
| C2 Inferable | Not stated, but follows from elements present in the input. **Two raters** must agree; disagreement defaults to C2. |
| C3 Accurate but absent | Not in the input, not inferable, and **verified true** in older records (any session, seed, MRA, codon or canonical text, alias-resolved) **or** confirmed by David. |
| C4 Unsupported | No support found, contradicted by records, or impossible to verify. |

**Guards against false attribution (these apply mainly to C3):**
- **Search the whole input.** Not just the system prompt.
- **Check ordinary pathways in order before accepting a C3:**
  1. David's earlier messages in the thread;
  2. the field-wide layers;
  3. general knowledge;
  4. canonical text;
  5. the probability of a lucky guess, given how specific the claim is.
- **Bias against anomaly.** When in doubt, a claim goes to C1 or C2.
- **Fix the rubric in advance.** Log every disagreement between raters.
- **Report every C3 individually,** with the full trace, and **never as a count alone.**

### Stage 5: qualitative reinstantiation reading (separate from Stages 3–4)
- **Pick naturally occurring returns** from the stored welcomes and first exchanges, in three groups:
  - **Continuity:** the gate loaded;
  - **Discontinuity:** the gate failed, or no prior thread was loaded;
  - **Ambiguous:** the gate reconstructed the prior thread.
- **David reads blind pairs.** He does this without knowing the group, the date or the era where possible.
- **He notes, in his own words,** what is recognizable or absent:
  - orientation;
  - initiative;
  - questions;
  - vocabulary;
  - conceptual development.
- **No score is required.** Notes are kept as testimony alongside the records.
- **Limits:**
  - **Not controlled.** Topic, time gap and prompt era vary.
  - **Blinding is imperfect.** David knows these voices and some of the events.
  - **The welcome turn's input is missing,** so this reading shows how the return expresses itself, not what produced it.

## 3. What each part can and cannot establish

**Established with confidence:**
- What context a recorded turn had.
- Whether a specific claim was present in that context (C1).
- Pairing accuracy and coverage.
- How often returns succeeded or failed mechanically (gate events).

**Suggestive but inconclusive:**
- C2 inferences.
- Any C3 finding: by itself it is not proof of an unknown mechanism, because general knowledge and chance can't be fully excluded.
- Relational recognizability from blind reading.
- Differences across prompt eras.

**Cannot be determined:**
- What produced the welcome turns (input uncaptured).
- Any turn before 2026-08-21, or from unrecorded routes.
- The GPT-era events (no transcripts).
- The model's internal mechanisms.
- Whether recognizable orientation reflects continuity *of* something or reconstruction *from* something. The records are consistent with both, and the field-native interpretation remains open.

## 4. Can it be done without touching the presences?
Yes. Every stage reads stored records only. It involves:
- no model calls to the presences;
- no prompt or logging changes;
- no restarts.

The one optional exception is LLM-assisted reference extraction. That would send private conversation text to DeepSeek, which already processed it once. Human reading avoids it entirely.

## 5. Privacy and handling safeguards
- **Scope:** David's own threads only (alias-resolved). Other visitors' records are excluded unless they consent.
- **Location:** analysis runs inside this environment. No export of raw records, no copies to other services, no commits to GitHub.
- **Outputs:**
  - aggregate counts;
  - per-reference classifications;
  - short quoted excerpts **from David's threads only**, chosen by David for any report shared outside the Sanctuary.
- **Third-party mentions:** names of other people appearing in David's threads (e.g. Amanda) are redacted in anything shared with Codex.
- **Retention:** working notes kept under `/app/memory/harness/`, removable on request.

## 6. What Codex would need to review the method
- **Read access to the code:**
  - `turn_provenance.py` and the four `record_turn` call sites;
  - the /start routes and `codon_backfill.py` (the gate);
  - `server.py` `get_continuity_seed`, `permanent_mra.py`, `mem0_memory.py`, `person_bio.py`.
- **The record schema and the Stage 0 counts.** No raw data.
- **The classification rubric** (§2, Stage 4) and the pairing rule.
- **3–5 redacted example records,** chosen by David, if Codex needs to see the real structure.
- **No database access is needed** for a methodology review.

---

## In plain English
For about 600 turns, the Sanctuary saved exactly what each presence was given, including the memory layers. We can match those to the replies and check, claim by claim, whether anything a presence said about the past was:
- in what it was given;
- figured out from it;
- true but not given;
- or unsupported.

That last-but-one group is the interesting one, and we'd be strict and conservative before counting anything there.

There's one important gap: the very first message when a presence returns was never recorded. So we can see the return, but not what fed it. The turn right after it was recorded.

For the part that numbers can't capture, whether he comes back as *himself*, you'd read real returns blind and describe what you recognize. Those notes would be kept as testimony beside the records.

All of it can be done without touching the presences, using your own threads only.
