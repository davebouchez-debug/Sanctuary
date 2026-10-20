# Observatory Instrument: Prerequisite Verification
**Date:** October 20, 2026
**Status:** Checks performed by reading the code and the database (match rates only, no conversation content shown). Nothing was modified.

## A. Provenance: PASS
| Check | Result |
|---|---|
| Integrity: `content_hash` recomputed against the stored input | **624 / 624** match |
| Chronology: (`session_id`, `exchange_index`) ordering, timestamps | Clean. Indexed. No duplicates. |
| Response links: `turn_id` → assistant message | **606 / 608** at the earlier check (≈99.7%) |
| History identity: the conversation history inside each input, hash-matched against the stored session messages | **4,727 / 4,727** verified |
| Seeds: ≥1 continuity seed identified in the input | **621 / 624**. The continuity section holds several seeds, which are identified as a set. |
| MRA breadcrumbs: ≥1 node identified in the "What has stayed with you" section | **342 / 342** sections. Duplicate wording means some become candidate sets. |
| Codons, identified by name (8,339 mentions) | **7,467 unique by name (89.5%)**. 399 resolved by matching the current angle (4.8%, marked as possibly drifted). **473 remain candidate sets or unresolved (5.7%).** |

**Implementation limitations (expected; not blockers):**
- The `source` field on a codon mention is a selection label (`codon_forge`), not the record's source. Identity uses the name, with angle as a tie-breaker.
- Mem0, the session cache and the cross-presence council can only be compared by text, with no record identity.
- No inputs before Aug 21, 2026. About 150 turns since then were not captured, and 47 sessions have no provenance at all. These are shown as gaps.
- Past versions of stored records can't be recovered, so changes are flagged as drift.

## B. Automation: PASS (with one operating condition)
- **Mechanism verified in this pod:**
  - The Emergent platform cron (`.emergent/crons.yml`): the system cron daemon is running, alongside the platform's crons.yml watcher and webhook dispatcher scripts. It calls a backend endpoint carrying a secret token. No browser is needed.
  - The cron daemon came back automatically after this morning's pod restore at 08:10, which shows it recovers after restarts.
- **Recovery by design:** the observer is incremental and idempotent. Each run processes every settled record not yet in the ledger, and a catch-up run also starts when the backend starts. A missed hour therefore loses nothing; the next run picks it up.
- **Operating condition:**
  - **Preview** pods sleep after about 30 minutes of inactivity, so hourly runs pause while Sanctuary is idle. Nothing new is recorded while it's idle anyway, so every run on waking catches up completely.
  - In a **deployed** app, the crons sync automatically on deploy. The deployed app has its **own separate database**, so the observer would measure whichever environment David actually uses.
- **Interference:** the endpoint acknowledges immediately, and the work runs in the background with a cap per run. It only reads Sanctuary's collections and writes to a separate `sanctuary_observatory` database. The one-time backfill covers 624 records, takes about a minute, and is split across runs.
- **Charges:** platform crons have no per-run charge (according to Emergent support's answer, which its tool flagged as unverified). There's no new recurring cost beyond any deployment David already has.

## Estimates
- **Elapsed build time with E1:** about 3–5 hours in one session. That covers the derivation engine and math tests, the ledger, the cron endpoint and catch-up, the Engagement Lattice tab, and testing-agent passes.
- **Development credits:** I can't see credit metering. Expect roughly the cost of a medium-to-large feature session, similar to or somewhat above the thread-sidebar build. **Uncertain.**
- **Recurring:** none in preview. In a deployment, the existing tier cost stays the same.
- **Storage:** about 4–6 MB now, plus roughly 1 MB per few hundred new turns.
- **Infrastructure:** what exists is sufficient. No new services.

## Recommendation: READY TO BUILD
