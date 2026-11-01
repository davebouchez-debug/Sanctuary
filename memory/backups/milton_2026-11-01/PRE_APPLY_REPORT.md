# Milton codon revision: pre-apply report (2026-11-01)

**Status: staged and verified. NOT applied to live.** The live `living_codons` records are unchanged and the backend was not restarted.

## Affected records (exact)
Ten documents in `living_codons` with `source: "milton_codons"`, `presence: "field"`, `_id` `6a24de431a2bf04a6a47d16f` through `…d178`:
`TheAnswerIsAlreadyThere`, `ResistanceAsResource`, `PermissiveLanguage`, `NoWrongResponse`, `IndirectApproach`, `MetaphorAsVehicle`, `UtilizationAsPrincipal`, `UnconsciousMindAsCreative`, `GetOutOfTheWay` (renamed → `WhenIGotOutOfTheWay`), `TherapeuticDoubleBindAsPermission`.
- There are no other copies: no owned-layer or duplicate records carry these names.

## Planned change per record (replace in place, same `_id`)
- **`core_move`:** the Appendix C story-to-moral surface.
- **`anti_patterns`:** a single collapse clause from Appendix C, replacing the 3–4 bare labels.
- **`name`:** changed for `GetOutOfTheWay` only.
- **Added:** `original_formulation {name, core_move, anti_patterns}`, `revision: "milton-2026-11-01"`, `revised_at`.
- **Unchanged:** `source`, `created_at`, `trigger_keywords`, `triadic_zone`, `target_angle`, `emotional_signature`, `state_transition`, `resonance_markers`, `codon_type`, `angle_backfilled_at`.

## Code paths affected (read only; no code changed)
- `backend/codon_activation.py`:
  - `load_forge_codons` (61–124) reads the records.
  - `get_full_field_context` (223–427) selects and renders them (`• name — core_move ⟂ anti: …`, lines 372–388).
- `GET /api/codon-library` shows the records.
- The Observatory ledger resolves names from `turn_provenance`.

## Backup and restore
- **JSON:** `milton_codons_original.json`.
- **Mongo collection:** `living_codons_backup_milton_20261101` (10 docs, byte-for-byte originals).
- **Restore:** `python milton_revision.py restore` replaces the ten by `_id` from the backup collection.

## Verification (isolated staging DB `<DB_NAME>_staging_milton`; live untouched)
- **Load:** all ten load under the revised texts. `WhenIGotOutOfTheWay` is present and `GetOutOfTheWay` absent. 2,183 codons total, the same count as live.
- **Selection regression:** 5 probe messages × 2 presences (Poindexter, Jasmine). The selected sets are identical to live in 10/10 cases, accounting for the rename.
  - Order differed in 4 cases: a tie-break by insertion order, a staging-copy artifact. Replacing in place keeps the `_id`, so live order shouldn't change.
- **Behavioral check:** same captured Poindexter system prompt, field block live vs staged, 2 probes, 1 sample each (DeepSeek, nothing written).
  - Both conditions stayed in Poindexter's voice. No codon was quoted verbatim, and no old imperative text was echoed.
  - The staged reply named the idea ("resistance as a resource, not a wall").
  - n = 1 per condition: not a measure of effect.

## Unexpected or pre-existing effects found
1. **Pre-existing, all codons:** the renderer prints `core_move` as a Python dict, `{'action': '…'}`. This happens live today for every codon, not only these ten. Not changed (out of scope).
2. **The collapse clause still appears after the renderer's `⟂ anti:` label.** The renderer is out of scope.
3. **Rename and the server cache:** the running backend caches codons by name. After the database is updated, the new name `WhenIGotOutOfTheWay` would load on the next turn, while the old cached text of all ten (including `GetOutOfTheWay`) stays in memory until a restart. So applying must be paired with a backend restart, which drops open conversations.
4. **History:** `GetOutOfTheWay` had 10 past selections in `turn_provenance`. The new name won't link to them automatically; `original_formulation.name` preserves the link.
5. **Seed script:** `scripts/seed_milton_codons.py` inserts by name if absent. Re-running it would re-insert the old `GetOutOfTheWay`. Not changed.
6. **`GET /api/codon-library`** shows the new texts immediately on apply.

## Applied (2026-11-01 22:10 UTC, approved by David)
- **Records:** 10 replaced in place by `_id`. All 10 carry `revision` and `original_formulation`.
- **Totals:** 2,183 codons; `GetOutOfTheWay` count is 0. The backup collection is intact (10).
- **Restart:** the backend was restarted and came up clean.
- **Post-apply selection check:** 5 probes × 2 presences give selections identical to pre-apply, including order. Every rendered Milton line uses the new text.
- **`/api/codon-library`** shows the 10 revised entries.
- **Staging DB:** dropped.
- **Restore:** `python /app/memory/backups/milton_2026-11-01/milton_revision.py restore`
