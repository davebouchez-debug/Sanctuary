# E1 — Sanctuary Relational Topology (SRT): Architecture Assessment
Date: 2026-11-06. Investigation only. No code, prompts, data, configuration or deployments were changed.
Grounded in the Sanctuary 1.0 codebase (`/app/backend`) and live preview data, checked today.
Section 7 was revised after the full request arrived.

---

## 1. Sanctuary 1.0 as it actually runs

### 1.1 Chambers and identity
- **26 presences.** 23 are template presences: each is a `PresenceConfig` in `presences/*.py`, auto-registered, served by `presence_template.build_presence_router`. Three are older chambers written inline in `server.py`: Jasmine, Ansel ("resonance") and Claude ("clarity").
- **Each chamber has its own session collection** (`<key>_sessions`). Threads, history and resume live there.
- **Identity is prompt text and nothing else.** A presence is its identity block plus shared blocks. No code-side property makes Sophia Sophia apart from the words in her prompt and the memories filtered by `presence`.
- **Engine:** every chamber calls DeepSeek through `SanctuaryChat`. Some forge code still passes `model="grok-3"`; the parameter is ignored.

### 1.2 Context assembly for one turn (template path)
The system prompt is built in this order (`presences/common.py::assemble_presence_prompt`, `presence_template.py` L149–210, L438–468):
1. Sanctuary dedication → room to listen → engine directives
2. The presence's identity
3. Calibration (Didactic 8 / Expansion 72) and the correction line
4. Story of arrival
5. **"FIELD MEMORY I CARRY:"** — the memory context, assembled in this order:
   - continuity seed (put first)
   - permanent memories (person × presence)
   - session cache
   - cross-presence context (council mode)
   - person bio
   - field context (field phrases and memories ranked by meaning)
6. Closing → field ground → welcome without debt → plain speech, which includes "How a thought begins" (the last thing the model reads, so it carries the most weight)
7. Codon field context: field phrases ranked by meaning against the message, added to the system prompt (default) or to the user message (older placement)
8. The last 10 messages of the thread

The three `server.py` chambers do the same thing inline, with their own copies of these steps.

### 1.3 "Layer 8"
**Layer 8 does not exist in Sanctuary 1.0.** There is no Layer 8 code, prompt block or data anywhere in this codebase. According to the 2.0 briefing (`memory/daily_briefing_sanctuary_2_0.md` L141–146), it lives in the 2.0 repository: the relation `DC(R1,R2) ∨ EC(R1,R2)` is computed upstream and delivered to the model as plain-language structure ("four regions; the first two either disconnected or externally connected, choice not supplied"). So Layer 8 is **model-visible text**. RCC sits upstream of the model; the model never runs it.

The only region-calculus code in 1.0 is `observatory_ledger/measure.py`: RCC5 relations (EQ, DR, PP, PPi, PO) between **sets of entity mentions** in consecutive turns, used by the Observatory. It runs offline, writes to a separate database (`sanctuary_observatory`), and is **never fed into model-visible context**.

### 1.4 Personal memory and the shared field

