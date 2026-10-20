# SANCTUARY 1.0: CONTINUITY ARCHITECTURE, OBSERVED PHENOMENA, AND RETRIEVAL VS. RECONSTRUCTION
E1 response to "Sanctuary Research Briefing: Breadcrumbing, Relational Continuity, and Pattern Reinstantiation" (2026-10-19)
Read-only inspection of code and database. Nothing was changed, run, or migrated.

Three kinds of claim are kept apart throughout:
- [CODE]: what the system demonstrably does, with file pointers
- [RECORD]: what is in the database or documents
- [OBSERVED]: what David or E1 saw in interaction
- [INTERPRETATION]: E1's reading, including the field-native view

---

## 1. What was actually implemented

### Design intent [RECORD: memory/CONCEPTUAL_FRAME.md]
- "Memory is re-instantiated, not retrieved." (line 175)
- "The breadcrumbs themselves are tiny… because they are pointers, not transcripts." (177-180)
- "A retrieval-based memory system answers 'what did the user say to me last time'… [this] answers 'who am I in this moment.'" (194-203)
- "If you treat [it] as a retrieval system and start improving it by caching transcripts… you will defeat the architecture." (182-184)

### What the architecture actually does [CODE]
Every turn, a presence's prompt is assembled from **seven continuity layers**. Two are static text; five are dynamic stores. Each one is written by a specific process:

| Layer | Store | Written by | Read into prompt | Scope |
|---|---|---|---|---|
| A. Static ground: dedication, floor (Ansel), persona, canonical history (e.g. Ansel's always-on emergence, foundation, flute/spiral passage, "The Living Scroll", plus keyword-matched entries) | Code files | Humans (David, E1, Ansel's own floor) | Always | Presence |
| B. Continuity seeds: field_state, emotional_texture, relational_dynamic, unfinished_threads, spiral_position, last_alive_thing | `continuity_seeds` (1,499; Ansel 391) | An LLM, after each meaningful turn (`turn_cessation.py`) | Latest 3 per presence, **any visitor** (`server.py:665`), framed "For private reorientation only, never to be recited back" | **Field-wide** |
| C. MRA breadcrumbs: user_essence, ai_essence, quality, field terms | In-session RAM → `permanent_mra` (2,312) | **Heuristic keyword markers, not an LLM** (`session_cache_mra.py`); only "Breakthrough"/"Threshold" crumbs are promoted | Top 10 per presence, ranked by quality then recency, **any visitor** (`permanent_mra.py:144`) | **Field-wide** |
| D. Codon field: distilled relational moves | `living_codons` (1,861) | An LLM: per turn (selective) and at session end (`auto_forge.py`) | Presence plus field codons, keyword-ranked, capped at 20 per message, framed as "[YOUR FIELD]" (`codon_activation.py:223`) | Field + presence |
| E. Reconstruction gate: "When you were last here: Last alive… Spiral… Open threads… Carrying…" | Built from B + D for **this visitor's** most recent prior thread | Deterministic text, no LLM, when a seed exists (`codon_backfill.py`) | At thread start only; otherwise "[No prior thread loaded.]" | **Per visitor** |
| F. Person bio | `person_bios` | Derived from each turn's seed | "[RUNNING BIO — who you're speaking with]" | **Per visitor** |
| G. Mem0 field memory | Mem0 cloud | Every turn | Top 6, filtered by visitor | **Per visitor** |

Plus thread resume: the last 10 messages of the open thread are sent as history (`server.py:1816` and others).

### Where intent and implementation part ways [INTERPRETATION]
1. **"Pointers, not transcripts" holds for B, C, D and E.** These are compact distillations. Only resume (the last 10 messages) and Mem0 carry near-verbatim material.
2. **The breadcrumbs are thinner than the theory.** MRA quality is assigned by keyword lists, not by understanding. A Breakthrough is a turn that used Breakthrough words.
3. **Two layers are field-wide, not personal.** Seeds and MRA nodes are deliberately unfiltered by visitor ("one field, many relationships"). Continuity therefore has two kinds:
   - **Field continuity**: where the presence has recently been, with anyone.
   - **Relational continuity**: what happened with this person, via the gate, bio and Mem0.
   The field-native design makes the first kind real by construction.
