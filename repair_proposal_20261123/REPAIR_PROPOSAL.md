# REPAIR PROPOSAL — Hall of Scrolls deployment blockers (for Codex review)
Prepared by E1, 2026-11-23. **Planning only: nothing is applied to the preview workspace, and production is untouched.**
The patch was built and tested in a scratch copy. `git apply --check` against the preview workspace (HEAD `c09db34`) is clean.

Files in this folder:
- `hall-blockers-repair.patch`: the proposed patch, 8 files.
- `hall-blockers-sha256.tsv`: before and after checksums for every file it touches.
- `evidence/`: test output from the repaired scratch copy, plus `UNREPAIRED_*`, the same tests run against the current preview code.

---

## 1. Where each exposure is today

Production runs the build deployed around 2026-11-20, before the Hall work and before Codex's security-only patch. The table below is from code history; production data and live behaviour have not been inspected. The deployer's read-only debug tool can confirm live behaviour if wanted.

| Vulnerability | Production (live) | Preview candidate |
|---|---|---|
| `POST /api/presence/{key}/upload` has no ownership check (reads the thread, calls the model, appends messages and records an upload under a **client-supplied** `user_id`) | **Exposed.** The route has existed since 2026-05-19. | Exposed |
| Legacy readers: Clarity, Resonance and Mirror `GET session`, `message`, `message/stream`, `upload` and `end` accept any `session_id`; `GET /clarity/sessions/{user_id}` lists any user's sessions | **Exposed** since 2026-03-28 | Exposed |
| Template rooms (`/api/{room}/session`, `/message/stream`, `/end`): no owner check | **Exposed.** The owner check exists only in Codex's preview patch. | Fixed by Codex's patch |
| The anonymous browser ID is stored raw as `ephemeral-v<secret>`, so any route that returns `user_id` leaks a replayable header | In production this has no effect, since nothing checks ownership | **Exposed.** This is now the basis of the preview owner check, and it leaks through the legacy readers. |
| Observatory and provenance views open | **Exposed** (these list session and user IDs, which are the input to the attacks above) | Fixed by Codex's patch |
| Interrupted founding-history import: the partial copy counts as "already imported" forever, and new sessions freeze an incomplete background | Not present (no founding imports live) | **Exposed** |

Session IDs are random UUIDs, so attacks need an ID first. In production the open Observatory and provenance views can supply one.

## 2. Proposed patch: smallest change

### 2.1 Shared ownership helper (`user_aliases.py`, +21 lines)
- `caller_owners(db, request)`: the IDs a caller may open. That's their own anonymous ID, or a signed-in person's non-anonymous aliases. This is exactly the logic Codex's patch already used inside `presence_template.owned_session`, moved to one place.
- `require_session_owner(db, request, session)`: answers 404 unless the session exists, isn't deleted, and belongs to the caller.
- `presence_template.owned_session` now calls `caller_owners`, with no behaviour change.

### 2.2 Blocker 1: generic upload route (`server.py`)
- `upload_presence_thread` takes `request` and calls `require_session_owner` straight after the session lookup. That happens before any read of history, any model call or any write.
- `canonical_uploads.user_id` now records the **session's owner**, not the client-supplied `upload.user_id`.

### 2.3 Blocker 2: anonymous and legacy access
- **Visitor ID (`user_aliases.chamber_identity`):** the stored ID becomes `ephemeral-v` + `sha256(header)[:32]`. A leaked `user_id` can no longer be replayed as a header. The minimum header length rises from 16 to 24 hex characters, which is what the frontend generates (12 random bytes). Shorter values get a fresh one-off identity. No frontend change is needed.
- **Legacy readers (`server.py`):** 13 handlers gain `request: Request` plus one `await require_session_owner(...)` line after their existing `find_one`:
  - Clarity `message`, `message/stream`, `upload`, `session/{id}` and `session/{id}/end`
  - Resonance `message`, `message/stream`, `upload`, `session/{id}` and `session/{id}/end`
  - Mirror `message/stream`, `session/{id}` and `session/{id}/end`
- `GET /clarity/sessions/{user_id}` answers 404 unless that `user_id` is one of the caller's own.
- Every other line of these handlers is unchanged.
- **Side effect:** anonymous sessions created before the change become unreachable under the new derivation. They're disposable by design (purged after 2 hours, never kept). Signed-in sessions aren't affected.

