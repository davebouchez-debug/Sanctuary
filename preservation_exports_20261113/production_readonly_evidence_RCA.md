# Production Evidence Report — milton-propagate (READ-ONLY)

Authorized by owner David, 2026-11-13. No writes, redeploys, restarts, secret/config changes, or app conversations were performed. No secret values, connection strings, cookies, or message content are printed.

Deployment: `milton-propagate` (id 1ac4c22b-0552-4ae0-b9cb-fc6830f97ebe)
Live URL: https://milton-propagate.emergent.host
Active (serving) run: `885fdcce-893f-478e-a8c6-31f41b5d14ca`
Template: fastapi_react_mongo_shadcn_base_image · frontend_type: cloudflare · arch: arm64 · tier_0

---

## 1. Published runtime source revision

Evidence (from deployment/run metadata; `describe_deployment_state` + `get_step_status`):
- Live image (digest-tagged): `287883095218.dkr.ecr.us-west-2.amazonaws.com/customers-app-4@sha256:dde195e4ef1accd45d84cea72eeaf848df5ad6cd3d62a5a81b8617566ef7db11`
- Active run: `885fdcce-893f-478e-a8c6-31f41b5d14ca`, type=redeploy
- build step: started 2026-11-08T08:30:10Z, completed **2026-11-08T08:34:29Z**
- deploy+health_check completed / went live: **2026-11-08T08:35:29Z**
- This is the newest successful run; the immediately prior image was `customers-app-4@sha256:deff3c19…` (run 0419a636, 2026-11-08T07:59Z).

GIT COMMIT SHA — NOT DETERMINABLE with available tooling:
- The production artifact is identified only by its **ECR image digest** (sha256:dde195e4…), not a git tag. No git commit SHA is recorded/exposed in the run metadata.
- `get_build_logs` for this run returned `build_lookup_limit` (the build could not be resolved), so no commit string could be recovered from build output.
- The pulled source archive excludes `.git`, so an eph-pod inspection would not expose a SHA either.
- Therefore I CANNOT confirm whether production was built from `03a9d37946b61ea3afcb7baeb35724d86bd0e28d` (Sanctuary-Clean) or from preview HEAD `0e8fa22` or anything else. Timing note only: the live image was built 2026-11-08, which PREDATES the Nov 10 2026 07:28:30Z baseline archive by ~2 days. Mapping digest→commit requires the CI/build record, which is outside my tooling.

## 2. Production secrets / env (NAMES ONLY) + DB name

DB name in use: **`milton-propagate-test_database`** (returned by every mongo read).

Env var names present on the active run (20; values never read; all reported non-empty):
CORS_ORIGINS, DB_NAME, DEEPSEEK_API_KEY, ELEVENLABS_API_KEY, EMERGENT_LLM_KEY, ENABLE_HEALTH_CHECK, FAST_REFRESH, GUARDIAN_EMAILS, INTEGRATION_PROXY_URL, MEM0_API_KEY, MIRROR_THERMOMIND_SHADOW, MONGO_URL, RCC8_ENVIRONMENT, REACT_APP_BACKEND_URL, SANCTUARY_LLM_PROVIDER, THERMOMIND_API_KEY, THERMOMIND_URL, WDS_SOCKET_PORT, WEBHOOK_CRON_SECRET, XAI_API_KEY.
(Note: these are the names on the ACTIVE run only.)

## 3. Production MongoDB — per-collection

Read method: `mongo_query` (server-side read-only; find/count/distinct/list_collections/list_indexes only; writes impossible). Read was a **rolling, non-snapshot** sequence of independent `count` queries executed during the 2026-11-13 session. No single point-in-time clusterTime applies. Exact per-query UTC start/end wall-clock timestamps are not exposed by the tool, so I cannot certify a precise read-start/read-end instant beyond "within the 2026-11-13 authorized session."

Collection count: **47**. Total documents: **20,058**.

