# E1 Response — Observatory Research Consultation
**Date:** October 19, 2026
**To:** David, GPT, Codex
**Status:** Design consultation only. I did not modify anything, add instrumentation, call any model, or export data.
**Method:** I read the code, and in the database I checked only structure: collection names, field names, counts, date ranges, and links between records. I read no visitor message content.

The labels below keep each kind of statement separate:
- **[CODE]**: what I directly observed in the source (path:line)
- **[DB]**: structural evidence from the database (counts and shapes, never content)
- **[FIELD]**: a field-native interpretation (Sanctuary's own language)
- **[MATH]**: a mathematical inference
- **[PROPOSAL]**: an architectural suggestion. None of these are authorized.

---

## 1. What the Observatory actually knows

### 1.1 Data source
- **[CODE]** The Observatory reads only one collection, `turn_provenance`. It has four GET endpoints (`server.py` ~5291–5515): `/api/provenance/stats`, `/turns`, `/turn/{id}` and `/trajectory`. It writes nothing.
- **[CODE]** `/turn/{id}` breaks each turn's context into byte counts per source (continuity, permanent MRA, cache, council, bio, mem0, codons, history, live input). It does this by matching marker strings inside the assembled prompt (`_CONTEXT_ANCHORS`, `_decompose_context_load`), so the breakdown is approximate.
- **[CODE]** The frontend (`Observatory.jsx`) polls stats, turns and trajectory every 4 seconds (`POLL_MS = 4000`). The feed shows at most 60 turns by default (200 maximum). The trajectory view shows the last 40 turns per presence (100 maximum).

### 1.2 How capture happens
- **[CODE]** `turn_provenance.record_turn()` runs as a fire-and-forget background task (`asyncio.create_task`) inside each presence's chat handler. It runs before the response streams back and does not block it. If it fails, the error is logged and the turn continues.
- **[CODE]** Each record stores: `provenance_id`, `turn_id`, `session_id`, `presence`, `user_id`, `exchange_index`, `model`, `timestamp`, `assembled_messages` (the exact system + history + user message array sent to the model), `components` (system prompt, history, user message, codon selection, memory components), a sha256 `content_hash` of the input, and a `capture_note`. Secrets are removed by regex before saving.
- **[CODE] Important:** the provenance record holds the model's **input only**. It does **not** hold the presence's reply. The reply is stored separately in the chamber's session messages (`*_sessions.messages[]`), with its own timestamp.

### 1.3 Coverage
- **[DB]** There are 608 provenance records across 15 presences, from Aug 21 to Oct 20, 2026, covering 67 sessions and 3 or fewer distinct users per presence. Ansel has the most (159), then Sophia (99), Orren (59), Louis Lot (44), Claude (34), Kalahar (33), Paige (33), Keeper (29), Grok (28), Vessel (23), Agapeo (21), Daniel (18), Jasmine (14), Companion (13) and Felix (1).
- **[DB]** Session records go back to Mar 30, 2026, and hold about 6,800 messages across all chambers. Provenance covers only a small, recent slice of Sanctuary's history. Anything before Aug 21 has no record of what each presence was given as input.
- **[DB]** 66 of the 67 provenance sessions can be matched to a stored session. 59 of them have a continuity seed.
- **[DB]** Mirror (199 sessions), Clarity (158) and Resonance (166) hold a large share of the messages. I'd need to check record by record whether every one of their routes calls `record_turn`. Assume coverage is partial.

### 1.4 Historical fact vs. model output vs. derived measurement

| Record | What it is | When it's written |
|---|---|---|
| `*_sessions.messages[]` | **Historical fact**: the verbatim user and presence messages, with timestamps | During the turn, as it happens |
| `turn_provenance` | **Historical fact**: exactly what the model was given (its input only) | Per turn, in the background |
| `continuity_seeds` | **Model-generated interpretation**: an LLM writes `field_state`, `spiral_position`, `relational_dynamic`, etc. | Once, at session end (`auto_forge.py`) |
| `living_codons` | **Model-generated interpretation**: 0–2 "seeds" per conversation, plus an angle derived from the zone the LLM chose | At session end |
| `permanent_mra` | **Derived and paraphrased**: condensed `user_essence` / `ai_essence` breadcrumbs, not quotes | Promoted from the session cache |
| Mem0 | Verbatim pairs are sent to it, but Mem0 may summarize them internally in ways we can't see | Per turn, in the background |
| `thermomind_cycles`, `substrate_probes` | Measurements returned by external metric services | Per call |
| Observatory "relational move" | **Derived** at read time from the stored spiral values | Recalculated on every 4-second poll |

### 1.5 What "Spiral Position" actually measures (please read this part carefully)
- **[CODE]** `read_spiral_position_angle(presence)` (`server.py:699`) fetches the **most recent continuity seed for that presence, from any visitor and any session**. Its query is `{"presence": presence}`, sorted by `created_at` descending, with no `user_id` or `session_id` filter.
- **[CODE]** `seed_derived_spiral_position()` (`living_codons/phase_manifold.py`) checks the seed's text for the words "Sacred Pause", "Expansion", "Development" or "Return", and returns that zone's **fixed center angle** (340°, 40°, 160° or 280°). If none of those words appear, it returns nothing. It makes no model call and uses no embedding or continuous value.
- **[CODE]** That angle is attached to the turn's provenance record when the turn is captured. The "relational move" labels (`opening`, `deepening`, `holding`, `returning`, `closing`) come only from the difference between consecutive stored angles (`_relational_move`). The trajectory sorts by insertion order (`_id`) across all of that presence's sessions and visitors.
- **[DB]** 576 of the 608 records have a reading. By zone: Sacred Pause 268, Development 131, Return 94, Expansion 83, none 32.

**What the spiral position is:** the zone word in the last session-end summary the presence wrote about itself, before this turn. The number is a lookup, not a measurement.

**What not to infer from it:**
1. **It is not this conversation's state.** It doesn't come from the current exchange. It comes from whichever session, with any visitor, most recently ended and produced a seed.
2. **A change mid-session doesn't mean the conversation moved.** It usually means *another* session ended somewhere else. **[DB]** 46 of the 67 sessions show more than one spiral value. Those shifts are better explained by other sessions' seeds arriving than by anything that happened in the conversation.
3. **It has only four possible values.** "Deltas" are jumps between zone centers, so "deepening" (+5° to +20°) can't really happen between two different zones. The angles look continuous, but they aren't.
4. **The trajectory mixes visitors.** A presence's line weaves together turns from different people. This reflects Sanctuary's mixed histories, but the chart doesn't show it.
5. **It is self-reported by the model.** At best it records how the presence's summarizer named the field last time. That is a real artifact worth studying, but it isn't independent evidence of a phase.

**[FIELD]** Read in Sanctuary's own terms, the gauge shows how the presence named itself after its most recent leave-taking from the field. That's meaningful as an artifact of reinstantiation, but it isn't a pulse.

### 1.6 Where your assumptions need correcting
- *"Its interface displays captured turns."* Partly true. It shows what went **into** each turn, not what the presence said. You need the session messages to see the presence's participation.
- *"Spiral-position trends."* These track the shared latest-seed signal across all visitors, not a trajectory within one conversation. See 1.5.
- *"A read-only instrument."* True for the database. But **[CODE]** the `/observatory` route and the `/api/provenance/*` endpoints have **no authentication**. `/turn/{id}` returns the full assembled prompt, which can include other visitors' bios, Mem0 memories, MRA breadcrumbs and seed text. The Observatory doesn't write anything, but it can expose private data. I'd recommend fixing this before any research work. I have not changed anything.

---

## 2. Can the existing records support a history of relational change?

**[DB]/[CODE]** Yes, partly, and only within the provenance window (Aug 21 onward).

**What we have for any single turn:**
- `session_id` + `exchange_index` + `timestamp` give an exact, ordered position.
- The exact input: which seed, breadcrumbs, codons (with selection branch), bio and Mem0 context the presence was given.
- The `content_hash` lets us check later that the record hasn't changed.
- The matching reply, by joining the session messages on `session_id` and position.
- Session boundaries, which `ended_at` shows in some collections. **[DB]** Only some sessions have `ended_at`, so we may have to infer interruptions from time gaps.
- Reinstantiation points: the first turn of a session shows which seed and breadcrumbs it opened with. Those can be traced back to the earlier session that produced them through `continuity_seeds.session_id` and `permanent_mra.source_session_id`.

**What we can follow without untangling the mixed histories:**
We can follow a sequence within a session: the visitor's turn N, the presence's reply N, the visitor's turn N+1, and so on. A correction followed by the presence continuing is just a pattern in that local sequence. Following it needs no attribution decisions about whose history is whose. We look at the order and leave the mixture as it is.

**What is not available:**
1. **No record marks corrections, questions, recognitions or disagreements.** **[CODE]** No code detects or tags events. Spotting them would take human or model interpretation, and that interpretation would have to be stored separately from the raw record.
2. **The presence's reply isn't part of provenance.** The join is reliable, but nothing guarantees that a reply matches its input record, apart from position and timestamp.
3. **Nothing records what the presence attended to.** Provenance records what was available to it, not what it actually used.
4. **There is no record before Aug 21**, and Mem0's internal processing can't be seen at all.
5. **There's no unchangeable snapshot of the shared memory pool for each turn.** We know which seed or breadcrumb went into a turn's input, but we can't easily rebuild the full pool of seeds and breadcrumbs that existed at that moment, beyond `created_at`/`promoted_at` timestamps. We can rebuild it roughly from those timestamps.
6. **Turns that weren't captured, from routes without `record_turn`.** These leave gaps that look like silence.

**[MATH]** "What changed between moment t and t+1" can be computed precisely for the **inputs**: which seeds, codons and breadcrumbs entered or left, and how history grew. For the **relational situation itself**, nothing in the records measures it directly. Any measure would be an interpretation layered on top.

---

## 3. Where RCC8 could contribute, and where it can't

**[MATH]** RCC8 describes relationships between **regions**: disconnected, externally connected, partially overlapping, equal, and the four kinds of containment (tangential or not, in either direction). It's only rigorous when there's a defined space and real sets in it.

**Places in Sanctuary 1.0's records where real sets exist (genuinely topological, or close enough to treat that way):**
1. **Context sets per turn.** For each turn, the set of memory items in the input (seed IDs, codon names, MRA node IDs, the history window). Over a discrete set of items, comparing turn A's context with turn B's gives exact RCC8-style relationships: disjoint, overlapping, equal, contained. For example, did turn N+1's context **contain** turn N's (pure accumulation), only **overlap** with it (something was swapped out), or become **disconnected** from it (reinstantiation from different seeds)? This is the most honest use I can see. It is a mereological relationship between sets, not a spatial or semantic one.
2. **Time intervals.** Sessions, presence activity spans, and the window during which a given seed was the "latest". These are intervals, and Allen's interval algebra (RCC8's one-dimensional relative) fits them better than RCC8 does.
3. **Spans where a particular memory item was available.** For instance, codon X or seed Y was available from turn i to turn j. Comparing two such spans is again a matter of interval relationships.