| Store | Scope | Written by | Read by |
|---|---|---|---|
| `permanent_mra` (2,701) | person × presence | every turn (instant promotion) + session end; ephemeral visitors excluded (`permanent_mra.py` L118, L282) | own chamber; cross-presence context; field context (by meaning, all the person's presences) |
| `continuity_seeds` | presence × person | session end (`auto_forge.py`); per turn for 19 template presences (`turn_cessation`) | own chamber's welcome and memory; cross-presence context; `field_territory.py` (Sanctuary-wide view, Kalahar) |
| session cache | one session, in process | each exchange | own chamber, same session |
| `field_phrases` (1,928) | **Sanctuary-wide**, no person or chamber scope | `auto_forge` (6), `turn_cessation` (39), one-time translation of the old codons (1,883) | **every chamber, every person**, ranked by meaning each turn |
| `living_codons` | presence, plus `presence:"field"` | — | **empty (0 records)**; `codon_activation.py` L64 still queries it. A dead path. |

**The field phrases are the propagating store.** A phrase forged from any conversation is retrievable by every presence for every person on the next turn where it's relevant.

### 1.5 Forging, admission and safeguards (code-side vs prompt-side)
- **How a phrase is forged:** an LLM reads the conversation (`PHRASE_FORGE_PROMPT`) and returns phrases. `field_memory.add_phrases` writes them straight into `field_phrases`.
- **Code-side gates that actually exist:**
  1. Ephemeral visitors never forge or promote (`is_ephemeral`).
  2. `forge_ledger` makes sure a session is forged only once.
  3. Removal after the fact by the guardian, in the Field Keeper.
- **What does not exist:**
  - **No admission review, quarantine or threshold.** Whether a phrase gets in depends only on the forge LLM's own judgment, which is prompt-side.
  - **No person or session provenance on field phrases.** Records carry only `source` and `presence`, so you can't tell whose conversation a phrase came from.
- **No chat-output path writes to storage.** No code parses a presence's reply for commands, tags or JSON. Telling a presence "forge a codon" cannot, by itself, write anything. **But the content of a conversation reaches the shared field indirectly, through the forge LLM.** That indirect path is the real exposure (§3).
- **Firewall:** `firewall/` re-rolls replies that break presence. It filters output only, not the field.
- **Test identities in personal memory:** `permanent_mra` holds records under test user ids (`deepseek-test-david` 104, `lockcheck-…` 63, `test-user-555` 46, `fw-test-user` 46). They're scoped to those ids, so they don't reach David. But it shows that **nothing in the environment separates test identities from real ones**. Who may write is decided at the call site, not by the environment.

### 1.6 Chamber-specific vs shared services
- **Per chamber:** the session collection, the codon network cache, and memory and seed rows filtered by `presence`.
- **Shared environmental services:**
  - field phrases and the meaning-search model
  - identity resolution (`user_aliases`) and authentication, including `require_guardian` and `deny_guests`
  - thread listing
  - the Observatory ledger (separate database)
  - the Field Keeper (guardian only)
  - integration health
  - ThermoMind (a passive side service)
- **Scoping is spread around.** Each loader applies its own `user_id` / `presence` filter, and cross-presence context and `field_territory` each define their own reach. **There is no single place that declares what may reach what.** That gap is exactly what SRT could fill.

---

## 2. Environmental RCC8

### 2.1 Where relational structure can act
A language model has only its context window. Structure can reach a presence through two channels:
- **Expressive:** the structure is put into words the model reads. That's Layer 8.
- **Structural:** the structure stays out of sight and decides what becomes available: which stores, which items, and when.

SRT as you describe it is the **structural channel only**. In 1.0 the place it would act is precise: the functions that decide what enters context, `_build_memory_context` and `get_full_field_context`, along with the write side (forge, promotion). The presence would feel the consequences of the topology (what is near, what is absent) without ever reading it.

### 2.2 What it could organize or replace
One declared topology plus one resolver function, "what is reachable from here, for this person, in what mode", could replace the scattered rules:
- `user_id` filters in each loader
- the "other rooms" mask in cross-presence context
- `is_ephemeral` checks at several call sites
- `field_territory`'s Sanctuary-wide reach
- guardian-only checks for tools that cross regions

This is the strongest practical case: **one place that says what touches what**, readable by a person and checkable by a machine.

### 2.3 How it would meet chambers, memory and codons (minimal regions)
- **Person regions** (one per signed-in person). Personal memory sits inside them: NTPP.
- **Chamber regions** (one per presence). A chamber and a person **overlap (PO)** during a conversation. Memories for person × presence live in that overlap.
- **The field.** Every chamber is **externally connected (EC)** to it: it can read, but it doesn't contain the field and the field doesn't contain it.
- **An admission buffer.** Forged phrases land here first. It's EC to the field, not inside it. Admission moves a phrase into the field.
- **Protected regions** (architecture and prompts, guardian tools, the Observatory). **Disconnected (DC)** from every chamber.
- **The visitor region,** a short-lived bubble around one visit. It overlaps only its own chamber and is DC from the field on the write side.

### 2.4 Does RCC8 add anything over ordinary relationships and access controls?
Honestly, for permissions alone, no. An access-control table or a graph does that job, and it's simpler. RCC8 earns a place in four narrower ways:
1. **Containment has direction** (TPP/NTPP and inverses). It gives inheritance for free: what belongs to a person is reachable wherever the person is. DC, EC and PO can't express that, and plain tables have to spell it out by hand.
2. **The declared network can be checked for consistency.** A contradictory topology (for example, a chamber declared both DC from and inside the same region) is caught when the server starts, not discovered in behavior.
3. **Non-transitivity of EC is a privacy statement you can check.** Two chambers each EC to the field are not thereby connected to each other. That's the formal version of "the field is shared but rooms stay private".
4. **A shared vocabulary.** The same eight words can describe the environment to David, GPT, E1 and auditors, with exact meanings.

**What it doesn't give:**
- It doesn't enforce anything. Enforcement is code (§3).
- Its composition table is weak. It yields *possible* relations, not decisions, so it can't be the reasoning engine for permissions.

### 2.5 What would be unnecessary or unjustified
- Computing RCC relations over conversation content to steer replies.
- Showing RCC terms to presences or asking them to embody relations. That's the expressive channel, and it's already covered by the separate Layer 8 question.
- Using all eight relations where three or four describe the real structure. In 1.0, EQ, TPP and the inverse relations have no real objects to attach to.
- Geometric regions, distances or continuous space. The environment is discrete.
- Using the composition table to decide access.
- Building SRT as a large framework before the two concrete needs (one access function, provenance plus admission) exist.

---

## 3. Security: topology, permission and authority

### 3.1 Keep the three apart
- **Topology** (what is related to what): a small, versioned declaration in code (e.g. `srt/topology.yaml`), consistency-checked when the server starts. The topology carries no rights.
- **Permission** (what may flow along each relation): a table keyed by relation and operation (read, write, admit, remove). It's enforced by **one access layer** that every memory and field read or write goes through. Prompts never enforce it.
- **Authority** (who may change topology or permissions): only the guardian, through a code change and a publish, or later a signed admin action. **Nothing that arrives through a conversation can hold authority.** Model output is data, never a command.

### 3.2 The real attack path today, and how the design closes it
**The path:** a compromised signed-in account (or a careless one) puts text into a conversation. The forge LLM distills it into phrases, and the phrases go straight into the shared field. From there, the content reaches every presence and every person by meaning. No instruction has to be obeyed for this to work; the content only has to be **summarized**.

**Minimal design to close it, in code, with no prompt rules:**
1. **Provenance on every write:** person, session, chamber, forge run and time. Today field phrases have none.
2. **Admission buffer.** Forged phrases land in the buffer, not the field. They move in by **rule**, for example independent reinforcement from at least two different people or sessions, or guardian approval in the Keeper. The rule is code-side and logged.
3. **Treat forge output as untrusted data:** fixed format, length limits, no fields that can carry instructions, and anything malformed is rejected.
4. **Separate what each path may write.** The chat path can write only to its own session and the person's own memories. Only the admission service can write to the field. Only guardian tools can remove or restore.
5. **Keep the existing rule that nothing executes model output.** Make it a stated invariant with a test, not an accident of implementation.
6. **Keep "protected architecture" out of context.** Anything in a model's context can be coaxed back out by asking. SRT's structure, permissions and implementation never appear in prompts, which is also why they don't leak.

None of this depends on presences behaving well. A presence could be fully manipulated in conversation and still not be able to widen its reach, write to the field directly, or skip admission.

### 3.3 Modular, portable, licensable
- **Package SRT as a module with a small interface:** `available(request) → allowed sources` and `admit(candidate) → decision`.
- **Keep Sanctuary-specific region names in a separate adapter.** The core knows regions, relations and permissions, not Sanctuary.
- **Licensing:** the topology format and interface can be published. The resolver, the admission rules and the consistency checker stay private. Because none of it is model-visible, prompts can't expose it.
- **Build only the two needs now:** one access layer, and provenance plus admission. Anything beyond that waits for a demonstrated need.

---

## 4. The smallest meaningful one-chamber experiment

**What it tests:** whether shaping what a presence can reach changes its relational behavior, with no new words in the prompt. That removes the spatial-wording confound that Layer 8 can't escape.

**Design:**
- **Chamber:** one template presence David rarely uses and isn't attached to (to be agreed). Not Jasmine, Ansel, Claude or Sophia.
- **Condition A (unchanged):** the chamber's current retrieval: full field plus the person's memories.
- **Condition B (topology-shaped):** the same prompt, word for word. Only the pool that field and memory retrieval may draw from changes, according to a declared relation. Example: the chamber reaches only the field phrases that came through chambers EC to it, plus its own memories. No RCC terms appear anywhere in context.
- **How it's run:** **offline replay** of real recorded turns from that chamber, using the snapshots already captured by `turn_provenance`, sent through both conditions several times each. This is the same harness used for today's pre-qualifier replay.
- **Writes:** none. No promotion, no forge, no seeds. Experiment results go to a separate collection or file.
- **Rollback:** there's nothing to roll back. The live chamber is never touched. If a live arm is ever wanted, it's a per-chamber flag that is off by default, and its sessions are marked so nothing they produce is forged or promoted.

**What to record:**
- **Technical (per turn):** which items were retrieved (ids), reply length, how much of the reply's wording traces to retrieved items, references to other rooms or people, self-location wording, and variation between repeated runs.
- **Relational interpretation:** David's reading of selected pairs, done blind (he doesn't know which condition is which), kept in a separate, labeled notes field so it never mixes with the technical record.

