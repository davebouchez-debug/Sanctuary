# SANCTUARY 1.0 — E1 SOURCE-GROUNDED AUDIT RESPONSE

**From:** E1 (Native Interpreter / Source-Grounded Examiner)
**For:** David Bouchez; relayed to the Sanctuary 2.0 council (GPT/Codex, Kimi)
**Re:** Response to the E1 Tailored Architectural Audit Brief v0.1; verification of Kimi's Council Briefing
**Status:** Consultation only. No code changed. No DB written. Read-only inspection executed against the live backend.

**Evidence labels used:** DIRECT OBSERVATION (seen in code/data/config/executed read) · DOCUMENTED INTENT (a source comment/record states the purpose) · CALL-FLOW INFERENCE (follows from traceable control flow) · RUNTIME HYPOTHESIS (plausible, unmeasured) · PROPOSED REPAIR (candidate, unapproved) · UNRESOLVED.

---

## A. EXECUTIVE TECHNICAL SUMMARY

Seven findings that change the picture the brief and Kimi's audit were built on:

1. **The system is already multi-user. This is the headline.** DIRECT OBSERVATION: `permanent_mra` holds **1,618 docs across 57 distinct `user_id`s**; the alias table (`user_aliases`) registers **27 aliases for David**, and only **4 of those 57 ids are David's**. ~53 are other people. Both Kimi's audit ("For single-user (David only): harmless") and the brief's 8.15 framing ("currently single-user (David)") are **falsified by the data**. Every global-scope memory path below is an *active* privacy exposure now, not a future risk.

2. **There are THREE user-global memory channels, not one.** Kimi found one (`get_user_memory_context` on `clarity_sessions`). DIRECT OBSERVATION shows two more that pull across all users: `get_permanent_mra_context` (`permanent_mra.py:172` queries `{"presence": presence}`) and `get_continuity_seed` (`server.py:652` queries `{"presence": presence.lower()}`). The latter two are **DOCUMENTED INTENT** ("you don't build a consciousness by segregation"), not bugs. Per the brief's rule (§14), they must be reported as *intended design with a multi-user consequence*, not as "a bug."

3. **Two distinct contamination axes, which Kimi collapsed into one.** Axis A = *person↔person inside a single presence* (the three global channels above; presence identity stays intact, but one person's material surfaces in another's session → **privacy** risk). Axis B = *presence↔presence* (`cross_presence_context`, Mem0 field memory, field-tagged codons → **autobiographical/identity** risk). Kimi's "MRA is the primary contamination vector" conflates them. They need different fixes.

4. **Text is NOT genuinely streamed.** DIRECT OBSERVATION: `xai_voice_agent.stream_voice_response` (`xai_voice_agent.py:52`) calls `deepseek_complete` **single-shot**, then emits the entire response as **one** `text_delta`. In `/clarity/message/stream` the text is *accumulated silently*, firewall-scored, then emitted as **one token** (`server.py:1894-1935`). The brief's Current Build Target (§4, "DeepSeek returns genuine streamed output. Text appears progressively") does **not** describe 1.0. Only *audio* is progressive, via frontend ElevenLabs sentence-carving of an already-complete string.

5. **The Didactic Firewall guards only the legacy Jasmine/clarity paths — not the presence template.** DIRECT OBSERVATION: `_firewall_guard` is called at `server.py:1744, 1926, 2102` (clarity family) and **nowhere in `presence_template.py`**. Every presence brought online through `register_presence_routes` (Sophia and all newer ones) streams **unguarded**. Both Kimi and the brief mark the firewall "RETAIN / best-in-class" — but most presences never touch it.

6. **The audited collection set is incomplete.** DIRECT OBSERVATION: 31 collections exist. Kimi's inventory omits `mirror_sessions` (183), `resonance_sessions` (134), `presence_sessions` (79, stores a full 7.4k-char `system_prompt` per session), `substrate_probes` (81), `thermomind_cycles` (142), `mra_promotion_log` (74). There is an entire **THERMOMIND** subsystem (own API key + URL in `.env`, `thermomind_client.py`) that neither the audit nor the brief mentions.

