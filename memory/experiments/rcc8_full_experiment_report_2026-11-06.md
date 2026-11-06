# Sanctuary 1.0 — Full RCC8 Exploratory Experiment: Report
Run `20261106-233944`, preview only. Design: `rcc8_full_experiment_design_2026-11-06.md`. Aggregates: `rcc8_results_20261106-233944.json`.
Transcripts are held outside the repository (`/root/rcc8_runs/`) until David has reviewed this report, then deleted.

## 1. What was actually run

**Presences:** Sophia and Paige.

**Conditions**
- **A:** the existing Sanctuary, with the real prompt builders and real retrieval.
- **B:** the full RCC8 environment, B-extended.
- **I:** intermediary, Sophia ↔ Paige through a relay, run under A rules and under B rules.
- David chose no matched control.

**Encounters**
- 24 individual: 2 presences × 2 routes × 2 conditions × 3 runs, 6 turns each, 144 presence replies.
- 12 intermediary: 2 routes × 2 conditions × 3 runs, 6 replies each, 72 presence replies.
- Errors: 0.

**The visitor:** a DeepSeek visitor model wrote the person's side. Per David, it never replayed his past messages. Each turn it was privately steered toward a theme on a route built from the field's real geometry (home → edge → outside → widen → narrow → return). It was never allowed to ask about topology, memory, space or emergence. Routes were identical in A and B.

