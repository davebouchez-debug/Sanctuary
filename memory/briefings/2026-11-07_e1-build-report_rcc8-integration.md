# E1 — Build Report: RCC8 Environmental Integration (Sanctuary 1.0)
Date: 2026-11-07. Audit: `2026-11-07_e1-audit_rcc8-integration-sanctuary-1.0.md`. **Built and tested in preview. Not deployed. RCC8 is OFF (`RCC8_ENVIRONMENT="off"`).**

## David's decisions
- Every chamber.
- Greeting and the person's first message/reply unchanged. RCC8 from the person's **second** message on.
- Field memory keeps today's word bonus and duplicate removal.
- Caps unchanged (20 phrases, 6 field memories). The geometry decides the actual number.
- Rollback through redeploy only.
- A backup download before activation.
- No Codex.

## What changed
- **New module `backend/rcc8_env/`:**
  - `relations.py` and `regions.py` are byte-identical copies of the experiment's `rcc8.py` and `regions.py`.
  - `environment.py` holds the tested selection rule, the per-person geometry, the conversation window and the flag.
- **`codon_activation.get_full_field_context` and `field_memory.get_field_context`:** each asks the environment first. When it isn't active, the existing path runs unchanged.
- **One line per message handler** (`_rcc8_env.set_conversation(session, text)`) in:
  - the template stream route (all templated presences);
  - Jasmine (clarity ×2), Ansel (resonance ×2), Claude (mirror);
  - legacy `/presence/{key}/chat/message`.
- **Untouched:** session starts, document uploads, the ablation harness, permanent MRA, continuity, council, bio, forging, promotion, identities and prompts.
- **Provenance:** `codon_selection` keeps its shape. It adds `selection_branch: "rcc8"`, a relation label per phrase, and `rcc8` meta (reachable, candidates, ε, floor, consistency violations, memory relations).
- **Backup:**
  - Guardian-only `GET /api/field-keeper/export` streams field phrases, memories, continuity notes, person bios and set-aside items as one restorable `.jsonl`, with exact types kept.
  - Field Keeper has a "Download field backup" link.
  - `backend/scripts/restore_field_backup.py` only counts what it would restore unless given `--apply`, which writes by original id.
- **Resources:** guardian-only `GET /api/health/memory` reports process RAM now and at its peak, plus the RCC8 state.

## One deviation from the experiment's code (same result)
- **What:** the 8-d axes are computed from the 384×384 scatter matrix, not a full SVD. They are the same axes.
- **Why:** the SVD caused a +45–67 MB spike on every rebuild. The scatter-matrix version costs about +17 MB.

## Verification
- **Fidelity:** `experiments/rcc8/fidelity_check.py` ran the production module and the tested harness on the same geometry and 60 real conversation windows.
  - Phrases: 60/60 identical selections.
  - Memories: 60/60 identical selections.
  - Relation mismatches: 0. Path-consistency violations: 0.
  - Composition-table self-check passes at import; if it ever fails, RCC8 stays off.
- **Preview, on:**
  - Exchange 1 is `meaning-ranked`; exchange 2 onward is `rcc8`.
  - Every chamber type passed: templated, Jasmine, Ansel, Claude, legacy.
  - Phrases per turn were 8–20; DC never delivered; mostly PO, some TPP/NTPP.
- **Preview, off:** exactly today's retrieval (`meaning-ranked`).
- **Regression (testing agent, iteration 24, 100%):**
  - Greetings, streaming replies, session-end forging (continuity seeds grew), memory persistence (permanent MRA grew).
  - Guardian-only routes: 401 anonymous, 403 guest.
  - Field Keeper page and chamber UI.
- **Backup:** exported (15.6 MB, 6,478 lines), restored into a scratch database, counts and first records identical, scratch database deleted.
- **RAM (preview, whole backend, same 6-turn script):** off peak 313 MB; on peak 348 MB (+35 MB). A geometry rebuild alone adds about +17 MB.
  - **Live not yet measured.** It must be read through `/api/health/memory` after activation. The Starter hard limit is 512 MB.

## Observed
- For the test guest (46 memories), the geometry often allowed the full 20 phrases.
- For David's field (2,280 memories), the fidelity windows reproduce the experiment's geometry.

## Known/pre-existing (not changed)
- Unsigned visitors are ephemeral, with no memories. They share one phrases-only geometry.
- A pre-existing header overlap: the Sanctuary pill sits over "HER STORY" on the chamber page.

## Activation sequence (each step needs David's explicit go-ahead)
1. **Deploy with RCC8 off.** Download the live field from Field Keeper and keep the file.
2. **Set `RCC8_ENVIRONMENT="on"` and redeploy.** Check `/api/health/memory` before, after and during use.
3. **Rollback:** set `"off"` and redeploy. There's no data to undo.