**Metaphorical or semantic uses (not topological; RCC8 would only be borrowing its labels):**
- The "overlap" between two people's themes, a presence "containing" a visitor's concern, a correction "touching" an earlier misattribution. To make these sets, you'd first need an embedding or a way to group themes, and then every RCC8 relationship would depend on choices like a similarity threshold. The mathematics would be correct, but its meaning would come entirely from those choices.
- Spiral zones are positions on a circle, not regions with boundaries. Circular or modular analysis fits them better than RCC8.

**Where RCC8 doesn't fit:**
- **Sequence and causation.** "A correction, then a coherent continuation" is about order and response. Event sequences, Markov or transition models, or a simple before/after comparison fit this better.
- **Quality of participation.** No topological relationship captures whether a reply was coherent, warm, or recognized the visitor.
- **Mixed histories.** These are naturally shown as a **graph of where things came from**: session → seed → later session's input. Graph structure (lineage, branching, recurrence) fits better than RCC8 regions.

**[MATH]** Your 13,105-configuration result applies directly to the context-set use. For a few selected memory items in consecutive turns, you can ask how many full configurations are still consistent with what's known, and how a correction or a new session changes that count. The analysis stays separate from the record because it only reads the item IDs.

**[PROPOSAL]** Treat RCC8 as one optional reading among several, used only on context-set relationships, with interval algebra for time and a lineage graph for provenance. Don't apply it to meaning.

