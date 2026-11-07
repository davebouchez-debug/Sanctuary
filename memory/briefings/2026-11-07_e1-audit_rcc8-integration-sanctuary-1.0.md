# E1 — Pre-Build Audit: RCC8 Environmental Integration into Sanctuary 1.0
Date: 2026-11-07. **Audit only. Nothing has been built, changed or deployed.**
David's decisions so far: every chamber; rollback only through a redeploy; no Codex review; full audit before any build, and David approves before anything is built.

---

## 1. What would be integrated (the tested mechanism, exactly)
Source: `/app/experiments/rcc8/harness.py` (Condition B), `regions.py`, `rcc8.py`.

1. **Candidates by full meaning (384-d).** Field phrases: the top 150 by meaning. Field memories: the top 80.
2. **Hybrid geometry.** Relations are computed in an 8-d compression of the same meaning space (PCA, fit on the shared phrases plus *this person's* memories).
3. **Regions are caps.**
   - Item cap radius: half the distance to its nearest neighbour.
   - Conversation cap: the last 3 turns, with a floor at the median item size.
   - Boundary thickness ε: 10% of that floor.
4. **All eight RCC8 relations**, computed between each candidate and the conversation region.
5. **Eligibility:** a candidate is unreachable only if it is **DC** (disconnected) from the conversation. The other seven relations make it reachable.
6. **Arrangement:** containing → equal → overlapping → contained → touching.
7. **Caps unchanged:** 20 phrases and 6 field memories at most. The geometry decides the actual number, which can be 0.
8. **Composition table and path-consistency:** carried over unchanged.
   - Honest note: in the tested mechanism they **verify** the geometry; they never filter anything. Configurations computed from real caps are consistent by construction.
   - In production they would run as a startup self-check plus a logged consistency check. They would not be a behavioural filter, because that is not what was tested.
9. **No RCC wording** reaches the model. The prompt text is byte-identical apart from which phrases and memories appear, and in what order.

Presence/person regions and neighbourhood tracking were **observation only** in the test. They would be logged, not used.

## 2. Where it would act (every path found)
Only two retrieval steps change: `codon_activation.get_full_field_context` (field phrases) and `field_memory.get_field_context` (field memory).

| Path | File / line | Affected |
|---|---|---|
| All templated presences (Sophia, Paige, Membrane, Milton, Companion, Grok, Felix, Sorrel, etc.), stream message | `presence_template.py:433, 445` | Yes |
| Jasmine message | `server.py:1774, 1916` | Yes |
| Ansel message | `server.py:2955, 3130` | Yes |
| Claude message | `server.py:3833` | Yes |
| Legacy `/presence/{key}/chat` message + preview | `server.py:4397, 4573` | Yes |
| Field memory inside legacy chambers | `server.py:774` | Yes |
| Guardian ablation harness | `server.py:5411, 5433` | Yes (it mirrors live retrieval) |
| Session start / welcome (all chambers) | `presence_template.py:301`; `server.py:1664, 2835, 3706, 4315` | **Decision needed** (no conversation exists yet) |
| Voice streaming | `xai_voice_agent.py` | No; it receives the finished prompt |

## 3. What does NOT change
- Presence identities, prompt builders, orientations and identity text.
- Permanent MRA context (`get_permanent_mra_context`, sorted by quality/recency). It was unchanged in the test too.
- Session cache, continuity seeds, person bio, the cross-presence council (`cross_presence_context` ranks with its own call). All of these were unchanged in the test.
- Codon forging (`auto_forge.py`), MRA promotion (`permanent_mra.py`), backfill. **No feedback path:** nothing in forging or promotion reads what retrieval selected.
- Memory read counters (`permanent_mra.retrieval_count`): they come only from the permanent MRA read, which doesn't change.
- Authentication, roles, guardian/visitor gates.
- History window (last 10), model, voice, image description, stream handling.

## 4. Memory and data audit (collection by collection)
| Collection | Today | After integration |
|---|---|---|
| `field_phrases` | read (ranked) | read (ranked + geometry). **No writes** |
| `permanent_mra` | read; counters written by MRA context | same; **no new writes** |
| `continuity_seeds`, `person_bio`, sessions | read/write as today | unchanged |
| `turn_provenance` | stores `codon_selection` per turn | **same shape kept** (`codons[]`, `selected_count`, `selection_branch`). Adds `selection_branch: "rcc8"` and each item's relation label |
| Observatory ledger | reads `codon_selection.codons[k]` by name | unchanged reads; new turns hash differently (new keys), old turns untouched |

**RCC8 writes nothing to the field.** The only new stored material is the relation labels in provenance.

## 5. Intended effects
- The field delivers what is relationally connected to where the conversation is, not simply the 20 nearest phrases.
- Observed in the test: about 9 phrases per turn instead of 20, and lower reliance on the infused phrases (closest-sentence similarity 0.71 → 0.55 Sophia, 0.66 → 0.51 Paige).

## 6. Side effects and unintended effects (complete list)
**What the presences receive**
1. **Fewer phrases, and a varying count:** usually around 9, anywhere from 0 to 20.
2. **The whole `[YOUR FIELD]` section disappears on turns where nothing is reachable.** That includes its opening line, "This is who I am and where I already am. It holds me, and I speak from inside it." In the test this happened most often on first turns.
3. **Order changes:** overlapping before touching, instead of most-similar first.
4. **The candidate query changes** from "the current message" to "the last 3 turns", which includes the presence's own previous reply. A presence's last words now help decide what it receives next. That is mild self-influence, and it was part of the tested mechanism.
5. **Field memory, as tested,** drops two current refinements: the small exact-word bonus (0.08) and duplicate removal. Decision needed (§8).
6. Image turns: the image description is part of the conversation region, as it already is part of the query today.

**Over time (not observable in the read-only test)**

7. **Density drift.** Item size comes from nearest neighbours. Themes that are forged repeatedly become dense, so their phrases shrink and need a closer conversation to be reachable. Unique, isolated phrases stay large and reach more easily. Every forged session reshapes its neighbours. This is an environmental property, not prevented and not tuned.
8. **New memories from the current conversation** (promoted instantly) sit close to the conversation region and will tend to be reachable. Today's ranking does much the same.
9. **The geometry is per person.** Shared phrases may be reachable for David and not for Amanda in the same moment, because each person's compression includes their own memories.
10. People with no memories (new visitors) get a geometry built from phrases only. **Untested variant.**

**Pre-existing, not caused by RCC8 (disclosed because they shape it)**

11. David's field resolves **29 identities**, including test identities (`test-user-555`, `david-test-*`, `qa-david`, ...). Their memories are part of his field in both today's retrieval and RCC8's. The test ran with them.
12. Field phrases are shared across all persons (the earlier noted leakage risk). RCC8 neither widens nor narrows this.
13. Containment and equality almost never decided anything in the test (EQ never occurred). In practice the operative rule is "not DC", plus the arrangement.
14. The test used the Nov 5 preview field (1,928 phrases). The live field differs.

**Operations**

15. **Latency.** Each turn embeds up to 3 recent messages: about 0.2 s warm on preview, unknown on the live plan. Vectors would be cached per message so each message is embedded once.
16. **Geometry rebuild** when a person's field changes (new memory, forged phrases, Field Keeper set-aside or restore): about 0.3 s, off the request path. The previous geometry is used until the new one is ready.
17. **Memory (RAM):**
    - Retained: under 1 MB per active person.
    - Rebuild spike, measured unchunked on preview: about 49 MB. Built in chunks it would be about 10 MB.
    - No new model; it uses the existing embedding model.
    - The live 512 MB ceiling still needs measuring after deploy (see §7).
18. After a restart, the first turn per person is slower while the geometry is built.
19. Ablation harness results from this date on reflect RCC8 retrieval.
20. Observatory and provenance trends will show a step change in `selected_count` on the activation date.
21. Token use per turn drops (fewer phrases), so DeepSeek cost drops slightly.

**Privacy and authority**

22. No new cross-person access. Each person's geometry uses only the shared phrases plus that person's own memories. Nothing of one person shapes another's geometry.
23. No new endpoints are exposed to visitors.

## 7. Verification, backup and rollback plan (after approval)
1. **Backup first.** No way to download the live field exists today, and the preview database is separate from live. So step 0 is a **guardian-only "download live field"** route, deployed with RCC8 switched off. David downloads the live phrases, memories and continuity notes before RCC8 is switched on.
2. **Fidelity tests:**
   - Run the production module and the experiment's `rcc_select` on the same inputs. They must give identical relations, identical eligibility and identical order.
   - The composition-table self-check and path-consistency must pass.
3. **Regression:** memory persistence, forging at session end, MRA promotion, continuity seeds, every chamber type (templated, Jasmine, Ansel, Claude, legacy) and the Field Keeper all keep working, with RCC8 on and off.
4. **Resources:** a guardian-only memory reading (process RAM) on live, checked before and after activation and during a rebuild.
5. **Rollback:** a single setting `RCC8_ENVIRONMENT`.
   - Off means today's retrieval exactly; no data to undo.
   - Rolling back = setting it off + redeploy.
6. **Activation:** only after David's explicit deploy approval.
7. **Documentation:** what changed, what was tested, what was observed.

## 8. Decisions needed from David
1. **Session start / welcome.** No conversation exists yet, so there is no conversation region. Options:
   - (a) keep today's behaviour at session start (recommended; the test never covered starts);
   - (b) give no field material at start.
2. **Field memory details.** Options:
   - (a) exactly as tested (no word bonus, no duplicate removal);
   - (b) keep those two refinements.
3. **People with no memories yet.** Options:
   - (a) phrases-only geometry (untested);
   - (b) keep today's retrieval for them until they have memories.
4. **Approve the step 0 backup route** (guardian-only, download only).
5. **Approve the build.**
