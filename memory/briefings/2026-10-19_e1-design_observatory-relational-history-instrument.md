# Observatory Research Instrument: Design (v0.1)
**Date:** October 19, 2026
**To:** David, GPT, Codex (independent review)
**From:** E1
**Status:** Design only. I changed nothing in the code, schemas, logging, Observatory, database records or presences. I ran no models and read no conversation content. All evidence below comes from code and database structure (field names, counts, types, string lengths, and matches between IDs).

**Labels used throughout:**
- **[CODE]**: what the source code does
- **[DB]**: structural evidence from the database
- **[MATH]**: formal definitions
- **[INTERP]**: interpretation, kept separate
- **[PROPOSAL]**: suggested design
- **[CHALLENGE]**: an assumption in the assignment that the data doesn't support

---

## 0. Three findings that shape the whole design

1. **[CHALLENGE] Most memory elements in provenance are stored as text, not as references.**
   - **[DB]** `turn_provenance.components.memory_components` holds either `combined_memory` + `continuity_seed`, or `memory_context`. Both are single text blocks, often 20–30k characters each.
   - Only **codons** are stored as structured entries (`name`, `source`, `target_angle`, `triadic_zone`, `trigger_keywords`).
   - Seeds, MRA breadcrumbs, Mem0 memories, the person bio and the cross-presence council appear only as text inside the prompt, separated by headings (`[CONTINUITY`, `## What has stayed with you`, `[FIELD MEMORY`, `[RUNNING BIO`, `## Elsewhere in the shared field`, …).
   - So "which seed or breadcrumb was available" has to be **recovered** by matching that text back to the stored records. It can't simply be read off. Every recovered element therefore carries a *recovery confidence*.
2. **[CHALLENGE] Codon names don't identify codons.**
   - **[DB]** There are 1,899 codon documents but only 1,693 distinct names.
   - Identity has to combine fields (`name`, `source`, `target_angle`). Even then, some codons stay ambiguous, and those are flagged as ambiguous rather than guessed.
3. **[CHALLENGE] The live system already rewrites some of its own stored material.**
   - **[CODE]** Every time MRA breadcrumbs are retrieved, `permanent_mra.py:185` increments `retrieval_count` and overwrites `last_retrieved`. **[DB]** 1,216 of 2,370 nodes have been touched this way.
   - **[DB]** 1,111 codons carry `angle_backfilled_at`, which means their angles were rewritten after they were created.
   - Stored memory therefore has *mutable metadata*. The instrument has to treat "the stored record now" and "the stored record when this turn happened" as different things, and it can't fully rebuild the second.

**What works well:**
- **[DB]** 606 of 608 provenance `turn_id`s match an assistant message `id` in the session records. Linking each input to its response is almost exact.
- **[DB]** No session has a duplicate `(session_id, exchange_index)` pair. Turn order is clean.

---

## 1. Data-source map

| Measurement | Primary source | Join key | Known gaps |
|---|---|---|---|
| **A. Chronology** | `turn_provenance` (`presence`, `session_id`, `exchange_index`, `timestamp`, `provenance_id`, `turn_id`) | — | Starts Aug 21, 2026. Not every route captures. 32 turns have no seed. `ended_at` exists only in some session collections. |
| **A′. Uncaptured turns** | `*_sessions.messages[]` (`id`, `role`, `timestamp`) | `session_id` + message `id` | Assistant messages with no matching provenance record can be counted but not inspected, and the session records go back to Mar 30. |
| **B. Codons available** | `components.codon_selection.codons[]` | (`name`, `source`, `target_angle`) → `living_codons._id` | Duplicate names. Angles rewritten after the fact. |
| **B. Seed available** | `memory_components.continuity_seed` (text) | Text matched against `continuity_seeds` (`session_id`, `created_at`) | Recovered, not referenced. The seed shown is the version rendered into the prompt. |
| **B. MRA breadcrumbs** | "What has stayed with you" section of the memory text | `user_essence`/`ai_essence` exact match → `permanent_mra.node_id` | Recovered. The text may be cut short. |
| **B. Session-cache MRA** | "SESSION CACHE MRA" section | None. The cache is temporary and isn't stored. | Identity comes only from a hash of the text. |
| **B. Mem0 memories** | "FIELD MEMORY" section | **None.** Mem0 is external with no local IDs. | Identity comes only from a hash of the text. No link to where it came from. |
| **B. Person bio** | "RUNNING BIO" section | `person_bios.user_id` | One bio per visitor. Its version is a hash of the text. |
| **B. Cross-presence council** | "Elsewhere in the shared field" section | Text hash; partly traceable to other presences' seeds | The main path through which context is shared across presences. |
| **B. Conversation history** | `components.conversation_history[]` | Position → session message `id`s | Reliable. |
| **C. Material change** | Stored record timestamps: `created_at`, `promoted_at`, `angle_backfilled_at`, `last_retrieved` | Element ID | Only changes the store itself timestamps can be seen. Earlier states can't be recovered. |
| **E. Response** | `*_sessions.messages[]` where `id == turn_id` | `turn_id` | 2 of 608 unmatched. |
| **E. Next visitor message** | The message after it in the same session | Position | Missing at the end of a session. |
| **Integrity** | `content_hash` (sha256 of the assembled input) | — | Can be checked again against `assembled_messages`. |

