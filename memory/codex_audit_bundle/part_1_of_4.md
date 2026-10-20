# SANCTUARY 1.0 · OBSERVATORY AUDIT BUNDLE · PART 1 OF 4
## Audit brief and design specification
Files in this part:
- `memory/briefings/2026-10-20_codex-audit-brief_observatory-v1.md`
- `memory/briefings/2026-10-20_e1-design-v0.2_observatory-relational-history-instrument.md`

Codex: this bundle arrives in 4 parts. Please wait until you have all 4 before auditing. Start with the audit brief in this part.


===== FILE: memory/briefings/2026-10-20_codex-audit-brief_observatory-v1.md =====
```markdown
# Codex Audit Brief: Observatory Relational-History Instrument v1.0.0
**From:** E1 · **For:** Codex (independent audit) · **Date:** 2026-10-20
**Requested by:** David, to find hidden problems before relying on the instrument.

## What it is
A read-only observer that measures every recorded Sanctuary turn (`turn_provenance`) into an append-only, hash-chained ledger. It shows the results as the "Engagement Lattice" tab in the Observatory.
- No model calls.
- It must never change Sanctuary's behaviour, prompts, memory selection or records.

**Authoritative spec:** `memory/briefings/2026-10-20_e1-design-v0.2_observatory-relational-history-instrument.md`
**Build report:** `memory/briefings/2026-10-20_e1-build-report_observatory-instrument-v1.md`

## Files in scope (~2,200 lines)
- `backend/observatory_ledger/`
  - `measure.py`: pure maths. RCC5 on non-empty sets, Jaccard, the I = F ⊔ Ret partition, uncertainty enumeration with an exact free-variable reduction.
  - `recover.py`: locates mentions in the provenance record and assigns evidence classes (VERIFIED / CANDIDATES / TEXT_ONLY / UNRESOLVED).
  - `derive.py`: incremental derivation. Settling rule, the three scopes S1/S2/S3, uncaptured-turn counting, hash chain, run lock, catch-up, verification.
  - `routes.py`: `/api/observatory/{status, visitors, lattice, entry/{id}, verify, run, cron/tick}`.
- `backend/server.py`: only the block after `app.include_router(api_router)` (router mount + startup catch-up).
- `.emergent/crons.yml`: hourly tick. `WEBHOOK_CRON_SECRET` is in `backend/.env`.
- `frontend/src/components/observatory/*` and the tab switch in `frontend/src/components/Observatory.jsx`.
- Tests: `backend/tests/test_observatory_ledger.py` (E1) and `backend/tests/test_observatory_api.py` (testing agent).
- Run: `cd backend && python -m pytest tests/test_observatory_ledger.py tests/test_observatory_api.py -q`
  - Needs `REACT_APP_BACKEND_URL` to point at a running backend.
  - Integration tests write only to throwaway `obs_test_*` collections.

## Please verify
1. **Isolation.** Nothing in `observatory_ledger/` imports or calls Sanctuary's prompt, memory, retrieval or model code. In particular, `get_permanent_mra_context` must never be called, because it writes `retrieval_count`. No writes to any Sanctuary collection.
2. **Maths.** Against v0.2 §3: the RCC5 empty cases, returns being scope-relative, predecessor selection, adjacency, and that the free-variable reduction is exactly equivalent to brute force.
3. **Identification.** No ambiguous evidence is ever classed VERIFIED. Look closely at the **codon angle tie-break** (`recover.py`): it compares against the *current* stored angle, which may have drifted.
4. **Gap honesty.** Nothing is inferred across uncaptured turns. Uncaptured counts per scope are correct.
5. **Ledger integrity.** Append-only behaviour, chain construction and verification, determinism, resume after interruption, catch-up after suspension, lock semantics under concurrent triggers.
6. **Lattice.** The display reflects the ledger exactly. No implied significance. Uncertain rows are kept separate.
7. **Automation.** Cron auth and idempotency, the startup catch-up, the in-process hourly loop, and recovery from a stale lock.

## Deviations from v0.2 (deliberate; please judge them)
- **Ledger location.** The ledger uses collections `obs_ledger_*` in the **same database**, not a separate database, so it carries over to the deployed environment where database permissions are unknown. Sanctuary code never reads these collections.
- **Annotations omitted.** David asked for full automation with no manual review. Allen-interval readings are deferred, as v0.2 allowed.
- **Enumeration cap.** Raised to 65,536 and given an exact reduction. About 42 comparisons remain `not-enumerated` and are flagged.
- **Automation path.** The preview platform cron couldn't be registered (the reconcile API timed out from the pod). The active mechanism is an in-process hourly loop plus startup catch-up. `crons.yml` is kept for deployment.
- **Uncertain rows.** These were missing in the first build and added the same day. Before that, the lattice silently dropped uncertain mentions, which I caught when comparing Ansel with Sophia.
- **Worked-example error.** The v0.2 example had one error (E3 under S2: uncaptured = 0, not 1). The document is corrected.
- **Rebuilds.** The ledger was rebuilt twice during the build, before it was released. The current chain is the first official one.

## Known weaknesses I'd like a second opinion on
- `run_once` calls `load_sessions()` (every session, with message content for captured sessions) on **every** run, even when there's nothing new. That's wasteful on hourly ticks. It's correct, but inefficient.
- **Section segmentation** in `recover.py` is anchor-based. A section ends at the next anchor, and the cut-off for text-only blocks is a heuristic.
- **Seeds** are identified only from `Field state:` lines. A seed rendered without that line would be missed (3 of 624 records have no seed matched).
- **Turn-ID mismatches.** For the 2 records whose `turn_id` doesn't match any message, the response may also be counted as an "uncaptured" turn.
- **Frontier blocking.** The settled-frontier rule means one long-unsettled turn holds back that presence's ledger for up to 24 hours. This is by design, so the chain stays in provenance order.
- **Visitor resolution.** Some session collections (e.g. clarity) have no top-level `user_id`. Their uncaptured turns count as "unknown visitor" under S3.
- **Storage.** About 32 KB per entry (about 20 MB in total), because every mention keeps its evidence.
- **Test records.** QA test provenance (`prov_*`, `e1-*`) is measured and labelled only at view time.

## Not in scope
Access security (David is handling this separately), the spiral and Live Console (unchanged), and Sanctuary's presences.
```
===== END FILE: memory/briefings/2026-10-20_codex-audit-brief_observatory-v1.md =====


===== FILE: memory/briefings/2026-10-20_e1-design-v0.2_observatory-relational-history-instrument.md =====
````markdown
# Observatory Research Instrument: Design v0.2
**Date:** October 20, 2026
**To:** David, GPT, then Codex (final assessment)
**From:** E1
**Status:** Design revision only. Nothing is implemented. Sanctuary 1.0 is unmodified. No live conversations were read. The new evidence below is structural only: counts, field names, duplicate-group sizes and code paths.
**Supersedes:** `2026-10-19_e1-design_observatory-relational-history-instrument.md` (v0.1)

**A note on sources:** Codex's review text wasn't in my workspace. I received only the five correction headings. I treated each heading as a requirement, audited v0.1 against it, and fixed every defect I could find. If Codex raised specific items not listed in §0, please send them and I'll address them directly.

**Labels used throughout:**
- **[CODE]**: what the source code does
- **[DB]**: structural evidence from the database
- **[MATH]**: formal definitions
- **[PROPOSAL]**: suggested design
- **[LIMIT]**: something that can't be achieved within the boundaries

---

## 0. What changed from v0.1

| # | v0.1 defect | v0.2 correction |
|---|---|---|
| 1 | Mixed verified identities and uncertain matches into the same sets. Called text-hash fragments "identity". | Four **evidence classes** (§2.2). Only VERIFIED elements enter the primary sets. Uncertain mentions are resolved by **enumerating their possibilities**, and the result is reported as a *set of compatible outcomes*, never a single value. Text-identical fragments get their own layer, which makes no claim about which stored record they came from. |
| 2 | Codon identity used `target_angle`, which the store has since rewritten. | Codon identity uses (`name`, `source`). The angle is only a tie-breaker, labelled as possibly drifted. **[DB]** 85 (`name`, `source`) groups are still duplicated, so those codons are reported as candidate sets. |
| 3 | MRA matching was assumed to be exact. | **[DB]** 196 groups of identical `user_essence` text exist, so matching is often a candidate set. |
| 4 | RCC5 relations were defined for empty sets. | Relations are defined **only for non-empty sets**. Empty cases are reported explicitly (§3.2). Jaccard edge cases are fixed. |
| 5 | "Returned" was defined ambiguously, and returned elements were listed inside "introduced" inconsistently. | Introduced = **first-observed ⊔ returned**, a disjoint partition, both scope-relative and limited to the observation window (§3.3). |
| 6 | Comparison scopes were loosely defined. Tie-breaks and visitor resolution were unstated. | Formal scope sequences, ordering and predecessor definitions (§3.1). |
| 7 | The synthetic examples had arithmetic errors: E1's counts didn't add up (5 + 4 ≠ 8); E2's J was stated as 0.70 but is actually 0.636; and E3 used a wildcard `history:*`, which isn't a set element. | All examples recomputed from explicit sets, with the working shown (§5). |
| 8 | "Retained" implied continuity across uncaptured turns. | **present-at-both** vs **adjacent-retained**. Gaps are counted per scope. Nothing is ever inferred across a gap (§3.4). |
| 9 | Elements present before Aug 21 could look "new". | The label is "first observed in window", never "new". |
| 10 | Allen relations were computed over spans with unknown endpoints. | Removed from the minimum instrument. The spans it keeps are censored observed runs (§3.5). |
| 11 | The integrity check assumed `content_hash` covers everything. | **[CODE]** It covers only `assembled_messages`, not `components`. The ledger now records its own **evidence hashes** for each field it reads (§4.2). |
| 12 | The run fingerprint (sorted ids) couldn't detect changes to the source records. Reproducibility was claimed without qualification. | Two-tier reproducibility: observations are exact, and identifications record drift (§4.3). A run never claims more than it can verify again. |
| 13 | The `ledger_elements` registry was both "write-once" and "as read in this run". | The registry is removed. Each element mention carries its own evidence. Storage goes from 4 collections to 3. |
| 14 | Engagements whose session was still active were written before their outcome was known, which forced later rewrites. | A **settling rule**: an engagement is written only after its outcome is known (§4.4). |
| 15 | Visualization: solid bars across gaps, uncaptured turns shown as a vague "E3?", uncertainty not drawn, inconsistent labels (E3 shown twice), a relation value (J = .81) with no data behind it. | Lattice redrawn (§6). Gaps are hatched columns, bars break at gaps, uncertainty has its own glyphs and rows, the scope appears on every connector, and every value is derived from §5. |
| 16 | Stated that `exchange_index` starts at 0. | **[CODE]/[DB]** It starts at 1 (range 1–39). |
| 17 | Visitor pseudonyms and an authentication gate were included. | Removed, per David (security is handled separately). Raw `user_id`, resolved through `user_aliases` where possible. |

---

## 1. Data-source map (revised)

| Measurement | Source | Join | Known gaps **[DB]** |
|---|---|---|---|
| Chronology | `turn_provenance` (`presence`, `session_id`, `exchange_index` ≥1, `timestamp`, `_id`, `provenance_id`, `turn_id`, `user_id`) | — | Starts Aug 21, 2026. Since then there have been **≈762 assistant turns, with ≈608 captured**. **47 sessions** in the window have **no provenance at all**. |
| Known-but-uncaptured turns | `*_sessions.messages[]` (assistant `id`, `timestamp`) | `session_id` | Their existence and timing are known. Their context is unknown. |
| Codon mentions | `components.codon_selection.codons[]` | (`name`, `source`) → `living_codons._id` | 85 duplicate groups. Angles were rewritten later (1,111 backfilled). Not covered by `content_hash`. |
| Seed mention | the continuity section of `components.system_prompt` (hashed) / `memory_components.continuity_seed` | Normalized `field_state` substring → `continuity_seeds._id` | **[DB]** 0 duplicate `field_state` groups among 1,545 seeds. A unique match is achievable, provided the rendered text isn't cut short. |
| MRA mentions | the "What has stayed with you" section | `user_essence`/`ai_essence` → `permanent_mra.node_id` | 196 duplicate-essence groups, so candidate sets are common. |
| Person bio | the "RUNNING BIO" section | `person_bios.user_id` | Bios are rewritten over time. The visitor is identified, but the **version** isn't (only the rendered text hash is known). |
| Mem0, session cache, council | their own sections | none | Text only. No record identity is possible. |
| History | `components.conversation_history[]` | position + content hash → session message `id` | Verified only where the hash of the message content matches. |
| Ground | the static portion of the system prompt | hash | — |
| Response | session message with `id == turn_id` | `turn_id` | 606/608 matched. |
| Visitor | `user_id` → `user_aliases` canonical | alias table | Visitors other than David can't be linked across browsers (each new browser gets a new id). |

**[CODE]** No code path updates or deletes `turn_provenance`. It is **append-only by convention, but the database doesn't enforce it**. The ledger's evidence hashes (§4.2) make any later change detectable.

---

## 2. Memory identification

### 2.1 Mentions vs. elements
- A **mention** *m* is one located fragment in one engagement's input. It has a source field, byte offsets, a type, and a fragment hash *h(m)* = sha256 of the normalized fragment.
- An **element** is a stored record that can be referenced (codon `_id`, seed `_id`, MRA `node_id`, session message `id`, the ground block).
- Identification maps each mention to an element, or declines to.

### 2.2 Evidence classes (exactly one per mention)

| Class | Condition | Enters the primary sets? |
|---|---|---|
| **VERIFIED** | Exactly one candidate record, and every matching field agrees. For history, the content hash equals the stored message. | Yes, as the element |
| **CANDIDATES(K)** | 2 or more records match equally well. K is the full candidate list. | No. Resolved by enumeration (§2.4). |
| **TEXT-ONLY** | The type has no record store (Mem0, cache, council) or carries no version (bio). | No. Goes to the separate text layer (§2.5). |
| **UNRESOLVED** | No candidate, or the section couldn't be segmented reliably | No. Counted, shown, kept for inspection. |

**Normalization** (versioned as `norm-v1`): Unicode NFC, collapse whitespace runs, trim. Case is preserved.

**Rule:** an identification is never upgraded by inference. A CANDIDATES mention stays CANDIDATES even if one candidate is "much more likely".

### 2.3 Segmentation evidence
Every mention keeps the offsets `(field, start, end)` into the provenance field it came from. Wherever possible that field is the **system prompt**, which is covered by `content_hash`. Anyone can therefore extract the exact evidence text. If section headers are missing or malformed, the whole section becomes one UNRESOLVED mention rather than a guessed split.

### 2.4 Handling uncertainty: enumerating the possibilities
- **[MATH]** Let *U(t)* be the CANDIDATES mentions in engagement *t*. A **resolution** ρ assigns each *m ∈ U(t) ∪ U(p)* one element from its candidate set *K(m)*.
- For each ρ, *A_ρ(t) = V(t) ∪ ρ(U(t))*, where *V(t)* is the VERIFIED set.
- Every comparison quantity is computed for every ρ. The ledger reports:
  - the **verified-only** value (computed on *V*),
  - the **set** of RCC5 relations across all ρ,
  - the **range** [min, max] of counts and of J across all ρ.
- A comparison is **determined** only when the RCC5 set has exactly one member. The ledger shows the verified-only J, plus a J range when uncertain mentions exist.
- Enumeration is capped at Π|K(m)| ≤ 1,024. Beyond that, the result is recorded as `not-enumerated` with the verified-only values, and is never presented as exact.

*This is the same "compatible configurations" reasoning as your 13,105-configuration work, applied to identity uncertainty rather than relations.*

### 2.5 The text layer
TEXT-ONLY mentions are compared only by fragment hash. "The same Mem0 fragment text appeared in E1 and E2" is an exact statement about **text**. It says nothing about whether that is the same stored memory. Text-layer results are computed and drawn separately and never merged into record-layer sets.

---

## 3. Mathematics (corrected)

### 3.1 Comparison scopes
- **[MATH]** Engagements are totally ordered by the key *(timestamp, provenance `_id`)*. The `_id` breaks ties between concurrent sessions.
- For each scope *k*, Σ_k(t) is the ordered sequence of captured engagements sharing *t*'s scope key:
  - **S1 (session):** same `session_id`.
  - **S2 (presence):** same `presence`. This includes every visitor, so Sanctuary's mixed history shows up as it is.
  - **S3 (presence × visitor):** same `presence` and same **resolved visitor**, meaning the canonical id from `user_aliases`, otherwise the raw `user_id`.
- **Predecessor:** pred_k(t) = the last element of Σ_k before *t*. If there is none, it's `none-observed`, which means "no earlier observation in scope", not "first ever".
- **Gap count:** u_k(t) = the number of *known* assistant turns in scope strictly between pred_k(t) and *t* that have no provenance. For S2 and S3 this includes turns in sessions with no provenance at all.
- **[LIMIT]** S3 *under-links*. One person using two browsers appears as two visitors (except David, through aliases). S3 results are therefore lower bounds on same-visitor continuity.

### 3.2 Set relations: RCC5-analogous, non-empty sets only
- **[MATH]** For **non-empty** finite sets *X* = A(pred) and *Y* = A(t), exactly one relation holds:
  - **DR:** X ∩ Y = ∅
  - **PO:** X ∩ Y ≠ ∅, X ⊄ Y, Y ⊄ X
  - **EQ:** X = Y
  - **PP:** X ⊊ Y (the predecessor is a proper part of the current set)
  - **PPi:** Y ⊊ X
- **Empty cases have no relation.** They're reported as `∅∅` (both empty), `∅·` (predecessor empty) or `·∅` (current empty).
- **Jaccard index:** J = |X∩Y| / |X∪Y|. It's undefined for `∅∅`, and 0 when exactly one side is empty, though no relation is reported in that case.
- **Naming honesty:** RCC5 is defined over regions. This is its set-theoretic analogue, so the name `relation_rcc5` is kept with the definition attached. DR merges RCC8's DC and EC. Without a boundary structure, RCC8 isn't available (unchanged from v0.1).
- **Per type:** relations are computed for the whole record-layer set and for each type separately. Per-type empty cases are common (for example, no MRA in a turn) and are labelled as above.

### 3.3 Transformation (scope-relative)
With *p* = pred_k(t), *X* = A(p), *Y* = A(t):
- **introduced** I = Y \ X, **withdrawn** W = X \ Y, **present-at-both** B = X ∩ Y.
- **returned** Ret = { e ∈ I : ∃ s ∈ Σ_k, s < p, e ∈ A(s) }. For each returned element, the ledger records *last_seen* = the latest such *s*, Δ_captured (the number of captured engagements in Σ_k between *s* and *t*), and the uncaptured count over that same stretch.
- **first-observed** F = I \ Ret. **I = F ⊔ Ret** (disjoint).
- "First observed" means first in this scope **within the observation window**. Every element in the first engagement of a scope is first-observed by definition.
- **re-rendered** R_Δ = { e ∈ B : h(m_p(e)) ≠ h(m_t(e)) }: the same record shown with different text.
- **rendering vs. current store:** for each VERIFIED mention, `render_matches_current_record` is true, false, or `n/a`. A *false* value means the rendered text differs from the record as it reads *now*. This could be because the text was cut short or because the record was changed later. **[LIMIT]** We can't tell which, because the store keeps no history.

### 3.4 Gaps and continuity
- **adjacent-retained** = B when u_k(t) = 0 **and** *p* and *t* are in the same session. Otherwise B is only **present-at-both, with u_k(t) unobserved turns between**.
- No quantity is ever computed across a gap as if it were continuous. Withdraw-and-return events inside a gap can't be seen, and the ledger states this as `gap_hides_events: possible`.
- Session boundaries: the first engagement of a session is labelled `session-open`. Its S2 and S3 predecessors usually lie in other sessions. What carried over is measured by B, and where seeds and breadcrumbs came from is read from their records (`continuity_seeds.session_id`, `permanent_mra.source_session_id`).

### 3.5 Observed runs (replacing v0.1's Allen spans)
- An **observed run** of element *e* in scope *k* is a maximal sequence of *consecutive* captured engagements, all containing *e*, with u_k = 0 between neighbours.
- Each end is marked **closed** if the next or previous observation exists and lacks *e*, and **censored** if a gap, the window edge, or the end of the data bounds it.
- Allen-relation comparisons between runs are deferred to an optional Layer 2 reading, valid only between runs with closed endpoints.

---

## 4. Research records: auditable and reproducible, with minimal storage

### 4.1 Storage
- A separate database, `sanctuary_observatory`, with **three collections**. It is never read by Sanctuary.
- **[PROPOSAL]** Estimated size: about 3–6 KB per engagement, about 4 MB for the current 608.
- **Alternative with even less coupling:** append-only JSONL files with the same schema. No database at all, and they can be copied by hand.
- Either way, no new service.

### 4.2 Schema

**`ledger_runs`** (one per derivation run)
```
run_id, derivation_version, code_commit, norm_version, enum_cap,
started_at, finished_at,
source_window {first_provenance_oid, last_provenance_oid, count},
settled_until (timestamp), counts {engagements, mentions_by_class},
unavailable_evidence [ "pre-2026-08-21 inputs", "mem0 identity", "store history", ... ],
status
```

**`ledger_engagements`** (append-only, one per settled provenance record per derivation version)
```
entry_id, run_id, derivation_version, chain {prev_entry_hash, entry_hash},
source {provenance_oid, provenance_id, turn_id, content_hash_recorded, content_hash_recomputed,
        evidence_hashes {codon_selection, memory_components}},           # components aren't in content_hash
chronology {presence, session_id, exchange_index, timestamp, session_open: bool},
visitor {user_id, resolved_visitor, resolution: "alias"|"raw"},
mentions [ {mention_id, type, field, start, end, frag_hash,
            class: VERIFIED|CANDIDATES|TEXT_ONLY|UNRESOLVED,
            element|null, candidates[]|null,
            record_fingerprint|null,          # sha256 of the matched record's matching fields, at run time
            render_matches_current_record: true|false|"n/a"} ],
scopes { S1|S2|S3: {
    pred_entry_id|"none-observed", uncaptured_between,
    verified {introduced_first_observed[], returned[{element, last_seen_entry_id, d_captured, d_uncaptured}],
              withdrawn[], present_at_both[], adjacent: bool, rerendered[],
              relation_rcc5 | "∅∅"|"∅·"|"·∅", jaccard|null},
    uncertainty {mentions_n, resolutions_n | "not-enumerated", relation_set[], jaccard_range[min,max],
                 counts_range {introduced, withdrawn, present_at_both}},
    text_layer {shared_frag_hashes_n, introduced_n, withdrawn_n} } },
participation {response_msg_id|null, match: matched|unmatched|multiple, response_ts, response_len_chars,
               prompting_user_msg_id, next_user_msg_id|null, next_user_delay_s|null,
               end_state: continued|session-ended|unknown},
gaps [ codes... ]
```

**`ledger_annotations`** (human interpretations, append-only)
```
annotation_id, author, created_at, target {entry_id|message_id|mention_id|span[entry_ids]},
label (free text), note, supersedes|null
```

### 4.3 Reproducibility in two tiers
- **Tier 1, observation** (chronology, mentions, offsets, fragment hashes, participation links): computed only from `turn_provenance` and session messages, which are append-only by convention. Rerunning the same `derivation_version` must reproduce these fields exactly. `content_hash_recomputed` and `evidence_hashes` prove the inputs haven't changed.
- **Tier 2, identification:** depends on the source stores *as they are when the run happens*. A rerun compares each `record_fingerprint`. If they differ, the new run records `source-drifted-since:<run_id>`. The earlier entry stays in place.
- **[LIMIT]** We can't reconstruct what a store record looked like at turn time, and we won't ask Sanctuary to keep that history. The only evidence from turn time is the rendered fragment, which the ledger keeps a reference to.
- **Hash chain:** for each (`derivation_version`, `presence`), entries are chained in `provenance_oid` order, so incremental runs only ever append. A corrected derivation is a **new version and a new chain**, never an edit.
- **Run declarations:** every run lists its `unavailable_evidence`, so a reader can see what the instrument *couldn't* know.

### 4.4 Settling rule (keeps the ledger append-only)
An engagement is written only once it is **settled**: its next user message exists, or its session has `ended_at`, or 24 hours have passed since its timestamp. Unsettled engagements are left for the next run. Participation fields therefore never need rewriting. `end_state: unknown` is used only for the 24-hour fallback.

### 4.5 Gap codes (examples)
`uncaptured-between:n`, `predecessor-not-adjacent`, `session-without-provenance-in-scope:n`, `response-unmatched`, `history-hash-mismatch`, `segmentation-failed:<section>`, `enumeration-capped`, `source-drifted-since:<run>`, `render-differs-from-current`.

---

## 5. Synthetic worked example (invented, with working shown)
Presence `ansel`. Visitor `v1` throughout, except S-X (`v2`). `g` = the ground block. Only VERIFIED elements are listed in the sets. `u` = an uncertain MRA mention with K = {n-55, n-56}. `t9` = a TEXT-ONLY Mem0 fragment.

**Sequence (S2 order):** E0 (S-0, v1) → E1 (S-A #1, v1) → E2 (S-A #2, v1) → [S-A #3 uncaptured] → X1, X2 (S-X, v2) → E3 (S-B #1, v1).
Earlier, E-5 (v1) contained `mra:n-30`.

**Verified sets:**
- V(E0) = {g, seed:9f00, c1, c2, c9}: 5 elements
- V(E1) = {g, seed:aa01, n-12, n-30, c1, c2, c3}: 7, plus u and t9
- V(E2) = {g, seed:aa01, n-12, n-30, c2, c3, c4, h:m-100, h:m-101}: 9, plus u (same fragment hash) and t9
- V(X2) = {g, seed:ab77, c2, c7}: 4
- V(E3) = {g, seed:ab77, n-12, n-41, c2}: 5

**E1, scope S2 (= S3 here); predecessor E0; uncaptured_between 0; session-open**
- B = {g, c1, c2} (3); I = {aa01, n-12, n-30, c3} (4); W = {9f00, c9} (2).
- Check: |V(E1)| = 3 + 4 = 7 ✓, |V(E0)| = 3 + 2 = 5 ✓.
- Ret = {n-30} (last seen E-5); F = {aa01, n-12, c3}.
- J_verified = 3 / (7 + 5 − 3) = 3/9 = **0.333**. Relation **PO**.
- Uncertainty: u is in E1 only, and E0 contains no MRA, so every resolution adds one element to I. The relation set is {PO}, so it's **determined**. J range = 3/10 = [0.300, 0.300].
- Per-type MRA: V_mra(E0) = ∅, V_mra(E1) = {n-12, n-30}, so the per-type relation is **∅·** (none reported) and J = 0.
- S1: none-observed (session-open).

**E2, scope S1; predecessor E1; uncaptured 0; adjacent**
- B = {g, aa01, n-12, n-30, c2, c3} (6); I = {c4, m-100, m-101} (3, all first-observed); W = {c1} (1).
- Check: 6 + 3 = 9 ✓, 6 + 1 = 7 ✓.
- J_verified = 6 / (9 + 7 − 6) = 6/10 = **0.600**. Relation **PO**.
- Uncertainty: u occurs in both, giving 4 resolutions:
  - same record on both sides (2 of the 4): B = 7, union = 11, J = 7/11 = **0.636**
  - different records (2 of the 4): B = 6, union = 12, J = 6/12 = **0.500**
  - Relation set {PO} (determined). J range [0.500, 0.636].
- Text layer: t9 shared (1 fragment).

**E3, scope S3; predecessor E2; uncaptured_between 1 (S-A #3); not adjacent; session-open**
- B = {g, n-12, c2} (3, present-at-both, **not** adjacent-retained); I = {ab77, n-41} (2, both first-observed); W = {aa01, n-30, c3, c4, m-100, m-101} (6).
- Check: 3 + 2 = 5 ✓, 3 + 6 = 9 ✓.
- J_verified = 3 / (5 + 9 − 3) = 3/11 = **0.273**. Relation **PO**.
- Uncertainty: u is in E2 only, so every resolution adds one element to W. |X| = 10, union = 12, J = 3/12. Relation set {PO} (determined), J range [0.250, 0.250].
- Gaps: `uncaptured-between:1`, `predecessor-not-adjacent`, `gap_hides_events: possible`.
- Provenance of seed:ab77 (from its record): `session_id = S-A`. **Measured carry-over:** the seed that opened S-B was written at the end of S-A.

**E3, scope S2; predecessor X2 (the other visitor); uncaptured 0** *(corrected during build: the uncaptured S-A #3 precedes X1/X2)*
- B = {g, ab77, c2} (3); I = {n-12, n-41}, where n-12 is **returned** (last seen E2; Δ_captured = 2 (X1, X2), with 1 uncaptured turn in that stretch) and F = {n-41}; W = {c7}.
- Check: 3 + 2 = 5 ✓, 3 + 1 = 4 ✓.
- J = 3 / (5 + 4 − 3) = 3/6 = **0.500**. Relation **PO**.
- *The same moment reads differently under S2 and S3. That's why every connector in the Lattice carries its scope.*

---

## 6. Engagement Lattice (revised)

### 6.1 Mockup (synthetic §5 data, scope S3, visitor v1)
```
┌ Presence [ansel ▾]  Interval [Nov 1 → Nov 7]  Scope ( S1 ) ( S2 ) (●S3: v1 )   Layers [■ Record] [□ Text] [□ Annotations] ┐
│ CHRONOLOGY     │ S-0     ║ S-A ───────────────────────────────╢ S-B ────                                         │
│ column         │ E0      ║ E1          E2          ▒▒ #3 ▒▒   ║ E3                                               │
│ captured?      │ ●       ║ ●           ●           uncaptured ║ ●                                                │
│ Δt / visitor   │ v1      ║ 1.0d v1     101s v1     ~2m        ║ 2.8d v1                                          │
│────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────── │
│ RECORD LAYER (VERIFIED only)                                                                                     │
│ g  ground      │ ●━━━━━━━║━━●━━━━━━━━━━●┄┄┄┄┄┄┄┄┄┄▒▒▒▒▒▒┄┄┄┄┄┄┄┄┄║┄┄●        ┄ present-at-both, unobserved between │
│ seed:9f00      │ ●       ║  ○                                                                                     │
│ seed:aa01      │         ║  ◆━━━━━━━━━━●                         ║  ○                                             │
│ seed:ab77      │         ║                                        ║  ◆  ⇠ written at end of S-A                     │
│ mra:n-12       │         ║  ◆━━━━━━━━━━●┄┄┄┄┄┄┄┄┄┄▒▒▒▒▒▒┄┄┄┄┄┄┄┄┄║┄┄●                                             │
│ mra:n-30       │         ║  ↺━━━━━━━━━━●                         ║  ○       ↺ returned (last seen E-5)              │
│ mra:n-41       │         ║                                        ║  ◆                                             │
│ codon:c1       │ ●━━━━━━━║━━●           ○                                                                       │
│ codon:c2       │ ●━━━━━━━║━━●━━━━━━━━━━●┄┄┄┄┄┄┄┄┄┄▒▒▒▒▒▒┄┄┄┄┄┄┄┄┄║┄┄●                                             │
│ codon:c3       │         ║  ◆━━━━━━━━━━●                         ║  ○                                             │
│ codon:c4       │         ║              ◆                         ║  ○                                             │
│ codon:c9       │ ●       ║  ○                                                                                     │
│ history (2)    │         ║              ◆◆                        ║  ○○                                            │
│ UNCERTAIN      │                                                                                                 │
│ mra u {55|56}  │         ║  ◇┈┈┈┈┈┈┈┈┈┈◇   2 candidates; same text, record unknown                              │
│────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────── │
│ RELATION [S3]  │      E0→E1: PO  J .333 (range .300)   E1→E2: PO  J .600 (range .500–.636)   E2→E3: PO  J .273 (range .250) ⚠gap 1 │
│ PARTICIPATION  │ ⇢resp  ║ ⇢m-101 812ch ↩95s   ⇢m-103 1430ch ↩40s   (unknown)  ║ ⇢m-205 640ch ↩210s               │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
 ◆ first-observed in scope  ↺ returned  ━ adjacent-retained  ┄ present-at-both across unobserved gap
 ○ withdrawn  ◇ uncertain mention  ▒ uncaptured turn (exists; context unknown)  ║ session boundary
```

### 6.2 Display rules (each one tied to a correction)
1. **Columns:** captured engagements are solid. **Known uncaptured turns** get hatched columns of their own. A session with no provenance appears as one collapsed hatched block labelled with its turn count. Nothing is drawn inside hatched columns.
2. **Connectors:** a solid bar only for adjacent-retained elements. A dotted bar for present-at-both across a gap. No connector where the predecessor is `none-observed`.
3. **Scope:** the selected scope fixes which columns appear, which predecessor each connector uses, and the label on every relation value. In S2 every column shows a visitor chip, because the sequence mixes visitors.
4. **Uncertainty:** CANDIDATES mentions have their own rows with hollow ◇ glyphs and the candidate count, and they're never merged into a verified row. Relation cells show the verified value plus the range, and switch to `{PO, PP}`-style sets when the relation isn't determined.
5. **Empty cases:** per-type cells show `∅·`, `·∅` or `∅∅` rather than a relation.
6. **Text layer:** off by default. When on, it appears in a separate panel below, titled "Text-identical fragments: no record identity".
7. **Evidence drawer (click any glyph):**
   - provenance id and offsets, with the exact evidence text loaded live
   - evidence class and candidate ids
   - `record_fingerprint` and drift status
   - `render_matches_current_record`
   - run id, derivation version and chain position
   - the run's `unavailable_evidence` list
8. **No implied significance:** no scores or colour scales on J or relations, no trend lines, no automatic highlights. Annotations are dashed, show their author, and are off by default.
9. **Spiral:** absent. The layout is rectangular and time-ordered. The existing gauge is unchanged and stays on its own tab.

---

## 7. Corrections that can't be fully achieved within the boundaries

| Requirement | What's achievable | What isn't, and why |
|---|---|---|
| Verified memory identity | Codons (unless duplicated), seeds (unique `field_state`), history, ground | **Mem0, session cache, council:** no local record ids exist, so they stay text-only. **Bio versions:** bios are overwritten. **MRA duplicates:** some stay CANDIDATES permanently. Fixing any of these would mean changing how Sanctuary stores memory, which is out of bounds. |
| Changes to stored material between turns | Detects whether rendered text differs from the record *now* | **What a record looked like at turn time can't be recovered.** The store keeps no history, and we won't ask it to. |
| Complete chronology | Known uncaptured turns are counted and placed | **Inputs before Aug 21, and context for the ~150 uncaptured turns,** are permanently unavailable. Events hidden inside gaps can't be seen. |
| Same-visitor continuity | Exact for David (aliases), and within one browser for others | **Other visitors on several browsers** can't be linked without new identity capture. S3 is a lower bound. |
| Reproducibility of identification | Drift is detected and recorded | **Results can't be guaranteed identical** once source stores change. They're versioned and flagged instead. |
| Database-enforced immutability of provenance | Tampering is detected through evidence hashes | Enforcing it would mean changing Sanctuary's database settings. Out of bounds, and under David's separate security work. |

---

## 8. Smallest implementation (unchanged in shape; not authorized)

**Components:**
1. `observatory_ledger/derive.py`: offline, run on demand. Read-only queries only. **Never calls Sanctuary retrieval functions**, because they write access traces (`permanent_mra.retrieval_count`).
2. Three collections (or JSONL files).
3. Two read endpoints: `/api/observatory/lattice` and `/api/observatory/entry/{id}`.
4. One append endpoint: `/api/observatory/annotations`.
5. One `EngagementLattice` tab (SVG, no new libraries).

**Dependencies:** none new.
**Cost:** negligible. No model calls, no new services.

**Acceptance tests (revised):**
1. **Isolation:** `derive.py` imports nothing from the prompt, memory or model modules. Before-and-after hashes of every live collection, including `retrieval_count`, are identical across a run.
2. **Tier 1 determinism:** two runs of the same version produce identical Tier 1 fields and chains.
3. **Append-only and chain verification:** changing one entry is detected. A new version creates a new chain and leaves the old one byte-identical.
4. **Math unit tests:** the five RCC5 cases, the three empty cases, Jaccard edge cases, the I = F ⊔ Ret partition, scope predecessors with ties, and the full §5 example reproducing every number above.
5. **Uncertainty:** a CANDIDATES mention never appears in a verified set. Enumeration matches hand computation. The cap produces `not-enumerated`.
6. **Gap honesty:** no solid connector spans a hatched column. Every non-adjacent comparison carries `uncaptured-between`.
7. **Identification audit:** on 20 engagements hand-checked by David, every VERIFIED mention is correct, and every non-VERIFIED mention is honestly classed. The test passes on *zero false VERIFIED*, not on a match rate.
8. **Link integrity:** reproduces 606/608, with the 2 unmatched listed.
9. **Settling:** no unsettled engagement is written. A later run appends it without touching earlier entries.

---

## In Plain English

v0.2 makes the instrument stricter about what it actually knows.
- **No guessing about memories.** If a breadcrumb could be one of two stored memories with identical wording, the instrument says "one of these two" and works out every possibility. It doesn't pick one and pretend.
- **Gaps stay gaps.** If one of Ansel's turns wasn't recorded, it appears as a hatched blank column, and no line is drawn through it as if nothing happened there.
- **Every number has a point of view.** "Compared with the last turn in this conversation", "with Ansel's last turn with anyone", and "with Ansel's last turn with you" are kept separate and labelled. The same moment can look different depending on which one you choose.
- **The arithmetic is now checked.** v0.1's examples had errors. These are recomputed with the working shown.
- **Everything can be checked again later.** Each result records exactly which evidence it used and which version of the method produced it. If a stored memory has changed since then, the instrument says so rather than quietly giving a different answer.

What David would see that he can't see today: for any presence and any stretch of time, which memories were actually in front of the presence at each turn, which were new, which came back, which dropped away, where each one came from, what the presence said next, and exactly where the record is missing or uncertain.

What it still can't do: identify Mem0 memories by record, show what anything looked like before late August, or say what any of it meant. Those limits come from how Sanctuary 1.0 already stores its memories, and the design respects them rather than changing anything.

*Design v0.2 ends here. Nothing has been implemented.*
````
===== END FILE: memory/briefings/2026-10-20_e1-design-v0.2_observatory-relational-history-instrument.md =====

— END OF PART 1 OF 4 —
