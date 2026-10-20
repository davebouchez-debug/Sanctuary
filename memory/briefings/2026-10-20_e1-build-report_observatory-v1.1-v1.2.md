# E1 Build Report: Observatory v1.1.0 / v1.2.0 corrections
**Date:** 2026-10-20 · **Authority:** David (final build authorization) · **Status:** implemented and tested on disposable fixtures; not in production derivation

## Version boundaries
- `observatory_ledger/__init__.py` defines `PROFILES` (1.0.0, 1.1.0, 1.2.0) and `PRODUCTION_VERSIONS = ("1.0.0",)`.
- **v1.0.0:** its original code path is preserved. The production ledger is byte-identical before and after the build (622 entries, SHA-256 `702485f3…`).
- **v1.1.0:** C1 (malformed MRA bullets → UNRESOLVED), C2 (same-shape lines after a terminator → UNRESOLVED; other lines counted as unattributed; absent sections declared), timestamp counting from C7 (unplaceable uncaptured turns counted, never placed). Per-section `completeness` and `configuration_complete` are added.
- **v1.2.0:** v1.1.0 plus C3′. Codon identity uses the loader's scope (record presence ∈ {rendering presence, "field"}). The angle is a declared secondary basis (`identity_basis: mutable-angle`, `conditional: true`), and conditional elements are flagged per comparison (`conditional_identity_n`, gap `conditional-identity:mutable-angle`).
- Each version has its own chain: entry_id prefix `<version>:`, chained per (version, presence).

## Results (disposable `obs_test_*` ledgers, same `now`; aggregate counts only)
**Stage 1 invariance (v1.0.0 → v1.1.0):** PASS. 622/622 entries compared, 0 differences across 15 set-mathematics field groups (verified/uncertain/text availability; per scope: predecessor, verified transform excluding `adjacent`, uncertainty enumeration, text layer).
- Completeness added: MRA malformed-bullet UNRESOLVED 458 · cache after-terminator UNRESOLVED 2,779 · council 11. Entries marked partial: 286.
- Timestamp-derived fields (reported separately): 0 changes to adjacency, uncaptured counts or participation. Unplaceable turns affecting a comparison: 0.

**Stage 2 delta (v1.1.0 → v1.2.0):**
- Codon transitions: CANDIDATES → VERIFIED(name+scope) 159 · CANDIDATES → VERIFIED(mutable-angle) 3 · angle-VERIFIED → VERIFIED(mutable-angle), same record, 398 · unique-name → name+scope, same record, 7,453 · CANDIDATES unchanged 310 · UNRESOLVED 1.
- **Angle-VERIFIED → CANDIDATES: 0 · VERIFIED → different record: 0.**
- Entries with a changed verified set: 120. Comparisons with changed sets: S1 192/554, S2 210/607, S3 208/601.
- Relation changes: S2 DR→PO 1, S3 DR→PO 1. Every |ΔJ| is ≤ 0.05.
- Uncertainty removed entirely: S1 50, S2 56, S3 55. Text layer changed: 0.
- Comparisons involving conditional (angle) identity: S1 389, S2 423, S3 418.

**Reproducibility:** the new code reproduced production v1.0.0 with 622/622 chain hashes matching (current store, stored participation). Fixture v1.0.0 = production v1.0.0 on all mathematics, gaps and participation. `verify(reproduce)` passed for all three fixture versions.

**Isolation:** Sanctuary collections fingerprinted before and after: identical. All fixtures dropped.

## Other corrections (no re-derivation needed)
- **C4:** grid relation/J cells show the compatible-outcome relation and range as the primary value, with verified-only as a secondary `v` line. The drawer does the same.
- **C5:** `pred_position` per column (none / previous-column / earlier-column / later-column / off-page). A `vs #n` or `vs ←pg` label is shown, and the `retained` glyph is used only when the predecessor is the previous column; otherwise `retained-remote`.
- **C6:** `/verify` returns `ledger_integrity`, `source_consistency` (now including component `evidence_hashes`) and optional `reproducibility` (`?reproduce=true`), each labelled separately. `/compare?a&b&mode=invariance|delta` reports counts only.
- **C7:** index/run-record failures handled inside the try block (status `failed`, lock released). New status `ok-with-errors`. Stale `running` runs are marked `abandoned`. The lock is renewed per presence and every 25 entries (`lock-lost` stops the run). Background task exceptions are logged. "Pending" is relabelled "Not yet measured".

## Tests
`tests/test_observatory_ledger.py` (24) + `tests/test_observatory_api.py` (15, updated for `retained-remote` / `not_yet_measured`) + `tests/test_observatory_v11.py` (7, new): **46/46 pass**. Frontend read-only UI test (iteration 18): all checks passed. Its 4 minor display notes have been fixed.

## Readiness
Production derivation of v1.1.0/v1.2.0 needs only `PRODUCTION_VERSIONS = ("1.0.0", "1.2.0")` (or with "1.1.0" as well). The startup catch-up then derives the new chain alongside v1.0.0, and the lattice version picker appears automatically. **Awaiting separate authorization.** Deployment has not been performed.