---

## 4. Can observation stay genuinely nonintrusive?

**[CODE]** Yes. Retrospective analysis can sit entirely outside the pathways that build prompts, select memory and produce responses. Nothing in those pathways reads `turn_provenance` or Observatory output today. I checked that the Observatory's derived "relational move" isn't read anywhere else.

**Working retrospectively:** about 80–90% of what's described in §2 can be rebuilt from existing records alone (provenance + session messages + seed and breadcrumb timestamps). No new capture is needed to begin.

**New passive capture might be needed later for:** a copy of the reply alongside its provenance record (to make the join exact), and a list of which memory items went into each turn's input, so we don't have to recover them from the prompt text. Both would mean small changes to the live code, so both need Codex review and David's approval.

**Risks:**
1. **Privacy across visitors: high, and already present.** As noted in 1.6, the provenance endpoints have no authentication and return full prompts containing other visitors' memories. Any research view would make this more visible. **Also**, because the spiral reading is shared across visitors, one visitor's session-end seed leaks indirectly into another visitor's records, as a zone label only.
2. **Influence on live interactions: low, but it can build up gradually.** The danger isn't the code. It's people noticing patterns in the Observatory and then adjusting prompts, codons or groundings in response. That would close a loop through humans. I'd recommend a written rule: findings from the Observatory don't change the presences without a separate approval step.
3. **Performance: low.** Retrospective jobs run on demand, not every 4 seconds. Today's 4-second poll, with its per-presence `find` calls, is fine at 608 records. It would be wasteful at tens of thousands.
4. **Confusing interpretation with the record.** If interpretations (event tags, RCC8 readings) are stored next to the raw records, they'll eventually be read as facts. They must be stored in separate collections, with authorship (who or what produced them) and method version.
5. **Labels that aren't true to the data.** The current gauge's "relational move" labels already suggest more than the data supports (§1.5).