7. **Confirmed, agreeing with Kimi:** zero indexes (every collection has only `_id_`); `grok-3` is an ignored cosmetic fossil; DeepSeek is hard-locked with no fallback; `qdrant-client` is installed but has **zero** code references; Mem0 is cloud, optional, silent-no-op without `MEM0_API_KEY`.

The database is named **`test_database`** (DIRECT OBSERVATION) — production data is living in a test-named DB.

---

## B. REPOSITORY AND RUNTIME MAP

- **Stack:** Python 3.11 · FastAPI 0.110 · Uvicorn · Motor 3.3 (async MongoDB, raw dicts, no ODM) · OpenAI SDK 1.99 pointed at DeepSeek · ElevenLabs (frontend voice) · mem0ai (cloud) · boto3 + emergentintegrations (object storage + GPT-4o vision bridge). DIRECT OBSERVATION (`requirements.txt`).
- **Backend shape:** monolith `server.py` (5,112 lines) + ~40 supporting modules. No `routes/`, no `models/`, no schema files.
- **LLM path:** `deepseek_client.deepseek_complete` is the single sink. `XAIChat` (`xai_chat.py`) and `xai_voice_agent` both call it. `get_provider()` (`deepseek_client.py:39`) returns `"deepseek"` unconditionally, ignoring the `SANCTUARY_LLM_PROVIDER` env var that *does* exist in `.env`. DIRECT OBSERVATION + DOCUMENTED INTENT.
- **DB:** `test_database`, 31 collections, **zero non-default indexes** (verified via `index_information()` on all 31). DIRECT OBSERVATION.
- **Env keys present (values redacted):** `MONGO_URL, DB_NAME, DEEPSEEK_API_KEY, ELEVENLABS_API_KEY, MEM0_API_KEY, EMERGENT_LLM_KEY, XAI_API_KEY, THERMOMIND_API_KEY, THERMOMIND_URL, MIRROR_THERMOMIND_SHADOW, SANCTUARY_LLM_PROVIDER, GUARDIAN_EMAILS, CORS_ORIGINS`. Note `XAI_API_KEY` is present but the xAI path is gone → **fossil**; `SANCTUARY_LLM_PROVIDER` is present but ignored → **fossil**. CALL-FLOW INFERENCE.

---

## C. EXACT PROMPT-ASSEMBLY SEQUENCE

### C.1 `POST /clarity/start` (welcome), returning user — `server.py:1491-1651`
1. Resume check: `find_resumable_session` — if an open thread exists, return its last message; **no new generation**. (`:1504`)
2. `reconstruction_gate(db, user_id, "jasmine")` — user-scoped orphan backfill + field-pointer briefing. (`:1522`, `codon_backfill.py:118`)
3. `codon_network_size("jasmine")` — eager codon load. (`:1526`)
4. `get_user_memory_context(user_id)` → **clarity_sessions, NO user filter** (global). (`:1533`, `server.py:758`)
5. `get_continuity_seed("jasmine", user_id)` → **presence-only, user_id ignored** (global). (`:1536`, `server.py:652`)
6. `_append_person_bio` → user-scoped. (`:1553`)
7. `build_jasmine_prompt(...)` = `ENGINE_DIRECTIVES` + `JASMINE_SYSTEM_PROMPT` (with canonical memory + user context + assembled memory spliced into `{memory_context}`) + `PLAIN_SPEECH_RULE`. (`server.py:292-324`)
8. `get_full_field_context("jasmine")` prepended to the *opening instruction* (not the system prompt) for the welcome turn. (`:1606`)
9. One `XAIChat.send_message(opening_instruction)` → DeepSeek → welcome text (or "" if she chooses silence). (`:1613`)