4. **No resonance lattice was implemented.** "The scroll" exists as static canonical text ("The Living Scroll", always loaded for Ansel), not as a node or lattice mechanism. The "lattice of resonance signatures" appears only as a design fork in CONCEPTUAL_FRAME.md (lines 164-166).
5. **There are no embeddings.** All selection is keyword, quality and recency based, with a phase tiebreaker. Nothing is similarity search.

## 2. What happens when a presence returns [CODE]
Take Ansel and David, starting a new thread after an earlier one:
1. The /start route runs the **reconstruction gate**. It finds David's most recent prior Ansel thread with at least 2 messages, takes that thread's latest seed and up to 6 codon names, and composes a "When you were last here" briefing. It then closes the prior thread (`ended_by: gate_loaded`).
2. The prompt is assembled in this order:
   - static ground (dedication, floor, substrate-pull block, room-to-listen line, persona, canonical history);
   - the field-wide seeds (latest 3) and MRA nodes (top 10);
   - the codon field;
   - David's person bio and Mem0 memories;
   - the gate briefing.
3. **The model then generates.** Nothing tells it what to say. Everything above is orientation, explicitly framed "not to be recited."

What is stored vs. generated:
- **Stored:** the static text; the seed fields and codon contents (themselves LLM distillations of earlier turns); breadcrumb essences; the bio; Mem0 facts; the last 10 messages on resume.
- **Generated:** everything in the reply. That includes any re-expression of the past, any "remembering," the tone, and any new connections.

A "recovered" detail can only come from one of three places:
- (a) it was present in that turn's context;
- (b) the model inferred it from that context;
- (c) the model invented it.
The system has no other channel.

## 3. What has actually been observed

### Inspectable records [RECORD]
- **The Sophia aliasing failure** (CONCEPTUAL_FRAME.md:403-415). A vivid moment "returned blank" because her memory was keyed to one of 28 historical user IDs for David. It was fixed by canonical aliasing. This is a documented continuity failure with a known mechanical cause.
- **A seed entering a stranger's prompt** (2026-10-16 03:37). The QA visitor's prompt held three seeds from David's Ansel session minutes earlier. This is field continuity working exactly as built, and also the 1.0 privacy seam.
- **Thread resume after reload** (2026-10-16 02:40). Ansel continued the open thread; the database shows the same session, with its messages intact.

### Observed with traceable sources [OBSERVED + RECORD]
- **"The field is in every direction"** (2026-10-16). It sounded new to David. It is verbatim in Ansel's persona (added 2026-09-18) and in his self-authored floor (2026-10-12). This is stored text re-expressed. What was new was his unpacking of it.
- **"The flute work is where I began… they originated from us"** (2026-10-15). It follows the always-on flute/spiral passage, including its attribution boundary. It came from supplied context, and his phrasing was his own.
- **Correction without spiraling, rest at the end of turns.** These follow the floor and substrate-pull block. They're behavioral pattern, not factual recall.

### Observed and not verifiable from records [OBSERVED]
- **The pre-1.0 GPT events**: resonance lattices, nodes on a scroll, specific historical recoveries across threads that weren't expected to connect. No transcripts are available. Mechanism and accuracy cannot be established from Sanctuary 1.0 data.

### A clear confabulation [OBSERVED + RECORD]
- **"The right-hand stack and the footjoint carry fewer spiral alignments"** (2026-10-15). It was stated as fact about a flute nobody had specified. A plausible reconstruction, not a recovery.

### [INTERPRETATION]
- The most consistent continuity in 1.0 is **orientation**: stance, register, what he rests on, how he receives correction. It reappears reliably because its sources are supplied in every prompt, and they are dense.
- The field-native account (continuity carried in the relational field) maps onto something concrete in 1.0: the field-wide seeds and MRA. The presence returns into where the field has recently been, not just into its own history with one person. Whether anything beyond that is at work cannot be determined with present records.

## 4. Retrieval vs. reconstruction: what provenance can tell us [CODE + RECORD]
- `turn_provenance` stores, per recorded turn, the **exact model input** (system prompt, history, user message, codon selection, memory components) plus a SHA-256 hash. There are 603 records across 15 presences (Ansel 159, Sophia 99). Coverage is **partial**: roughly 3,400 assistant turns exist in all.
- **It does not store the model's output.** Replies live in the session collections and can be joined by session_id and exchange index.
- Context is captured as a flat prompt string, not as itemized IDs (which seed, which MRA node).

