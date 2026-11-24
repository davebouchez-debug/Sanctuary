# Sanctuary (milton-propagate) — Read-Only Production Diagnostic

Scope: read-only report, no changes made, no deploy triggered.
Deployment: milton-propagate | active run: e4607d3e-e0fc-4c66-9d35-b5cc4aa70e9c
Database: milton-propagate-test_database | Live URL: https://milton-propagate.emergent.host
Note on "now": latest data timestamp observed is 2026-11-22T06:02Z, so the 30-day window below uses cutoff 2026-10-23T00:00:00Z (counts were identical at a 2026-10-21 cutoff).

## 1. Session collections (document count / most recent created_at / created in last 30 days)
| Collection | Total docs | Most recent created_at | Created in last 30 days |
|---|---|---|---|
| clarity_sessions | 159 | 2026-10-30T05:18:48.396945+00:00 | 1 |
| resonance_sessions | 171 | 2026-11-22T01:49:58.447034+00:00 | 5 |
| mirror_sessions | 207 | 2026-11-17T10:48:33.474809+00:00 | 8 |

created_at is stored as an ISO-8601 string; range comparison is lexicographic (valid for this format).

## 2. presence_history
- Collection `presence_history` does NOT exist in the database (verified: collection_not_found; 48 collections present, none named presence_history). "Count by kind" therefore not available.
- Closest existing collection is `presence_sessions` = 97 documents. It has NO `kind` field (distinct on `kind` returned 0 values), so a per-kind breakdown is not possible there either. If the intended collection/field differs, re-run with the exact names.

## 3. Unauthenticated endpoint access (does it respond WITHOUT a 401/403?)
Both endpoints return HTTP 200 to an unauthenticated GET — i.e. they are publicly reachable, NO auth wall:
- GET /api/observatory/status → 200 (JSON: derivation_version 1.0.0, ledger_entries 1068, provenance_records 1067, per-presence entries). resp ~1365ms.
- GET /api/provenance/stats → 200 (JSON: total 1067, per_presence breakdown, latest_timestamp 2026-11-22T06:02:42Z). resp ~390ms.

Both serve full data anonymously. Flag for planning if these are meant to be gated.