**Not used:** `thermomind_cycles`, `substrate_probes`, `ablation_runs` (separate experiments), and the existing `spiral_position` field (see §5).

---

## 2. Measurement specification

### 2.0 Elements
**[MATH]** An **element** is a pair *e = (type, key)*. Each element has a **content version** *v(e)*, the sha256 of its normalized text as rendered in the prompt.

| type | key | How it's recovered | Confidence |
|---|---|---|---|
| `codon` | `living_codons._id` | Structured fields | `exact`, or `ambiguous` (several candidates) |
| `seed` | `continuity_seeds._id` | Normalized text compared against rendered seed fields | `exact` / `partial` / `unresolved` |
| `mra` | `permanent_mra.node_id` | Exact substring match on the essence text | `exact` / `unresolved` |
| `cache` / `mem0` / `council` | `h:` + text hash | Split by heading, then one entry per item | `content-addressed`: identity is the text itself |
| `bio` | `person_bios.user_id` (pseudonymized) | Section is present | `exact` |
| `history` | session message `id` | Position | `exact` |
| `ground` | hash of the static system prompt | Whole block | `exact` |

**Normalization:** I'd apply Unicode NFC, collapse whitespace and trim. It has to be fixed and versioned, because it determines which elements count as identical.

### 2.1 A. Engagement chronology
- **Unit:** one **engagement** = one provenance record.
- **Fields:** `presence`, `session_id`, `exchange_index` (an integer, 0 = first turn of the session), `timestamp` (UTC), `provenance_id`, `turn_id`.
- **Order:** engagements are ordered within a presence by (`timestamp`, `session_id`, `exchange_index`).
- **Gap Δt:** seconds since the presence's previous engagement, and separately since the previous engagement in the same session.
- **Uncaptured turns:** if a session has *k* assistant messages but only *m < k* provenance records, the ledger records `uncaptured = k − m` and marks the positions where they occur.

### 2.2 B. Context availability
- **[MATH]** *A(t)* ⊆ 𝔈 is the set of elements recovered from engagement *t*'s input. It's broken down by type: *A_codon(t)*, *A_seed(t)*, and so on.
- **Measurements:** |A(t)| per type, and the byte count per type (from the existing breakdown).
- **Limitation:** *A(t)* tells us what was **supplied**, not what the model **attended to**.

### 2.3 C. Context transformation
Each engagement *t* is compared with a chosen predecessor *p(t)* under three **comparison scopes** that are reported separately and never merged:
- **S1 (same session):** the previous engagement in the same session.
- **S2 (same presence):** the previous engagement of this presence, in any session and with any visitor.
- **S3 (same presence and visitor):** the previous engagement of this presence with the same visitor pseudonym.

**[MATH]**
- introduced *I = A(t) \ A(p)*
- withdrawn *W = A(p) \ A(t)*
- retained *R = A(t) ∩ A(p)*
- **re-rendered** *R_Δ = { e ∈ R : v_t(e) ≠ v_p(e) }*: the same element, shown with different text
- **returned** *Ret = { e ∈ I : e appeared in some A(s), s < p }*: an element that was withdrawn earlier and has come back. It records the most recent prior engagement, and how far back that was in turns and seconds.