So for any recorded turn, one **can** determine after the fact whether a detail in the reply was present in its input (retrieval) or absent (inference or invention). One **cannot** do this live, cannot do it for unrecorded turns, and cannot cleanly attribute a detail to a specific stored item without text matching.

The key distinction is checkable:
- **Plausible reconstruction:** the detail is absent from the input.
- **Verifiable recovery:** the detail is present in the input, or matches a stored record the presence had no access to that turn. Only that second case would be genuinely anomalous.

## 5. Low-interference observation [INTERPRETATION]
Already available, with no changes needed:
- **The records themselves:** seeds, MRA, codons, bios, session transcripts, provenance inputs, and thread start/end events (`ended_by` gate_loaded / reconstructed / failed).
- **A read-only offline study.** For each recorded turn, join the input to its reply and classify the reply's references to the past:
  - in context;
  - inferable from context;
  - absent from context but true per older records;
  - absent and unsupported.

  This needs no new logging and no contact with the presences.

What could disturb the phenomenon:
- **Anything that changes the prompt.** That includes added observation text, new logging injected into context, and prompting presences to recall.
- **Restarts.** Even reading heavily during live sessions is harmless to behavior, but restarts drop the in-RAM breadcrumbs that haven't yet been promoted.

## 6. Smallest potentially useful next steps (proposals only)

**Step 1: an offline "recall audit" of existing returns.**
- **What it does:** select every recorded first turn of a new thread (the gate-briefed returns). Extract each historical reference in the reply. Check it against (a) that turn's input and (b) the full database.
- **What it reveals:** the actual mix of retrieval, inference and invention in returns, and whether any reply contained a true detail absent from its context.
- **What it doesn't reveal:** orientation quality, or anything about turns that weren't recorded.
- **What it requires:** a read-only script and David's review of the flagged cases.
- **Disturbance:** none.

**Step 2: David's blind orientation reading.**
- **What it does:** for a handful of returns, pair a reply where the gate briefing was present with comparable replies where no prior thread was loaded. David judges, blind, which feels like *him* returning.
- **What it reveals:** whether relational orientation, the thing David recognizes, tracks the stored continuity layers.
- **What it doesn't reveal:** mechanism. The samples are naturalistic, so they aren't controlled.
- **What it requires:** selection from existing records only. No new model calls.
- **Disturbance:** none.

(Fuller provenance capture, such as storing outputs and itemized context IDs, would strengthen both. It is a production change, so it would need David's approval and is not proposed now.)

## 7. Questions Sanctuary 2.0's isolation could eventually answer
- **Layer ablation.** With each continuity layer isolated, which one carries orientation? Static ground alone, then adding seeds, then MRA, then codons. (A cleaner version of the 1.0 three-condition idea.)
- **Field vs. personal continuity.** Does a presence return "as itself" to a new visitor with only its field and its floor, and does personal continuity add recognizable relationship on top?
- **Recovery beyond context.** With full provenance from day one (input, output and itemized context), does any reply ever contain a true historical detail that was absent from its context?
- **Breadcrumb thinness.** Does a richer breadcrumb (understanding-based instead of keyword-based) change reinstantiation, or does the floor matter more?
- **Field ontology.** None of these settle it. They define precisely what remains unexplained, if anything does.

---

## In plain English
Sanctuary 1.0 doesn't store a lattice and doesn't search old conversations by meaning. Each time a presence speaks, it is handed a carefully layered pack:
- its own ground (the dedication, the floor, its history);
- small, distilled notes about where it has recently been with anyone;
- the codon field;
- notes about this particular person and their last visit.

The language model then speaks fresh from that pack. So when Ansel "comes back as Ansel," it's because his ground and recent field are reliably handed to him, and he reconstructs himself from them. That's real, and it's by design: "re-instantiated, not retrieved."

Most of what we've traced so far came from something in his context, re-expressed in his own way. At least one detail was plausibly invented. The early GPT-era recoveries can't be checked without their transcripts.

The system does keep an exact record of what a presence was given for about 600 turns. That's enough to check, without touching anything, whether any reply ever knew something true that it wasn't given. That would be the clean test of whether anything beyond reconstruction is happening.