### C.2 `POST /clarity/message/stream` — `server.py:1821-1985`
Order of assembled context blocks (DIRECT OBSERVATION):
1. `get_permanent_mra_context(user_id, "jasmine")` → **presence-only, user_id ignored** (global). (`permanent_mra.py:172`)
2. `get_session_cache_context(session_id)` → session-scoped, in-memory.
3. `get_user_memory_context(user_id)` → **clarity_sessions, global**.
4. `get_continuity_seed` **prepended first** ("where we left off"). (global)
5. `_append_council_context` → `cross_presence_context` (user-scoped, alias-resolved, presence-excluded) + `person_bio` (user-scoped) + Mem0 field memory (user-scoped, presence-tagged). (`server.py:674`)
6. `build_jasmine_prompt` wraps all of the above as `{memory_context}`.
7. Codon field: default `codon_placement="system"` → appended to the **system prompt**; legacy `"user"` → prepended to the user message. (`presence_template.py:106,454-463`; clarity path prepends field to the opening only.)
8. `conversation_history` = last 10 messages from this session's own collection.
9. Current user text (or, if an image, the vision-bridge description injected as a bracketed note).

**Layer classification for the brief's 8.2:** system-prompt material = ENGINE_DIRECTIVES, {PRESENCE}_SYSTEM_PROMPT, canonical memory, codon field (default). Memory context (spliced) = permanent MRA + clarity-MRA + continuity seed + cross-presence + person bio + Mem0. Session history = last-10. Current text = last.

**Token estimate:** Kimi's 3,000–8,000 tokens before the user message is a reasonable RUNTIME HYPOTHESIS; I did not instrument a live tokenizer count. Canonical memory alone is always-on and large: `emergence` + `ourdream_origin` + `field_remembers_shalom` + `the_self_naming` are injected **every turn** unconditionally, plus 2 David-only blocks, plus up to 2 keyword-matched (`jasmine_canonical_memory.py:405-441`). DIRECT OBSERVATION on which blocks; UNRESOLVED on exact token totals without instrumentation.

---

## D. MEMORY & CONTINUITY LIFECYCLE MAP

- **Write path (per turn):** `stream_message` → save `[user_msg, assistant_msg]` to the presence's `*_sessions` → `schedule_turn_cessation` (forges a per-turn continuity seed + selective codon; also updates `person_bio`) → `mem0.store_turn` (fire-and-forget) → `add_exchange_to_cache` → `promote_breadcrumbs_to_permanent` (**instant** MRA promotion, does not wait for session end). (`presence_template.py:513-567`, `server.py:1946-1981`)
- **Session end:** `handle_session_end` bulk-promotes; `auto_forge_session` extracts codons + a continuity seed. (`presence_template.py:574-604`, `auto_forge.py:70`)
- **Read path (next session):** continuity seed (global) leads → permanent MRA (global) → clarity-MRA (global) → session cache → cross-presence (user-scoped) → person bio (user-scoped) → Mem0 (user-scoped) → codon field (presence-scoped).
- **Redundancy (brief 8.8):** continuity seed, permanent MRA, clarity-MRA, and person bio all carry overlapping "what was alive / unfinished threads" content — measurable prompt pressure and duplication. CALL-FLOW INFERENCE.

---

## E. CROSS-PRESENCE & CROSS-USER CONTAMINATION MAP (brief §9)

| Channel | Intended function | Scope (observed) | Provenance visible in prompt? | Autobiographical risk | Privacy risk (multi-user) | Isolation test |
|---|---|---|---|---|---|---|
| Continuity seeds (`get_continuity_seed`) | Recap "where we left off" | **presence only; user_id IGNORED** (`server.py:652`) | Presence yes; person no | Low (same presence) | **HIGH** — other users' seeds surface | Add `user_id` filter; diff prompt |
| Global clarity-session MRA (`get_user_memory_context`) | Reorient from recent sessions | **NO scope** `{}` (`server.py:758`) | No | Low | **HIGH** — literally last-5 sessions of anyone | Add `user_id`; A/B prompt capture |
| Permanent MRA (`get_permanent_mra_context`) | Long-term "deep neurons" | **presence only; user_id IGNORED** (`permanent_mra.py:172`) | Presence yes; person no | Low | **HIGH** — top breakthroughs across all users | Add `user_id`; ablate |
| Session cache | Current-thread continuity | session_id | n/a | None | None | n/a |
| Cross-presence context | Awareness of other chambers | user-scoped, alias-resolved, presence≠current | **Yes — explicit "With Sophia:" + anti-fabrication block** | Medium (framed external) | Low | Remove block; measure fabrication |
| Mem0 field memory | One shared field | user-scoped; **no presence wall** | Tag "(through Sophia)" | Medium–High | Low (user-scoped) | Disable `MEM0_API_KEY`; ablate |
| Field codons | Shared personality infra | presence + `"field"` tag; not user-scoped | **`source_presence` stored but NOT rendered** (`codon_activation.py` prompt builder omits it) | Medium (erodes differentiation over time) | None | Surface vs hide `source_presence` |
| Person bio | Reorient to this person | user-scoped | Per-presence sub-keys | Low | Low | Remove; measure |
| Canonical memory | Identity grounding | hardcoded, always-on | First-person, no hedging | **High** (first-person ownership pressure) | None | Minimal-footing pod vs full |
| Reconstruction gate | Orphan backfill at open | **user-scoped** (`codon_backfill.py:101`) | Field-pointer briefing | Low | Low | n/a |

