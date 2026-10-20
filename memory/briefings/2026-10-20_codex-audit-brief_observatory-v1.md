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