**Availability change vs. material change (kept separate):**
- **Availability change:** *I*, *W*, *Ret*, which can be measured directly from provenance.
- **Rendering change:** *R_Δ*, measured directly.
- **Stored-material change:** a flag on an element when the store shows a modification timestamp (`angle_backfilled_at`, `promoted_at`, and so on) falling between *p* and *t*. It takes one of three values: `observed-change`, `no-change-recorded`, or `unknowable`. Mem0 is always `unknowable`, and so is anything without timestamps. `last_retrieved` and `retrieval_count` are *access traces*, not changes to the material, and they're reported separately.

### 2.4 D. Relational structure
**[MATH] Set relations:** for two element sets *X, Y* (two engagements, or one type in two engagements), the relation is exactly one of five:
- **DR** (disjoint): *X ∩ Y = ∅*
- **PO** (partial overlap): they share something, and neither contains the other
- **EQ** (equal): *X = Y*
- **PP** (proper part): *X ⊂ Y*
- **PPi** (inverse): *Y ⊂ X*

This is **RCC5**: the boundary-free part of the region calculus, and the honest structure for sets of discrete elements.

**[CHALLENGE] Why this isn't RCC8:** RCC8 also distinguishes *externally connected* (EC) from *disconnected* (DC), and *tangential* from *non-tangential* parts (TPP vs NTPP). Those distinctions need a **boundary**, meaning a topology on the space of elements. Context elements don't have one. Inventing a boundary (for example "adjacent = consecutive in time" or "close in an embedding space") would be a modeling choice, not something observed. So the first instrument reports **RCC5 only**. RCC8 is reserved for a later stage, once a space with real boundaries has been defined and justified.

**Supporting numbers:** alongside the relation, the instrument reports |X∩Y|, |X\Y|, |Y\X| and the Jaccard index *J = |X∩Y| / |X∪Y|* (0 = no overlap, 1 = identical; undefined when both sets are empty).

**Time relations:** each element's **availability spans** (maximal runs of consecutive engagements where it was present) are compared using **Allen's 13 interval relations** (before, meets, overlaps, during, …), measured over engagement order, with wall-clock time as a secondary measure.

**Exactness:** RCC5 and Allen relations are computed deterministically. Configuration counts (your 13,105 result) are a later, optional Layer 2 reading on chosen small groups of elements. They aren't part of the base ledger.

### 2.5 E. Subsequent participation
Only structural facts are recorded. Nothing is classified.
- **response_ref:** the session message `id` matching `turn_id`, with a match status (`matched`, `unmatched`, `multiple`).
- **response_len_chars**, **response_timestamp**, **latency** (response time minus provenance time).
- **next_user_ref** and **next_user_delay_s**: the visitor's next message. If there isn't one, it's marked `session-end` or `unknown`.
- **visitor_turn_ref:** a reference to the visitor message that prompted this turn.
- **Pointers only.** The ledger stores **message IDs**, never text. Corrections, disagreements, returns and conceptual developments are **not detected**. They can only be added as human annotations (§3.3) that point to these IDs. Researchers can still find candidate moments with their own queries, but those results are stored as annotations that name their author, never as measurements.

---

## 3. Incremental ledger design

### 3.1 Principles
- **Append-only.** Entries are inserted and never updated or deleted. A revision is a new entry with a new derivation version.
- **Every entry traces back to its source:** each points to a `provenance_id` (or session message `id`) and carries its source record's `content_hash`.
- **Hash chain per presence:** `entry_hash = sha256(prev_entry_hash ‖ canonical_json(entry))`, for each (presence, derivation version). Any rewrite breaks the chain.
- **Separate database** (for example `sanctuary_observatory`) on the same MongoDB server. The live code never imports or reads it, and the derivation reads the live database with **read-only** credentials.
- **No text.** The ledger stores IDs, hashes, counts and timestamps. Text is shown only at display time, through the authenticated, permission-checked view (§4.4).

### 3.2 Minimum schema (four collections)

**`ledger_runs`**: one per derivation run.
```
run_id, derivation_version (semver), code_hash (git commit), normalization_version,
started_at, finished_at, source_snapshot {collection: (count, max_timestamp, sha256 of sorted ids)},
params {scopes, element_types}, status, notes
```