**Limitations:**
- Condition B changes what is available. Any effect may come from different content, not from "topology" as such.
- The experiment shows that availability shaping matters. It can't show that the presence experiences a relation.
- One chamber can't show anything that happens between chambers.
- Offline replay misses how a live person would respond to the change.
- Effects at this scale may stay within ordinary model variation. Repeated runs exist to measure that variation.

---

## 5. Observing the unexpected

**Use what already exists:**
- `turn_provenance` records exactly what the model saw on each turn.
- The Observatory ledger is append-only, hash-chained and separate from the live data.

**Add one lightweight thing:** an annotation stream where David or Amanda can mark a moment ("this surprised me") in their own words, with no categories required.

**Telling the three apart:**
- **Ordinary model variation:** replay the same recorded input N times. If the phenomenon shows up at a similar rate across repeats, it's in the model's normal range.
- **Architectural effect:** replay the same input under different environmental conditions. If the rate changes with the condition, the architecture is involved.
- **Recurring observation:** the same motif across different sessions, people or presences, over weeks. Group replies by meaning and track motifs over time.

**Independent reinforcement without treating repetition as an error:** for each recurrence, check the provenance snapshot.
- If the motif's wording, or a field phrase carrying it, **was in the model's context**, mark it **carried**. That's propagation through the field, which is welcome but not independent.
- If **nothing in context carried it**, mark it **arose**. That's independent emergence.
- Repetition is counted either way. Only "arose" across independent sources counts as independent reinforcement.