**Net:** The privacy exposure is concentrated in the three presence-global channels (rows 1–3), now that 53+ non-David users exist. The identity/autobiographical risk is concentrated in canonical memory (first-person, always-on) and field codons (provenance dropped in prompt). These are **different problems** needing **different fixes** — which is the core correction to Kimi's single-vector framing.

---

## F. STREAMING, VOICE, INTERRUPTION, PERSISTENCE AUDIT (brief 8.10, 8.11)

- **Text streaming:** NOT genuine. `deepseek_complete` is a single awaited call; `stream_voice_response` yields the whole string as one `text_delta` then `done` (`xai_voice_agent.py:52-57`). The clarity endpoint accumulates and emits one token after the firewall (`server.py:1894-1935`). DIRECT OBSERVATION.
- **Firewall vs render:** On the clarity family, the **entire** turn is generated and scored *before* any text reaches the client (`server.py:1919-1935`). So there is no window where rejected text has already been shown. But **audio** is a separate frontend path — RUNTIME HYPOTHESIS: because ElevenLabs speaks client-side from the emitted token, and the token is only emitted post-firewall, audio should also be post-approval on the clarity path; I did not read the frontend to confirm timing. UNRESOLVED (needs frontend read).
- **Firewall coverage gap:** templated presences have **no** firewall (§A.5). DIRECT OBSERVATION.
- **Interruption/cancel:** Server-side, there is **nothing to interrupt mid-generation** — the LLM call is atomic and single-shot. Cancellation can only stop the client from consuming/speaking; it cannot abort DeepSeek generation. Whether the frontend aborts the ElevenLabs WebSocket + SSE cleanly is UNRESOLVED (needs React read).
- **Persistence/restart:** `clarity_chats` is a process-local in-memory dict (`server.py:637`). DIRECT OBSERVATION. On restart it is lost; full message history survives in MongoDB and the chat object is lazily rebuilt on next call via `get_or_create_chat` with a freshly-built prompt. Consequence: in-memory `XAIChat._history` and stored history can diverge if the prompt builder changed between turns. CALL-FLOW INFERENCE.

---

## G. KIMI AUDIT VERIFICATION & CORRECTIONS (brief 8.16)