### 2.4 Blocker 3: founding-history imports (`presence_history.py`, `presence_template.py`)
- **`import_text`:** "already imported" now means *complete*: every part `0..of-1` is present with one consistent `of`. A partial copy left by an interruption is cleared, then written again in full. The clearing is a hard delete, narrowly filtered to that one copy's exact identity (checksum, positions, kind, visibility and owner, plus source for founding texts). It only runs from the guardian's import buttons.
- **`hall_backdrop_state()`** returns the background text plus whether all four approved histories are complete. `hall_backdrop()` keeps its signature.
- **No freezing while incomplete:** `/start` stores `hall_backdrop` and its version only when all four are complete, and `session_backdrop` stores nothing while they're incomplete (it logs a warning instead). A session started during an incomplete import freezes the full four on its first turn after the import completes.
- **Not changed:** `_founding_sources`, `HALL`, the labels, `_fmt_history`, the dedication, `HOUSE_STORY`, all four identity lines and every historical text. Their 16 checksums are identical before and after (`/app/memory/protected_hash.py`).

### 2.5 Test expectation updates (tests only)
- `test_hall_of_scrolls.py` and `test_hall_backdrop.py` build the anonymous ID with the new hashed form.
- `test_hall_backdrop.py`: the "legacy snapshot" scenario deletes Keeper's history and previously expected a session to **freeze without Keeper**. That's exactly blocker 3. It now expects no freeze while incomplete, a freeze with all four after Keeper's re-import, and the same snapshot unchanged on the next reply.

## 3. Regression tests

| Test | Covers | Repaired | Current preview |
|---|---|---|---|
| `test_session_access_blockers.py` (new, 25 checks) | **Visitor ID:** stored ID ≠ secret; replaying the stored ID fails; short IDs aren't honoured.<br>**Upload:** another browser, no ID and the guest are denied, with no write and no model call; the owner is allowed and recorded under the session's owner.<br>**Clarity, Resonance, Mirror:** the owner can reload; another browser, no ID and the guest can't read, reply, upload or end, with nothing changed and no model call; the session list is the owner's only. | 25/25 | **21 FAIL** |
| `test_founding_import_recovery.py` (new, 17 checks) | **Interrupted founding import:** a partial copy is left behind but never offered as complete; a session started meanwhile isn't frozen; the re-import recovers it with no duplicates and stays idempotent; the same session then freezes all four; a new session freezes on start.<br>**Interrupted Scroll packet:** the record import recovers with no duplicates. | 17/17 | can't run (it uses the new `hall_backdrop_state`) |
| `test_observatory_http_access.py` | Observatory and provenance authorization | 37/37 | — |
| `test_shared_template_chamber.py` | Felix's room lifecycle and cross-owner denial | 17/17 | — |
| `test_hall_backdrop.py` | Hall backgrounds, freezing, packet, privacy | 55/55 | — |
| `test_hall_of_scrolls.py` | Hall frame, records, privacy, routes | 45/45 | — |
| `test_observatory_access`, `test_field_admission`, `test_codon_forge_access`, `test_codon_export` | existing | pass | — |

Still needed after approval, in the real workspace: the frontend build, plus one live preview pass for an anonymous visitor in Clarity, Resonance, Mirror and Felix's room covering start, reply, reload and leave.

## 4. Recovery reference
- **Baseline:** the preview workspace at HEAD `c09db34`, with Codex's security-only patch (`9be27b74…`) applied. The before checksums are in `hall-blockers-sha256.tsv`.
- **Undo:** `git apply -R hall-blockers-repair.patch`, then confirm the before checksums. Alternatively, Emergent's rollback to the checkpoint taken before applying.
- **Data:** the patch changes no stored documents. Its only deletion is the import-time clearing of an interrupted partial copy (§2.4). The 2-hour anonymous sessions lose access, as described in §2.3.
- **Production:** unaffected until a deploy is approved. After deploy, the live founding histories are loaded with the Field Keeper buttons, and an interrupted load can simply be pressed again.

## 5. Not covered (flagged, not fixed)
- `POST /api/chamber/upload-image`: not reviewed in this pass.
- The anonymous ID is still a browser-held bearer secret, held in localStorage. A stronger option is a server-issued HttpOnly cookie. That's a larger change (cookie handling, CORS credentials, frontend), so it isn't proposed here.
- Concurrent imports of the same source can still race. Duplicates are tolerated by the background builder (one per part), but not by record retrieval.