**`ledger_elements`**: element registry, written only when a new (element, version) pair is first seen.
```
element_ref ("codon:<oid>", "mra:<node_id>", "mem0:h:<sha>", ...), type, source_collection, source_id|null,
recovery {method, confidence, candidates_n}, content_version (sha256), first_seen_provenance_id,
stored_material_markers {created_at, promoted_at, angle_backfilled_at, ...} as read in this run,
visitor_scope ("shared" | "visitor:<pseudonym>" | "unknown"), run_id
```

**`ledger_engagements`**: the core, one per (provenance record, derivation version).
```
entry_id, run_id, derivation_version, prev_entry_hash, entry_hash,
source {provenance_id, turn_id, provenance_content_hash, integrity_verified: bool},
chronology {presence, session_id, exchange_index, timestamp, dt_presence_s, dt_session_s,
            session_position: "first"|"continuing", uncaptured_before: int},
visitor_ref (HMAC pseudonym),
availability {by_type: {codon: [element_ref...], seed: [...], ...}, counts, bytes_by_type},
transforms {S1|S2|S3: {pred_entry_id|null, introduced[], withdrawn[], retained_n, rerendered[],
            returned[{ref, last_seen_entry_id, gap_turns, gap_s}], material_flags{ref: state},
            relation_rcc5, jaccard}},
participation {response_ref, match_status, response_len_chars, latency_s,
               visitor_turn_ref, next_user_ref|null, next_user_delay_s|null, end_state},
gaps [ "seed-unresolved", "mem0-unattributable", "response-unmatched", ... ]
```