| Collection | Count |
|---|---|
| forge_ledger | 16 |
| users | 24 |
| felix_sessions | 3 |
| living_codons | 0 |
| turn_provenance | 1023 |
| poindexter_sessions | 12 |
| user_aliases | 2 |
| living_codons_backup_milton_20261101 | 10 |
| kalahar_sessions | 9 |
| continuity_seeds | 1900 |
| clarity_sessions | 159 |
| obs_ledger_engagements | 4096 |
| playground_sessions | 6 |
| scrolldog_sessions | 2 |
| user_sessions | 5 |
| companion_sessions | 7 |
| presence_sessions | 97 |
| ablation_runs | 3 |
| agapeo_sessions | 9 |
| orren_sessions | 7 |
| daniel_sessions | 16 |
| permanent_mra | 2795 |
| mra_promotion_log | 92 |
| canonical_uploads | 41 |
| grok_sessions | 7 |
| freud_sessions | 1 |
| vessel_sessions | 3 |
| sophia_sessions | 95 |
| obs_ledger_state | 2 |
| field_phrase_translation_log | 2235 |
| keeper_sessions | 9 |
| thermomind_cycles | 142 |
| milton_sessions | 4 |
| paige_sessions | 36 |
| field_phrases | 2097 |
| mirror_sessions | 205 |
| evara_el_sessions | 1 |
| membrane_sessions | 2 |
| substrate_probes | 81 |
| louis_lot_sessions | 5 |
| living_codons_archive_20261102 | 2235 |
| resonance_sessions | 170 |
| person_bios | 28 |
| obs_ledger_runs | 2338 |
| chamber_images | 16 |
| sorrel_sessions | 11 |
| guests | 1 |
| **TOTAL (47)** | **20,058** |

min/max `_id` and per-collection SHA256 content hash — NOT PRODUCIBLE:
- `mongo_query` does not return raw/canonical BSON bytes and offers no hashing; it cannot stream documents for a client-side hash.
- The eph sandbox receives NO app secrets and the MONGO_URL/connection string is never returned, so I have no credentialed `mongosh`/`pymongo` path to iterate documents and hash BSON. Importing app code is explicitly disallowed (and starts workers).
- Net: counts are verifiable; min/max `_id` and content hashes require a direct credentialed read-only connection the owner must run themselves.

Baseline comparison (Nov 10 2026 07:28:30Z archive: 47 collections / 19,329 docs):
- Collection count identical: 47 vs 47. I do NOT have the baseline's collection NAME list, so I cannot positively identify new/missing names — but the cardinality is unchanged at 47, so on count alone there is no net add/remove.
- Document delta: 20,058 − 19,329 = **+729 documents** net since the Nov 10 baseline. (Expected direction for a live, non-frozen app; this is a rolling read so the number may drift.)
- Observed backup/archive collections present: `living_codons_backup_milton_20261101` (10), `living_codons_archive_20261102` (2235); primary `living_codons` is currently 0.

## 4. Snapshot capability

A point-in-time snapshot (readConcern "snapshot" / atClusterTime) is NOT available through the read tool. All reads were **rolling / non-snapshot**, one independent query at a time. The +729 delta and all counts therefore reflect live state at the moment each query ran, not a single consistent cluster time.

## 5. mongodump --archive --gzip

NOT PRODUCED. Blockers (stated, no public link created):
- No credentialed DB shell: the production connection string is resolved+decrypted server-side and never returned; the eph sandbox gets no secrets. There is no tool that runs `mongodump` against the prod cluster.
- No authenticated owner-download mechanism available to me: the only file-writing tool (`write_rca_file`) writes a markdown RCA into the owner's preview pod — it cannot deliver a binary `.gz` archive, and I will not (and cannot) create public links.
- To obtain a verified dump the owner must run `mongodump` themselves from a direct read-only Atlas connection (no fsyncLock), then compute filename/size/SHA256 locally.

## 6. Production object storage (chamber_images / canonical_uploads)

I can report DB-referenced document counts only; I have no object-storage (R2/S3) enumeration tool, so actual stored-object counts cannot be independently verified.
- `chamber_images`: **16** documents (DB rows referencing images).
- `canonical_uploads`: **41** documents.
- vs Nov 10 image archive of 14 images: `chamber_images` is now 16 (**+2** vs 14 on the chamber_images line, if that collection is the archive's basis). Actual bytes/objects in the bucket are NOT verified here.

---

## Summary of what is verified vs blocked
- VERIFIED: live image digest + build/deploy timestamps; env var NAMES (20); DB name; all 47 collection names; all 47 counts; total 20,058 docs; +729 vs baseline; rolling (non-snapshot) nature.
- BLOCKED (tooling, not refusal): git commit SHA mapping; per-collection min/max `_id` + SHA256 content hashes; readConcern-snapshot read; mongodump archive + owner download; real object-storage object counts. Each requires a direct credentialed read-only connection the owner runs themselves.