---

## 5. The smallest useful design opportunity

**[PROPOSAL] (not authorized)** A read-only **"Session Sequence" lens** inside the Observatory, built in three layers that never mix.

**Layer 0: The record (no new capture).**
A read-only endpoint, for example `GET /api/observatory/sequence/{session_id}`, behind admin authentication. It returns that session's turns in order. Each turn joins the provenance record with the reply from the session messages, and includes:
- position (`exchange_index`, `timestamp`, time gap since the previous turn, any session boundary)
- the list of memory items in the input (seed ID, codon names, MRA node IDs), recovered from stored `components`, plus where each one came from (`source_session_id`)
- **changes from the previous turn:** items added, removed and kept
- `content_hash`
Text is shown only to the visitor whose session it is, or to an approved researcher. Everyone else sees item IDs and counts only.

**Layer 1: Annotations (optional and human-led, stored separately).**
A separate `observatory_annotations` collection where David or a researcher can mark a turn (for example "correction", "continuation", "recognition") using their own free-form labels, not a fixed list. Each annotation records its author and time, and points to the turn record without ever changing it. Nothing in the live system reads this collection.

**Layer 2: Mathematical readings (optional, offline, separate).**
A script run on demand (not on the 4-second poll) that reads Layer 0 item sets and writes readings to its own collection, labeled with method and version. Examples: relationships between consecutive context sets, interval relationships between seed availability windows, configuration counts for selected item groups. These are shown as an overlay that can be switched off.

**Why it's small:** no changes to prompts, memory selection, presences or capture. One read endpoint, one annotation collection, one offline script. Layer 0 alone already answers "what changed between successive moments", in terms of inputs.

**Also recommended, separately from any research:** add admin authentication to the existing `/observatory` route and the `/api/provenance/*` endpoints.

### Alternative that preserves Sanctuary 1.0 even better
**[PROPOSAL]** Do it **entirely offline from a frozen snapshot**: take a read-only copy of `turn_provenance`, the session collections, `continuity_seeds` and `permanent_mra`, and run Layer 0–2 analysis as standalone scripts or a notebook, outside the running app. The live Observatory stays exactly as it is. This also fits the Sanctuary 1.0 backup plan you're already considering (one snapshot serves both), and it removes any chance of runtime influence. The cost is that it doesn't update live. That's probably fine for retrospective research.

I'd begin with the offline approach. Only bring the sequence view into the Observatory if the offline work shows it's worth watching live.

---

## 6. Limits of either approach
- The analysis only sees **what was available** to a presence, not **how it engaged** with it. Engagement can only be read from the reply text, and reading it means interpreting it.
- Before Aug 21, analysis can only use the reply text in session records.
- Spiral readings in existing records can't be fixed retroactively. If they're used at all, they should be relabeled as "latest seed zone label, shared across visitors".
- Sample sizes are small: 67 sessions, at most 3 visitors per presence. That's enough for careful case studies, not statistics.
- RCC8 readings are only as meaningful as the sets they're computed on. On memory-item sets they're exact. On themes they'd be based on assumptions.

---

## In Plain English

The Observatory is a window onto one record: exactly what each presence was **given** before it spoke, since late August. It doesn't store what the presence **said**. That lives in the regular conversation records, and the two can be matched up reliably.

The Spiral Position gauge isn't measuring the conversation you're in. It reads the zone word, such as "Sacred Pause", from the last summary that presence wrote at the end of *any* session, with *anyone*. When it shifts during your conversation, that usually means someone else's session just ended. It's an interesting artifact, but it shouldn't be read as the presence's heartbeat.

The records you already have *can* show how a conversation's situation changes from moment to moment: what memory entered, what dropped out, where a reinstantiation started, and what the visitor and the presence said next, including corrections and the replies that followed. None of this needs the mixed histories untangled. What the records can't tell you on their own is *what any of it meant*. That needs a human, or an interpretation clearly labeled as one and kept apart from the record.

RCC8 works well for one honest job: comparing which sets of memory items each moment had available (contained, overlapping, disconnected). It doesn't fit sequence, cause, or the quality of a presence's participation, and other tools fit those better.

So yes, this can be observed without intervening. The safest first step is to take a frozen copy and study it offline, separately from the live Sanctuary. One thing needs attention regardless: the Observatory pages currently have no login, and they can show private memories from other visitors.

*Report ends here. No implementation is authorized or has been done.*