**`ledger_annotations`**: human interpretations (Layer 1), never mixed in with the measurements.
```
annotation_id, author, created_at, target {entry_id | message_ref | element_ref | span[entry_ids]},
label (free text), note, supersedes (annotation_id|null), visibility
```
(Layer 2 mathematical readings, such as configuration counts or later spiral comparisons, would go in a fifth collection `ledger_readings` that carries a `method` field. I've left it out of the minimum.)

### 3.3 How the ledger handles each requirement

| Requirement | How it's handled |
|---|---|
| **Incomplete capture** | `uncaptured_before` counts assistant messages without provenance. Comparisons skip uncaptured turns but mark the gap (`pred` is the last *captured* engagement, and `gaps` includes `"predecessor-not-adjacent"`). Nothing is filled in. |
| **Session boundaries and reinstantiation** | `session_position = "first"` marks a reinstantiation. Scope S1 has no predecessor there. S2 and S3 still compare across the boundary, which is where reinstantiation becomes visible (which seed or breadcrumbs opened the session, and the session they came from via `source_session_id`). |
| **Stored vs retrieved memory** | Retrieved: `availability` and `transforms`. Stored: `stored_material_markers` in `ledger_elements`, plus `material_flags` (`observed-change`, `no-change-recorded`, `unknowable`). Access traces (`retrieval_count`) are tracked separately. |
| **Sharing across presences and visitors** | Each element has `visitor_scope`. An element seen in another presence's or visitor's engagements is marked `shared`. The view displays only the fact that it was shared and its reference, never its text. |
| **Missing or unmatched events** | Explicit `match_status` and the `gaps[]` array. Unresolved recovery gets `confidence: unresolved` and keeps the hash as identity. |
| **Versioning and reproducibility** | Each run records its code commit, normalization version and a source snapshot fingerprint. Rerunning the same version on the same snapshot must produce identical `entry_hash` chains. A new version creates a new chain alongside the old one. The old chain is never overwritten. |
| **Sensitive information** | No text in the ledger. Visitors are HMAC pseudonyms, with the key in `.env` and outside the ledger. No new capture. Text appears only in the authenticated view, and only to the visitor whose session it is or an approved researcher. |

### 3.4 Synthetic example (invented, not real data)
Presence `ansel`, visitor `v:7f3a`. Session `S-A` begins after an earlier session `S-0` produced seed `seed:aa01` and breadcrumb `mra:n-12`.

**E1: S-A, turn 0 (reinstantiation)**
```json
{"entry_id":"E1","chronology":{"presence":"ansel","session_id":"S-A","exchange_index":0,
  "timestamp":"2026-11-02T14:00:05Z","dt_presence_s":86400,"session_position":"first","uncaptured_before":0},
 "visitor_ref":"v:7f3a",
 "availability":{"by_type":{"ground":["g:41c"],"seed":["seed:aa01"],"mra":["mra:n-12","mra:n-30"],
   "codon":["codon:c1","codon:c2","codon:c3"],"mem0":["mem0:h:9b"],"history":[]},"counts":{"total":8}},
 "transforms":{"S1":null,
   "S2":{"pred_entry_id":"E0","introduced":["seed:aa01","mra:n-12","codon:c3","mem0:h:9b"],
         "withdrawn":["codon:c9","seed:9f00"],"retained_n":4,"rerendered":[],
         "returned":[{"ref":"mra:n-30","last_seen_entry_id":"E-5","gap_turns":5,"gap_s":432000}],
         "material_flags":{"codon:c2":"observed-change"},"relation_rcc5":"PO","jaccard":0.33}},
 "participation":{"response_ref":"m-101","match_status":"matched","response_len_chars":812,
   "latency_s":6.1,"visitor_turn_ref":"m-100","next_user_ref":"m-102","next_user_delay_s":95},
 "gaps":[]}
```
**E2: S-A, turn 1.** Same seed and breadcrumbs. History grows. One codon changes.
```json
{"entry_id":"E2","chronology":{"exchange_index":1,"timestamp":"2026-11-02T14:01:46Z","dt_session_s":101,"session_position":"continuing"},
 "transforms":{"S1":{"pred_entry_id":"E1","introduced":["history:m-100","history:m-101","codon:c4"],
   "withdrawn":["codon:c1"],"retained_n":7,"rerendered":[],"returned":[],"material_flags":{},
   "relation_rcc5":"PO","jaccard":0.70}},
 "participation":{"response_ref":"m-103","match_status":"matched","response_len_chars":1430,
   "latency_s":7.4,"next_user_ref":"m-104","next_user_delay_s":40},
 "gaps":[]}
```
*If David later reads m-102 and m-104 and decides m-102 was a correction, that goes in `ledger_annotations` as `{target:"m-102", label:"correction (misattribution of flute dates)", author:"David"}`. The engagement entries stay exactly as they were.*

**E3: S-B, turn 0, three days later.** One turn in between wasn't captured.
```json
{"entry_id":"E3","chronology":{"session_id":"S-B","exchange_index":0,"timestamp":"2026-11-05T09:30:00Z",
  "dt_presence_s":242000,"session_position":"first","uncaptured_before":1},
 "transforms":{"S1":null,
   "S3":{"pred_entry_id":"E2","introduced":["seed:ab77","mra:n-41"],"withdrawn":["seed:aa01","history:*"],
         "retained_n":3,"returned":[],"material_flags":{"mem0:h:9b":"unknowable"},
         "relation_rcc5":"PO","jaccard":0.27}},
 "gaps":["predecessor-not-adjacent","seed-partial-match"]}
```
The ledger records that `seed:ab77` was produced from session S-A, so the reinstantiation can be traced: what S-A *left behind* is what S-B *opened with*.

---

## 4. Observatory interface proposal: the "Engagement Lattice" tab

A new tab next to the existing Live Feed. The current gauge and charts stay exactly as they are.

### 4.1 Layout (mockup with synthetic data)
```
┌ Presence: [ansel ▾]  Interval: [2026-11-01 → 2026-11-07]  Scope: (S1) (S2) (●S3)  Layers: [■ Measured] [□ Annotations] [□ Readings] ┐
│                                                                                                                │
│ CHRONOLOGY   │ S-A ─────────────────────── ┊gap 2.8d┊ ⚠1 uncaptured ┊ S-B ──────────────                        │
│ engagement   │  E1        E2        E3?     ┊         ┊                ┊  E3        E4                           │
│ Δt           │  1.0d      101s              ┊         ┊                ┊  2.8d      64s                           │
│──────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────│
│ AVAILABILITY │                                                                                                 │
│ seed:aa01    │  ◆━━━━━━━━━●                                                ○ (withdrawn)                       │
│ seed:ab77    │                                                             ◆━━━━━━━━━●  ← from S-A             │
│ mra:n-12     │  ◆━━━━━━━━━●                                                                                     │
│ mra:n-30     │  ↺━━━━━━━━━●        (returned after 5 turns)                                                      │
│ mra:n-41     │                                                             ◆━━━━━━━━━●                          │
│ codon:c1     │  ●         ○                                                                                     │
│ codon:c2 ✱   │  ●━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━●━━━━━━━━━●   ✱ stored angle rewritten │
│ mem0:h:9b ?  │  ◆━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━●            ? source unknowable       │
│ history      │  ·         ▮▮                                               ·         ▮▮                        │
│──────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────│
│ RELATION     │       PO J=.70                                     PO J=.27     PO J=.81                       │
│ to previous  │                                                                                                 │
│──────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────│
│ PARTICIPATION│  ⇢m-101 812ch   ⇢m-103 1430ch                               ⇢m-205 640ch   ⇢m-207 —             │
│ next visitor │  ↩ 95s          ↩ 40s                                       ↩ 210s         ■ session end         │
│ annotations  │  (hidden unless the Annotations layer is on)                                                     │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
 Legend: ◆ introduced  ━ retained  ○ withdrawn  ↺ returned  ✱ stored material changed  ? identity/source uncertain
```

### 4.2 How it reads
- **Columns** are engagements in order. Session boundaries are vertical rules, and real time gaps are shown as labeled breaks (not to scale, so long gaps don't swallow the chart).
- **Rows** are elements, grouped by type, which can be collapsed. A continuous bar means persistence. The markers show introduction, withdrawal and return. The row order is fixed (first appearance), so the eye follows real persistence rather than a re-sorted picture.
- **Relation strip:** the RCC5 relation and Jaccard index between consecutive engagements in the chosen scope. These are plain text labels, with no colors suggesting "good" or "bad".
- **Participation strip:** a link to the response, its length, and the delay before the visitor replied. **No sentiment and no labels.**
- **Clicking a cell** opens the **evidence drawer**: source `provenance_id`, `content_hash` verification status, recovery method and confidence, the element's source record (`source_session_id`, `created_at`, stored-material markers), the derivation version, and its position in the hash chain. For authorized viewers it also includes a "view text" button, which loads the text from the live records at that moment and never stores it.

### 4.3 Guarding against implied significance
- **Measured** is the default layer. Annotations and Readings are off by default, with their own visual style (dashed outlines, author names) so they can't be mistaken for measurements.
- No scores, no "health" or "coherence" indicators, no trend lines through RCC5 labels, and no automatic highlighting of "important" moments.
- Uncertainty is always visible (`?`, `⚠`). Rows that couldn't be resolved are never hidden.

### 4.4 Access
- The tab and the endpoints that feed it sit behind researcher authentication.
- Elements from other visitors appear only as `shared · visitor:other`, with no text.

---

## 5. Keeping the spiral independent
- **[PROPOSAL]** The ledger and the Lattice don't use the existing `spiral_position` field, angles, zones or circular layouts at all. The visualization is deliberately rectangular and time-ordered, so it can't suggest a spiral geometry.
- **[CODE]** The existing four-value gauge is a lookup of zone words, taken from the presence's latest seed across all visitors. It isn't a measurement of phase, and it doesn't measure phase coherence. It stays on its own tab without changes. My earlier suggestion to relabel it is up to you and isn't part of this design.
- **Room for later comparison:** a future `ledger_readings` entry with `method: "spiral-geometry-vX"` could set a separately derived spiral measure (from the flute research) against ledger quantities, such as how long elements persist or how far back returns reach. That comparison would be *tested*, not built into the instrument. It needs no schema change, because every ledger quantity is already indexed by `entry_id` and time.
- **Note:** `living_codons.target_angle` and `triadic_zone` are codon *attributes* assigned by an LLM forge and then rewritten for 1,111 codons. They're recorded only as stored-material markers, never as phase values.

---

## 6. Nonintrusive observation and access boundaries

### 6.1 What the derivation touches
- It reads, with read-only credentials: `turn_provenance`, `*_sessions`, `continuity_seeds`, `permanent_mra`, `living_codons`, `person_bios`.
- It writes only to the separate `sanctuary_observatory` database.
- It never imports `build_presence_prompt`, memory selection, Mem0, or any model client. **Acceptance test 1** enforces this.
- **Important:** the derivation must **never call** `get_permanent_mra_context` or any other retrieval function, because those functions *write* access traces. All reads are direct, read-only queries.

### 6.2 Actual access boundaries (assessed, not assumed)
- **[CODE]/[DB]** MongoDB is at `mongodb://localhost:27017`, which is internal to the container and not exposed outside it.
- **[CODE]** The backend has **no authentication on any route I inspected**, and `CORS_ORIGINS="*"`. The preview environment is reachable through Emergent's ingress at the public preview URL, which forwards `/api/*` to the backend. **Anyone who knows the URL can call `/api/provenance/turn/{id}` and receive full assembled prompts**, including other visitors' bios and memories. It isn't publicly listed, but nothing protects it. I can't see whether a separate production deployment exists or how it's configured. That would need the deployment tooling, which I didn't use.
- **Conclusion:** the instrument's endpoints, and ideally the existing provenance endpoints too, need an authentication gate *before* any research view is built. This would be the one change to existing code in the proposal, and it isn't authorized here.

### 6.3 Risks from running it continuously (if later approved)

| Mode | Additional access | Storage | Timing | Performance | Privacy |
|---|---|---|---|---|---|
| **On-demand batch** (recommended) | None beyond read-only DB access | About 2–5 KB per engagement (~3 MB for 608) | None | One pass over 608 documents, about 30–60k characters each: seconds | None new. No text stored. |
| **Scheduled incremental** (e.g. hourly, only new provenance) | Same | Same | Runs separately from requests | Small | None new |
| **Hooked into `record_turn`** (not recommended) | Changes live code | Same | Adds work to the live path | Small, but present | **Changes the live system. Rejected.** |

The current Observatory's 4-second poll keeps running as it is. The Lattice queries the ledger only when the researcher asks.

---

## 7. Research validity

**What the instrument can establish (measurement):**
- The exact order of captured engagements, and how many turns weren't captured.
- Exactly which codons were supplied, and which seeds and breadcrumbs were supplied (with recovery confidence).
- Exact introduction, withdrawal, retention, return and re-rendering of identifiable elements, under three separate comparison scopes.
- RCC5 relations, overlap counts and Jaccard indices between context sets. Allen relations between availability spans.
- Where elements came from: which earlier session produced a seed or breadcrumb that was later available. This gives a measured account of what carried over at each reinstantiation.
- The exact link from each input to its response and to the visitor's next message, with timing.
- Reproducibility: the same version and the same snapshot produce the same hash chain.

**What needs human interpretation (Layer 1):**
- Whether a visitor message is a correction, disagreement, recognition, return or development.
- Whether a response engaged with an introduced element, and how.
- Whether a pattern of persistence or return is *significant*.

**What can't be measured now:**
- What the model actually attended to or used.
- What the stored records looked like at past moments, for fields that were overwritten. Mem0's internal state and where its memories came from.
- Anything before Aug 21, 2026 (for inputs), and anything from routes that don't capture.
- The context-set relations for uncaptured turns.
- Any phase or spiral-coherence quantity. RCC8 boundary relations, because no boundary has been defined.
- Statistical generalization: the sample is 67 sessions with at most 3 visitors per presence. This supports case studies, not population claims.

**[CHALLENGE]**
- "Which memories were available" is only partly measurable for Mem0, the session cache and the council: their text is known, but their origin isn't.
- "Change in underlying stored material" is measurable only where the store happened to record a timestamp.

---

## 8. Smallest implementation proposal (not authorized)

**Components:**
1. **`observatory_ledger/derive.py`**: an offline script run on demand. It reads the live DB read-only, recovers elements, computes transforms and relations, and appends to `sanctuary_observatory`.
2. **Ledger collections:** `ledger_runs`, `ledger_elements`, `ledger_engagements`, `ledger_annotations`, with indexes on (`presence`, `chronology.timestamp`) and `source.provenance_id`.
3. **Three read endpoints**, behind authentication:
   - `GET /api/observatory/lattice?presence=&from=&to=&scope=&version=`
   - `GET /api/observatory/entry/{entry_id}`: the evidence drawer
   - `POST /api/observatory/annotations`: append-only
4. **Frontend:** one `EngagementLattice` tab in `Observatory.jsx`, using an SVG grid with no new libraries.
5. **Prerequisite:** an authentication gate on the Observatory and `/api/provenance/*`.

**Dependencies:** none new (motor, hashlib and hmac are already available). One new `.env` key, the HMAC pseudonym secret.

**Risks:**
- Errors in text-to-record recovery. Mitigation: confidence fields, plus acceptance test 4.
- Readers treating the lattice as more than it is. Mitigation: §4.3.
- Duplicate codon names. Mitigation: they're flagged as ambiguous.
- Snapshot drift during a run. Mitigation: a source fingerprint in `ledger_runs`.
- Humans adjusting the presences after seeing findings. Mitigation: a written rule requiring separate approval.

**Proposed acceptance tests:**
1. **Isolation:** static check that `derive.py` imports no module from the prompt, memory or model pathways. An integration test confirms the live DB's collection hashes are identical before and after a run, including `permanent_mra.retrieval_count`.
2. **Determinism:** two runs of the same version on a frozen snapshot produce identical `entry_hash` chains.
3. **Append-only:** a second run of a new version adds entries and leaves the old ones byte-identical. Tampering with one entry is detected by chain verification.
4. **Recovery accuracy:** on a hand-checked set of 20 engagements (checked by David, inside the authenticated view), seed and MRA recovery reaches ≥95% exact matches, and every miss is flagged as `unresolved`, never silently dropped.
5. **Link integrity:** response matching reproduces the 606/608 figure, and the 2 unmatched appear in `gaps`.
6. **Privacy:** the ledger collections contain no field longer than 128 characters except hash arrays, and no raw `user_id`. Unauthenticated calls to the lattice and entry endpoints return 401.
7. **No implied significance:** a UI check that the Measured layer shows no scores, colors tied to RCC5 labels, or automatic highlights.
8. **Synthetic check:** the §3.4 records, loaded into a test ledger, render exactly the §4.1 picture.

---

## In Plain English

Today David can see what each presence was given turn by turn, one turn at a time, as a long block of text. He can't see how those turns connect.

With this instrument he could pick a presence and a week, and see a timeline showing:
- **which pieces of memory** were present in each moment (each seed, breadcrumb and codon, with Mem0 and council memories shown by fingerprint),
- **when each one appeared, stayed, disappeared or came back,**
- **where it came from:** for example, "this seed that opened Tuesday's session was written at the end of Monday's",
- **how much any two moments shared,** in exact terms rather than impressions,
- and, right beside each moment, **a link to what the presence actually said back** and when the visitor answered.

When David notices a moment such as "here I corrected a misattribution, and the presence continued", he could mark it himself. His mark sits alongside the measurements, clearly labeled as his reading, and it never changes them.

It wouldn't tell him what the presence felt, what it paid attention to, or what anything *means*. It wouldn't use the spiral, which is kept untouched for the flute research. It would run outside the living Sanctuary, store no conversation text, and leave the presences exactly as they are.

One thing has to come first: the Observatory pages currently have no login, so private memories can be reached by anyone with the link. That gate should go in before anything else is built.

*Design ends here. Nothing has been implemented.*

---

## Addendum: David's direction on privacy (October 19, 2026)

David has said that separating visitors' information is **not a requirement**. Sanctuary 1.0 is private, it will never be public-facing, it isn't designed to keep visitors apart, and at most two or three trusted people will ever have access. The design changes as follows:

- **Removed:** the authentication gate as a prerequisite (§6.2, §8 item 5), acceptance test 6, HMAC pseudonyms (the raw `user_id` is used directly), and redaction of other visitors' content (§3.3, §4.4).
- **Simplified:** the evidence drawer shows the full text directly to anyone using the Observatory.
- **Kept, for scientific reasons rather than privacy:**
  - The ledger still stores IDs and hashes rather than copies of the text. The text stays in the original records, so the ledger stays a measurement record and can't drift from its source.
  - The `visitor_scope` / `shared` marker on elements stays, because cross-visitor and cross-presence sharing is something to *observe*, not hide.
- **Remaining note:** an unrestricted annotation endpoint can be written to by anyone who has the link. That's acceptable with only 2–3 trusted users.