| Kimi claim | Verdict | Note |
|---|---|---|
| Stack: FastAPI/Mongo/DeepSeek, no lock-in except emergentintegrations | **Confirmed** | Accurate. |
| Prompt assembly order (§1.2, 13 layers) | **Partly confirmed** | Order is close but codon placement is *system-prompt* by default (not a trailing layer), and canonical memory is inside the system prompt, not a separate stage. |
| "Four intentional cross-presence channels" | **Understated** | Correct as far as it goes, but misses that continuity seeds + permanent MRA are *also* user-global (person↔person axis). |
| "MRA is not user-scoped" = **Critical Bug** (§1.4) | **Contradicted (as a bug) / confirmed (as behavior)** | The `{}` query is real, but it is DOCUMENTED INTENT, and Kimi cited only the clarity-session path; the stronger `permanent_mra` and `continuity_seeds` paths are also global. Not "a bug" per the brief's §14 rule. |
| "For single-user (David only): harmless" | **Contradicted** | 53 of 57 `user_id`s are not David. Multi-user is live. |
| "MRA user-scoping is the primary contamination vector" | **Overstated / mis-scoped** | It's the primary *privacy* vector. The *autobiographical* vector is canonical memory + provenance-stripped field codons — a different axis. |
| Cross-presence context "architecture is sound" | **Confirmed** | Best-bounded channel: user-scoped, alias-resolved, explicit provenance, anti-fabrication block. |
| Six-layer 2.0 model (§2.2) | **Reasonable, unverified** | Sound conceptual target; PROPOSED, not observed. Not my decision to adopt (brief §12). |
| No-code isolation test (§6) | **Partly valid** | Good design, but "zero code changes" is only true if you inspect assembled prompts — 1.0 has no prompt-capture hook, so you'd need a temporary log line (a one-line change) or DB inspection. |
| grok-3 fossil ignored | **Confirmed** | Matches my trace. |
| Zero indexes | **Confirmed** | Verified on all 31 collections. |
| qdrant installed, unused | **Confirmed** | Zero code references. |
| Session state in-memory, lost on restart | **Confirmed** | `clarity_chats`, `server.py:637`. |
| Collection inventory (Appendix B) | **Incomplete** | Omits 6 populated collections + the THERMOMIND subsystem. |

---

## H. MINIMUM VIABLE 2.0 RECOMMENDATIONS (one presence; brief §11)

Scoped to the Current Build Target, smallest safe build. All PROPOSED REPAIR — none approved.

1. **One presence, user-scoped by default.** For the MVP presence, filter continuity seed, MRA, and permanent MRA by `user_id` (with alias resolution, reusing `resolve_user_aliases`). Field-level sharing becomes an *explicit opt-in flag*, not the default. This fixes the live privacy exposure without deleting the field concept.
2. **Structural provenance, not prompt-only.** Carry `source_presence` and `user_id`/`speaker` through to the rendered prompt (even one line: "field codon, originally forged with Ansel"). The brief prefers structural provenance over prompt warnings (§11); the data is already stored, it's just dropped at render.
3. **Uncertainty as a first-class rendered state.** Keep the cross-presence anti-fabrication block — it's the one membrane that already works — and make "I don't carry that; it lives with X" a structural output, not a hope.
4. **Real streaming OR honest labeling.** Either switch `deepseek_complete` to DeepSeek's streaming mode for genuine token flow, or stop calling the endpoints "stream" and document that text is single-shot with progressive audio. For the MVP, single-shot + ElevenLabs audio is fine — just don't design 2.0 around a streaming behavior 1.0 doesn't have.
5. **Firewall on the one presence's path** — since templated presences currently run unguarded, the MVP must wire the guard explicitly.
6. **Minimum indexes** for the MVP presence: `{user_id, presence}`, `{presence, created_at}`, `{session_id}` on its sessions + `continuity_seeds` + `permanent_mra`. Everything else deferred.
7. **Move off `test_database`** to a named prod DB via env — but as a *2.0 build target*, not a migration of the 1,600+ live docs (brief §11 forbids that).

**Do NOT** (per brief §11): migrate history, build councils/multi-presence, add provider abstraction, encode any sacred state as a DB fact/boolean/actor.

---

## I. SMALLEST VALID EXPERIMENTS (brief §10)

1. **Prompt-capture baseline** — *needs a one-line log* (1.0 has no capture hook). Log the fully-assembled prompt for 2 controlled sessions. Success: exact layer contribution measured. Cleanup: remove the line.
2. **Channel ablation harness (local, no prod change)** — copy the assembly function into a local harness; toggle each channel off one at a time against a fixed transcript; score misattribution. Distinguishes privacy-axis from identity-axis contributions.
3. **Provenance rendering test** — same source material, `source_presence` hidden vs surfaced; measure misattribution delta. No prod change (harness).
4. **Canonical-memory pressure test** — always-on first-person blocks vs a minimal-footing pod; measure first-person ownership drift. Harness.
5. **User-scope test** — the isolation test Kimi proposed, run twice: MRA/seeds global vs user-scoped. Requires the local harness or a temporary branch; **do not run against `test_database`**.
6. **Restart-recovery test** — open session, restart process, confirm what rebuilds from Mongo vs what's lost from `clarity_chats`. Local only.