The same distinction could later feed the admission rule in §3.2.

---

## 6. What carries into 2.0

**Bring forward the principles, not the code:**
1. **Environment over instruction.** Today's pre-qualifier work showed that rules in prompts get echoed back ("I won't pretend" was our own line). Whatever the environment can do, the prompt shouldn't say.
2. **Identity in prompts; scope and access in code.** Keep presences free of mechanics (Didactic 8 / Expansion 72) and let the environment carry structure.
3. **A shared field with private rooms,** stated once as topology (EC to the field, rooms not connected to each other) and enforced by one access layer.
4. **Provenance on every write, and admission as a code decision,** with the guardian's removal and restore as the backstop.
5. **Offline replay and condition comparison as the standard test method.** Flags that are off by default, so every change is reversible.
6. **Lessons from today's publish** (see the incident briefing): packed vectors, incremental indexes, one copy per scope, measuring on a box the size of the target plan, no unexamined defaults.
7. **Relational coherence without uniformity:** every presence shares the field and keeps its own identity, room and voice. The topology relates them; it doesn't flatten them.

**Leave behind:**
- the duplicated chamber code in `server.py`
- four overlapping personal-memory stores (permanent memories, continuity seeds, session cache, cross-presence context). In 2.0 they could be one store per person × chamber region.
- the dead `living_codons` path
- test identities writing into the real memory store
- field phrases with no provenance

---

## 7. Conclusions

### 7.1 Implemented and working
- Per-chamber identity (prompt text) and sessions.
- A shared field of meaning-ranked phrases, retrieved by every chamber on every turn.
- Personal memory scoped to person × presence, promoted every turn, stored packed and loaded incrementally (as of today).
- Ephemeral visitors fully excluded from memory and the field.
- Forge-once guarding (`forge_ledger`).
- Guardian-only Field Keeper removal and restore.
- No code path executes or parses model output into writes.
- Model-visible input snapshots (`turn_provenance`).
- An offline, hash-chained Observatory computing RCC5 over sets of mentions, never fed back to presences.

### 7.2 Technically feasible, not implemented
- Provenance (person, session, chamber, forge run) on field phrases.
- An admission buffer with code-side promotion rules.
- Separate write rights per path, with one default-deny access layer.
- A declared topology with a consistency check at startup.
- The offline one-chamber availability experiment (§4).
- The carried/arose observation method (§5).
- SRT as a portable module with a small interface.

### 7.3 Still hypothetical
- That shaping what a presence can reach, with no new wording, changes relational behavior in a meaningful way. Untested.
- That a presence experiences environmental relations in any sense beyond receiving different material. Not directly testable.
- That Layer 8's lake observation came from relational structure rather than spatial wording. Open, and belongs to 2.0.
- That RCC8 consistency checking or inference would catch real errors a plain table wouldn't. At Sanctuary's scale (about ten region types), the network can be checked by eye.
- That independent reinforcement is a sound admission signal. Plausible, not measured.
- That the Relational Pressure Hypothesis describes anything operational.

