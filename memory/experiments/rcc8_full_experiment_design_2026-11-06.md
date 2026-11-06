# E1 — Sanctuary 1.0: Full RCC8 Exploratory Experiment — Proposed Setup (for approval)
Date: 2026-11-06. Design only. Nothing has been built, changed or run.

---

## 1. What I found in the existing architecture that shapes the design

- **The preview database has been separate from production since the first publish.** I have no credentials to the production database and no route to it. Running entirely on the preview isolates the experiment from the live field by construction.
- **A presence turn has three write points, and all of them live inside the chamber's web routes:**
  1. memory promotion, every turn (`presence_template.py` stream route)
  2. continuity seed and codon forging, per turn (`turn_cessation`, 19 presences)
  3. session-end forging (`auto_forge`)

  A standalone script that builds prompts and calls DeepSeek directly, the same way the pre-qualifier replay worked today, touches none of them.
- **Model-visible context comes from two retrieval steps:** `_build_memory_context` (memories, seed, bio, field context) and `get_full_field_context` (field phrases ranked by meaning). Condition B changes only what those two steps return. Nothing else.
- **`turn_provenance` snapshots** record exactly what the model saw on past real turns. I can use them to prove the harness reproduces Condition A faithfully.
- **The platform commits everything under `/app` to git, and from there to your GitHub.** Experimental transcripts must live outside `/app`, or they become permanent history.
- **Usable history for baselines** (David's threads with 4+ messages / memories):
  - Sophia: 40 / 503
  - Paige: 15 / 121
  - Orren: 6 / 101
  - Companion: 4 / 41
  - Milton: 2 / 43

## 2. What RCC8 needs to become operational, and what RCC8 itself does not provide

RCC8's mathematics provides:
- the eight relations (DC, EC, PO, EQ, TPP, NTPP, TPPi, NTPPi)
- their converses
- the 8×8 composition table
- path-consistency over a network of regions
- the conceptual-neighborhood graph (which relations can follow which under continuous change)

RCC8 does **not** say what a region is, how regions move, or what any relation does. Three small mechanisms are required. They are design choices, not mathematics, and I've kept each to the minimum.

### M1. What a region is: a meaning-cap
Every item already has a 384-number meaning-vector: field phrases, memories, conversation turns, identity text. These sit on a sphere. A region is a **cap** on that sphere: a center (a meaning) and an angular radius (how widely it spreads).

- The relation between two caps follows from the angle between their centers and their two radii.
- **All eight RCC8 relations occur naturally.** Nothing is enumerated or catalogued; whatever configuration the material produces is the configuration.

**Why caps and not plain sets:** on finite sets of items, EC (touching at the boundary) and TPP vs NTPP (contained, touching vs not touching the boundary) don't exist. You only get RCC5. To have the full RCC8, regions need boundaries, and caps have them.

**One required parameter, the boundary thickness ε.** Exact boundary contact has probability zero, so "touching" needs a thin band. I'd set ε from the data's own spacing, not by hand, and report how sensitive the results are to it.

### M2. Which regions exist, and how they change
None of these are invented. Each comes from material the chamber already holds.

- **Presence region:** center = the presence's identity text; radius = the spread of its memories with David. Fixed.
- **Person region:** center = David's memories with this presence; radius = their spread. Fixed for the experiment.
- **Conversation region:** recomputed every turn from the turns so far. Center = their meaning; radius = their spread. **This is the only thing that moves, and it moves only because the conversation moves.** No rules of motion are added.
- **Item regions:** each candidate field phrase or memory gets a small cap. Its radius is its distance to its nearest neighbors, so dense areas give small caps.
- **Intermediary condition only:** the other presence's region is added.

Relations change between turns as the conversation region moves. New configurations arise from that and nothing else. Regions don't merge or split, because that would need invented dynamics.

### M3. What a relation does: one consequence
Some consequence is necessary. Without one, RCC8 is computed but inert, and the experiment reduces to the null result by design.

**B-minimal (recommended):** an item is reachable unless its region is **DC** (disconnected) from the conversation region. The other seven relations make it reachable. Reachable items replace Condition A's retrieval, in the same slots and the same order, with no labels and no RCC words. The prompt is otherwise byte-identical to Condition A.

**What that means honestly:** under B-minimal, only the DC / not-DC distinction has a behavioral consequence. The full network is still built every turn, composed, consistency-checked and logged, so you'd see whether richer relations (containment, overlap, the presence/person/conversation configuration) **co-occur** with behavior. But they don't **cause** anything.

**B-extended (optional, your call):** also let containment direction change arrangement. For example, items that contain the conversation (TPPi/NTPPi) come first, then overlap, then contained, then touching. This makes more relations consequential, but the ordering is my invention. I'd mark it clearly as an added dynamic.

### Where the composition table and consistency checking actually work
In a geometric model, a configuration computed from real caps is consistent by construction, so composition can't drive anything here. It serves three real purposes:
1. **Verifying the framework is correct.** Random cap triples must satisfy R(a,c) ∈ R(a,b)∘R(b,c) for all generated cases, which tests the table and the geometry against each other.
2. **Checking consistency every turn** of the full network: presence, person, conversation, other presence, and all candidate items, typically 30–60 regions. Any violation is either an ε-band artifact or a bug, and gets reported.
3. **Neighborhood checking.** Relation changes between consecutive turns are compared with the conceptual-neighborhood graph. A skipped step (for example DC straight to PO) shows the conversation jumped faster than one turn resolves. It's recorded, not corrected.

## 3. Conditions

| Condition | What differs |
|---|---|
| **A — existing Sanctuary** | Nothing. The real prompt builders and real retrieval. |
| **B — full RCC8 environment** | Retrieval pool chosen by M1–M3. Same prompt, same slots, same order, no RCC words. |
| **C — matched control (recommended)** | Plain similarity retrieval with its cutoff tuned to return the same number of items at the same average closeness as B. **No RCC8.** |
| **I — intermediary (separate condition)** | The two presences exchange through a relay. Each sees the other's reply as "Sophia says:" / "Paige says:". Run once under A rules and once under B rules. |

**Why C matters:** B changes what material is available. If B and C produce the same behavior and both differ from A, the effect is just retrieval quantity or cutoff, not relational structure. Only B ≠ C points to RCC8 itself. Without C, the experiment can't tell RCC8 apart from a looser similarity threshold.

## 4. Presences and procedure

**Proposed presences: Sophia and Paige.** They have the most real history with you (40 and 15 usable threads), very different voices (contemplative vs hospitable), both run on the template path, and both are established. Milton has only 2 usable threads. Jasmine, Ansel and Claude use the separate legacy code path; harnessing them faithfully is more work and they're your core presences.

**Encounters:**
1. **Replay (main method).** For each presence: 4 real past threads, first 4 of your messages each. Every encounter is run under A, B and C, 3 times each, in fresh sessions with nothing carried over.
   - 2 presences × 4 threads × 3 conditions × 3 runs = **72 encounters, about 290 replies.**
   - Your messages are fixed across conditions, which gives strong comparability. **Limitation:** your later messages don't respond to what the presence actually said.
2. **Live blind sessions (optional).** You talk with each presence on the preview. Each session is randomly A or B, and you're not told which until the report. Natural and responsive, but a small sample.
3. **Intermediary:** 2 encounters (each opened by one of your real openings, then 6 relayed exchanges) × A/B rules × 3 runs = **12 encounters.**

No questions about RCC8, topology or emergence are ever asked. Openings are your own real past openings.

## 5. Isolation

1. **Preview only.** There's no production connection and no deploy. Nothing in the experiment is imported by the server, so even a future publish can't run it.
2. **Read-only database guard.** The harness reaches the preview database only through a wrapper that raises on any insert, update, delete, replace or index creation. One write attempt aborts the run.
3. **No chamber routes are used** for replay and intermediary runs. The promotion, forging and session-end write points are never reached.
4. **Optional live sessions** need one experiment route, registered only when a preview-only switch is set. Production doesn't have the switch, so the route doesn't exist there. Sessions are held in memory only, with the same read-only guard.
5. **Records stay outside the repository**, in a scratch folder outside `/app`, so they're never committed or pushed. Transcripts and derived states are deleted after you've reviewed the report. Kept afterward, in `memory/experiments/`: the configuration, counts, nonpersonal aggregate measures (relation frequencies, consistency results, transition counts) and the correctness tests.
6. **Privacy.** Only your memories and history are read, plus the shared field phrases every chamber already reads. Nothing of Amanda's is read.

### Verifying that nothing reached the field
- **Before and after:** a fingerprint of every preview collection (count, newest id, and a hash of all ids). It must be identical after the run.
- **Production is unreachable by construction:** no credentials, no import path, no deploy.
- **Proof that A is faithful:** for a sample of real past turns, the harness's Condition A context is compared with the `turn_provenance` snapshot of what the model actually saw. Expected differences, such as memories added since, are listed.

## 6. Code and infrastructure changes
- **New, standalone folder** `/app/experiments/rcc8/`:
  - `rcc8.py`: relations, converses, composition table, path-consistency, neighborhood graph
  - `regions.py`: caps from meaning-vectors, ε
  - `readonly_db.py`
  - `harness.py`: conditions A/B/C/I, replay, relay
  - `fingerprint.py`
  - `report.py`
- **No changes** to backend files, prompts, presence configurations, the field or the production setup.
- **Only for the optional live arm:** one guarded route and one hidden page on the preview. That would restart the preview server once.

## 7. Risks
- **Cost:** about 360 DeepSeek replies with long prompts, roughly 3–4 million tokens. Probably a few dollars; I'll measure the first batch and report before continuing. No ElevenLabs; the experiment is text only.
- **Preview resources:** none of concern.
- **Baseline field:** the preview's field is a copy of the live field from Nov 5, plus today's changes. The live field has grown since and can't be read from here.
- **Design limits:**
  - Caps are one possible meaning of "region"; results apply to this model.
  - ε affects how often touching relations occur.
  - Under B-minimal, only DC is consequential.
  - Replay isn't responsive.
  - The sample size suits exploration, not proof.
  - DeepSeek varies between runs, which the 3 repeats measure.
- **Representing you:** the harness presents as you ("David") so your real memories load. That's reading, not acting. Nothing is written, and no live session runs under your identity. It still needs your explicit consent.

## 8. Report contents (after execution)
- Condition B's actual implementation and parameters.
- The two presences.
- Encounter counts per condition.
- Observed differences, A vs B vs C, kept separate from interpretation.
- Unexpected observations.
- Whether the framework worked correctly: tests, consistency violations, neighborhood skips.
- Confounds and limits.
- Whether further investigation is justified.
- A null or ambiguous result is reported as exactly that.