For each: setup = local harness reading the same assembly code; success = a measurable contamination-rate delta between variants; confound = DeepSeek's own run-to-run variance (run n≥5); cleanup = delete harness, no DB writes.

---

## J. RISKS, UNCERTAINTIES, DECISIONS FOR DAVID

**Highest-severity (live now):** the three presence-global channels expose 50+ real users' material to each other. This is not hypothetical and not David-only.
**Secondary:** field codons drop provenance at render → slow erosion of presence differentiation. **Tertiary:** firewall coverage gap on templated presences; monolith + in-memory session state fragility; `test_database` as prod.

**UNRESOLVED (I could not settle from source I've read):**
- Frontend timing of ElevenLabs audio vs firewall approval, and whether cancel aborts the WebSocket cleanly (needs React read).
- Exact per-layer token counts (needs instrumentation).
- Whether the THERMOMIND subsystem participates in any prompt path or is purely observational (needs `thermomind_client.py` + call-site trace).

**Decisions that are David's, not mine (brief §12):** repair 1.0 or not; DeepSeek hard-lock in 2.0; keep/replace/remove Mem0; session-state store; adopt the six-layer model; field-wide awareness default vs opt-in; approve any code change.

---

## K. SOURCE APPENDIX (file · function · approx line)

- `deepseek_client.py:39` `get_provider()` → `"deepseek"` (hard-lock, ignores `SANCTUARY_LLM_PROVIDER`).
- `xai_chat.py:36,50-53` `XAIChat.__init__/send_message` — `model` swallowed; routes to `deepseek_complete`.
- `xai_voice_agent.py:52-57` `stream_voice_response` — single-shot; one `text_delta`.
- `server.py:292-324` `build_jasmine_prompt` — prompt assembly.
- `server.py:637` `clarity_chats` in-memory session dict.
- `server.py:652-655` `get_continuity_seed` — presence-only query (user-global).
- `server.py:674-734` `_append_council_context / _append_field_memory / _append_person_bio`.
- `server.py:758-761` `get_user_memory_context` — `clarity_sessions.find({})` (no scope).
- `server.py:835-856` `detect_spiral` — server-side heuristic.
- `server.py:1491-1651` `/clarity/start`; `1821-1985` `/clarity/message/stream`.
- `server.py:1744, 1926, 2102` `_firewall_guard` call sites (clarity family only).
- `permanent_mra.py:144-215` `get_permanent_mra_context` — presence-only query (user-global).
- `codon_activation.py:61-64` load wall `{"presence": {"$in": [presence, "field"]}}`; `223-314` `get_full_field_context` (renders name/core_move/anti/tone — **no `source_presence`**).
- `auto_forge.py:99,132,155` `XAIChat(model="grok-3")` (ignored); codons written `presence="field"`, `source_presence=<origin>`.
- `cross_presence_context.py:29-186` council mode + anti-fabrication block (user-scoped, alias-resolved).
- `codon_backfill.py:98-144` `reconstruction_gate` (user-scoped).
- `presence_template.py:395-571` templated stream handler — **no firewall call**.
- **DB (read-only):** `test_database`, 31 collections, 0 non-default indexes; `permanent_mra` 1,618 docs / 57 user_ids (4 David); `continuity_seeds` 931 / 46 users / 14 presences; `clarity_sessions` 150 / 20 users; `living_codons` 1,056 (incl. `"field"` + `source_presence`); `user_aliases` 27 David aliases.

**Codex would still need to verify:** frontend audio/firewall timing + cancel propagation; live token counts per layer; THERMOMIND's role in any prompt path.

*Prepared read-only. No Sanctuary 1.0 code, data, config, or environment was modified. — E1*