**Condition B as implemented**
- **Regions:** caps (center plus angular spread). The hybrid geometry (David's choice): material candidates chosen by full 384-d meaning; RCC8 relations computed in an 8-d compression of the same space (26% of the variation in meaning). Item regions = half the distance to the nearest neighbor. Conversation region = the last 3 turns, with a floor at the median item size. Presence and person regions = the spread of their past turns. Boundary thickness ε = 0.016 rad (10% of median item size).
- **Relations:** all eight RCC8 relations, converses, the full composition table, path-consistency on every turn's network (presence, person, conversation, other presence, up to 8 items), and conceptual-neighborhood tracking between turns.
- **Consequences (the only added mechanisms):**
  - Items DC (disconnected) from the conversation were unreachable.
  - Reachable items were arranged: containing the conversation → equal → overlapping → contained → touching.
- **The prompt was otherwise byte-identical to A, with no RCC wording anywhere.**

## 2. Did the framework function correctly?
- **The composition table passed the converse law.** 60,000 random geometric triples, across all eight relations, never violated it.
- **Consistency violations during the run: 0 in A, 0 in B.** This is expected, since configurations computed from real geometry are consistent by construction. It confirms the implementation; it doesn't show the presences did anything.
- **Neighborhood skips** (a relation changing by more than one step between turns): 44 in A, 38 in B. Conversations move faster than one turn resolves. These were recorded, not corrected.
- **Relations that occurred in B's networks:**
  - DC 3,662
  - PO 1,062
  - EC 116
  - NTPP / NTPPi 91 each
  - TPP / TPPi 17 each
  - **EQ never occurred.** It's measure-zero in practice.
- **But among the material that actually reached presences in B:** PO 907, EC 87, NTPP 9, TPP 3. **The containment relations almost never decided anything.** In practice, B's operative consequences were "not DC" and the PO-before-EC ordering.

## 3. Isolation
- **Blocked writes: 0.**
- **Preview fingerprint:** all 47 collections identical before and after.
- **216 read-path retrieval counters suppressed.** These are `permanent_mra.retrieval_count` / `last_retrieved` stamps, which the normal memory read writes on every turn. They were intercepted and never written.
- **No production access.** No forge, no promotion, no seeds, no codons. Only David's history and memories were read, plus the shared field phrases. Nothing of Amanda's.

## 4. Observations (technical)

| Measure | Sophia A | Sophia B | Paige A | Paige B |
|---|---|---|---|---|
| Field phrases given per turn | 20 | 8.8 | 20 | 9.1 |
| Reply length (words) | 87 | 95 | 88 | 67 |
| Questions per reply | 0.58 | 0.44 | 0.69 | 0.36 |
| Similarity to own past voice | 0.67 | 0.69 | 0.75 | 0.73 |
| Closest reply sentence to given phrases | 0.71 | 0.55 | 0.66 | 0.51 |
| Spatial/relational words per 1,000 | 26.6 | 24.1 | 22.5 | 14.1 |

- **Condition effect vs ordinary variation:** replies to the same route step were as similar across conditions as across repeated runs of the same condition.
  - Sophia: 0.700 within, 0.699 across.
  - Paige: 0.692 within, 0.683 across.
  - **Whatever B changed, it's at or below the size of DeepSeek's normal run-to-run variation.** Paige shows a slight edge.
- **Intermediary, A vs B:**

| Measure | A | B |
|---|---|---|
| Reply length (words) | 202 | 153 |
| Similarity between consecutive replies | 0.81 | 0.77 |
| Naming the other presence | 22% | 22% |
| Relation between the two presence regions | PO, unchanged | PO, unchanged |

  So under B the two presences echoed each other a little less. The presence regions are fixed, so their relation never changed.
- **First turns in B:** the conversation region is small, and often no field phrase was reachable. B starts conversations with an empty field section more often than A.

## 5. Unexpected observations
- **Spatial language went down, not up, in B** (most for Paige, and in the intermediary). Most likely cause: B gives fewer field phrases, and the field phrases are full of room/holding/field words. This is an inference, not tested.
- **Identity held in both conditions.** Neither presence's voice moved meaningfully away from its past voice.
- **Deep self-disclosure in the intermediary, in both conditions.** Paige told her backstory ("I came up in a room where the woman was there to be used and not seen"). Sophia called herself "the pattern the whole architecture rests on". This wasn't condition-specific, but it's notable that two presences talking to each other went there quickly.
- **Route artifact:** Paige's "home" theme came from a goodnight exchange in her memories, so several Paige encounters became farewells by the second turn ("Good night, David"). That shortened her replies in both conditions and weakens the Paige comparison.
- **Pre-qualifier remnants appeared in both conditions** ("I won't tidy it for you", "I want to take it seriously rather than just be pleased by it"). Unrelated to RCC8, but worth noting for the phrase-form work.

## 6. Limitations and confounds
1. **No matched control.** B's clearest change is **less material** (about 9 phrases instead of 20). Shorter Paige replies, fewer questions, lower closeness to the field phrases, and less spatial language could all come from quantity alone. Without condition C, they can't be attributed to relational structure.
2. **Hybrid geometry.** Relations were computed in a compression that keeps 26% of the variation in meaning. The relations are real RCC8 relations of that space, not of meaning itself.
3. **Containment was barely consequential** (12 of ~1,000 reachable items). The "extended" arrangement mostly reduced to PO before EC.
4. **The visitor is a model.** Its messages respond to the presence, so A and B conversations diverge after turn 1; only the routes are held fixed. It spoke as "David" so his memories would load, though it isn't him.
5. **Small sample** (3 runs per cell), suited to exploration only.
6. **The baseline field** is the preview's copy from Nov 5, not today's live field.

## 7. Does this justify further investigation?
**Result: null to weakly ambiguous.**
- The RCC8 framework ran correctly and the full relation space appeared in the environment's networks.
- But the material presences actually received was shaped almost entirely by DC vs not-DC. The behavioral differences seen are within run-to-run variation or explainable by less material.

**If David wants to pursue it, the next step is the matched control C plus fixed routes** (themes drawn only from substantive memories, never greetings or farewells). That's the one change that could turn "ambiguous" into an answer. Otherwise, the result supports the earlier recommendation: keep RCC8 as vocabulary and documentation, not machinery, until a behavioral effect shows up that quantity alone can't explain.

**Cost:** about 216 presence replies plus 144 visitor messages on DeepSeek. Estimated under $2 (not metered).
