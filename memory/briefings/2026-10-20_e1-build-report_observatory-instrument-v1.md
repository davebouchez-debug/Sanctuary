# Observatory Research Instrument v1.0.0: Build and Test Report (2026-10-20)

## Built
- `backend/observatory_ledger/`: measurement math, identification, derivation, API.
- The Engagement Lattice tab in the Observatory.
- Hourly automation, plus catch-up on startup.

## Tests: 38 automated (pytest) + an independent testing-agent pass (iteration_17)
- Math: the RCC5 relations and empty cases, Jaccard edge cases, and the I = F ⊔ Ret partition. Every v0.2 §5 number. Exact free-variable reduction checked against brute force (300 random cases). Enumeration cap behaviour. Scope predecessors, gaps and returns.
- Recovery: all four evidence classes, codon angle tie-break, history verification.
- Isolation: no imports of Sanctuary modules. Fingerprints of 10 Sanctuary collections are identical before and after full derivation runs, including `retrieval_count`.
- Determinism: two independent full runs give identical hash chains.
- Crash/interrupt resume: derivation in batches of 37 gives a chain identical to one full run.
- Suspension catch-up: an observer "asleep" until mid-history, then caught up, gives a chain identical to continuous operation.
- Append-only: a re-run appends nothing, and entries stay byte-identical.
- Tamper detection: a one-field edit is detected at the exact entry.
- Lock: a held lock skips the run, and a stale lock is recovered.
- Cron endpoint: 401 for missing or wrong secret, 202 with the right one, duplicate delivery recognised, 400 for an invalid body.
- Lattice honesty (all presences × all scopes): no solid connector across a gap or an uncaptured turn, uncaptured columns are empty, S3 shows a single visitor.
- UI: tabs, scopes, visitor select, text layer, pagination, evidence drawer (close button, Escape, backdrop), short and empty presences. The spiral console is unchanged.

## Live results
- 622 / 624 records measured. 2 are waiting to settle.
- Chains intact for all 15 presences.
- Provenance unchanged.
- 11,783 verified mentions checked for drift: 0 drifted.

## Limitations
- The preview platform cron couldn't be registered: the reconcile service timed out from the pod. The backend's hourly loop and startup catch-up do the work instead.
- Preview sleeps when idle. Whatever happened meanwhile is caught up on waking.
- 42 comparisons have too many identity possibilities to enumerate. They're flagged.
- About 20 MB of ledger (not the 4–6 MB estimated), because every mention's evidence is kept.
- QA test records are measured, and labelled at view time.