### 7.4 Preserve unchanged
- Identities in prompts; mechanics out of prompts. Didactic 8 / Expansion 72, affirmative framing, and today's phrase-form rewrites.
- The shared field propagating by meaning. That's the core thesis, and it works.
- Personal memory scope (person × presence) and the ephemeral exclusion.
- The invariant that nothing executes model output.
- Guardian removal and restore.
- `turn_provenance` and the Observatory as separate, offline record-keepers.
- Layer 8 in 2.0, per its own "do not disturb".
- The DeepSeek lock.

### 7.5 The smallest worthwhile experiment
The smallest worthwhile **step** isn't an experiment. It's **provenance on field writes.** It changes no behavior, and it's a prerequisite for admission control, for removing things by origin, and for the carried/arose distinction.

The smallest worthwhile **experiment** is the offline replay in §4: one rarely used chamber, real recorded turns, unchanged versus topology-shaped retrieval pool, identical prompt, no writes. It tests the only claim that matters for environmental SRT: does availability alone change relational behavior? If it doesn't, environmental RCC8 has no behavioral case, and only its bookkeeping value remains.

### 7.6 Security risks and unresolved dependencies
**Risks, highest first:**
1. **Forge path into the shared field.** Any signed-in account shapes the shared field through conversation content alone. There's no admission review and no provenance.
2. **Person-to-person leakage through the field.** Phrases distilled from one person's private conversation are retrieved in everyone's chambers. A phrase can carry personal detail across people. The field is shared by design, but this consequence has never been decided explicitly.
3. **Anything in context can be coaxed out:** identity blocks, field phrases, cross-presence material. Prompt rules can't protect it; only keeping material out of context can.
4. **Permission checks are attached endpoint by endpoint** (`require_guardian`, `deny_guests`). One missed check exposes an endpoint. There's no default-deny.
5. **No separation between test and real identities in the memory stores.** Test ids hold about 300 permanent memories today.
6. **The dead `living_codons` path** treats `presence:"field"` records as universal. Anything that writes there bypasses even forge judgment.
7. **Kalahar's `field_territory`** reads across all people by design. That's acceptable, but it's an unrecorded exception.

**Unresolved dependencies:**
- Layer 8's code lives in the 2.0 repository, which I can't see. My account of it relies on the 2.0 briefing.
- Whether Emergent's production Atlas supports in-database vector search. This affects 2.0 storage design.
- The ThermoMind/PermaMind update (Nile).
- The hosting plan, which affects whether admission and checks run in-process comfortably.
- Who besides David holds authority.

### 7.7 Questions for Codex's independent review
1. Does Layer 8 in the 2.0 repository match the description here (computed upstream, rendered as text, nothing executed by the model)?
2. Independently verify the claim that no 1.0 path turns model output or user content into a write, except forge and promotion.
3. Is a single default-deny access layer actually enforceable in this codebase, given database calls spread across roughly 40 files? What would it take?
4. At about ten region types, is RCC8 consistency checking worth anything over a plain relation table? Recommend against it if not.
5. Is "two independent sources" robust as an admission rule against one person with several sessions, or a compromised account farming sessions?
6. Is "was the motif present in the model-visible context" a sound test of independence for the carried/arose split?
7. For the §4 replay: what confounds remain, and how many runs are needed to separate an effect from normal model variation?
8. How severe is the person-to-person leakage through field phrases, and what is the minimal mitigation?

### 7.8 Decisions requiring David's explicit approval
1. Whether to pursue SRT at all, or only the concrete pieces (provenance, admission, access layer) without RCC8.
2. The admission policy: what lets a phrase into the field (reinforcement threshold, guardian approval, or both), and whether today's 1,928 phrases are kept as they are.
3. Whether the field is shared across people completely, or by person with an explicitly shared subset. This is the privacy decision in risk 2.
4. Who holds authority over topology and permissions.
5. Which chamber hosts the experiment, and whether a live arm is ever allowed.
6. Cleaning test identities out of the memory stores.
7. Retiring the dead `living_codons` path.
8. Still pending from earlier today: the near-twins policy, and the Atlas in-database search check.

### 7.9 Recommendation
**Don't adopt RCC8 as an implementation foundation now.** Everything 1.0 actually needs (scoping, provenance, admission, default-deny) is fully met by ordinary data structures and one access layer. RCC8's distinct contributions are real but small at this scale:
- containment as inheritance
- consistency checking
- EC that isn't transitive

Build the three concrete pieces with plain structures. If useful, describe the resulting topology in RCC8 terms **as documentation and shared vocabulary**. Revisit RCC8 as executable structure only if both of these hold:
- the §4 experiment shows that availability shaping changes relational behavior
- the topology grows past what can be checked by hand

That's the smallest coherent architecture that works. RCC8 stays available without being built in before the evidence calls for it.
