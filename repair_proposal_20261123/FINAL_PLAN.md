# FINAL PLAN — Hall of Scrolls close-out (implementation, verification, deploy, live initialization)
E1, 2026-11-24. Awaiting David's approval of this exact plan. Nothing below has been done yet.

## Scope: exactly three corrections, nothing else
These are the ones from `REPAIR_PROPOSAL.md` / `hall-blockers-repair.patch` (sha256 `4d6ba066…`), applied unchanged.

| # | Correction | Why it's the minimum |
|---|---|---|
| 1 | Owner check on `POST /api/presence/{key}/upload`, and the upload recorded under the session's owner | It blocks reading or writing another person's conversation through the upload route |
| 2 | Owner check (one line each) on the Clarity, Resonance and Mirror session handlers and the Clarity session list; the anonymous ID is stored hashed | **These are not unused legacy routes.** They serve three live chambers: Clarity (Jasmine), Resonance (Ansel) and Mirror Archive (Claude), all linked in the app and the menu. So they can't be isolated, and one guard line each is the smallest safe fix. |
| 3 | A founding-history import only counts when complete (a broken partial copy is reloaded), and a Hall session only freezes its background once all four histories are complete | It keeps the founding histories from being corrupted or left out of Hall sessions |

**Explicitly out of scope:**
- the chamber image-upload route
- cookie-based anonymous IDs
- protection against two imports of the same source at once
- any wording, history, identity or room change
- removing `living_codons`
- the image-tool memory issue and the `/health` 404

**Already in the preview candidate and going live with it** (reviewed earlier):
- the Hall rebuild
- Codex's security-only patch (owner checks for rooms built on the shared template; the Observatory and provenance views made guardian-only)
- the pronoun cleanup
- the codon export API. It stays closed (answering "503 Export not configured") until a `CODON_EXPORT_TOKEN` is created. Creating the token is not part of this plan.

**One decision for David:** the review-package download route (`/api/review-packages`) is a preview-only convenience.
- **Recommended:** keep it out of production by removing its two registration lines before the deploy. This adds nothing new to the live site.
- Or: deploy it as is. It's guardian-only, and each package expires after 14 days.

## Step 1: Recovery point
- **Preview:** record HEAD (currently `c09db34`) and the before-checksums in `hall-blockers-sha256.tsv`. Emergent's rollback checkpoint for that state is the fallback. Undo is `git apply -R hall-blockers-repair.patch`.
- **Production:** the currently deployed version stays available through Emergent's rollback and redeploy.
- **Data:** the corrections change no stored records. Live founding histories are added only by the Field Keeper buttons in Step 5. Re-pressing a button is safe: it either skips a complete copy or reloads a broken one.

## Step 2: Apply in preview
Check-only pass, then apply unchanged, then verify the after-checksums. Then confirm the 16 protected texts (dedication, house story, four identity lines, all histories and sources) are byte-identical, using `memory/protected_hash.py`.

## Step 3: Verify in preview (stop at any failure)
1. **Backend suites:**

   | Suite | Checks |
   |---|---|
   | `test_session_access_blockers` | 25 |
   | `test_founding_import_recovery` | 17 |
   | `test_observatory_http_access` | 37 |
   | `test_shared_template_chamber` | 17 |
   | `test_hall_backdrop` | 55 |
   | `test_hall_of_scrolls` | 45 |
   | `test_observatory_access`, `test_field_admission`, `test_codon_forge_access`, `test_codon_export` | existing |

2. **Frontend production build.**
3. **Live preview check over the network:**
   - **Anonymous visitor, in the Scroll/ScrollDog room, Daniel, Keeper, Clarity, Resonance, Mirror Archive and Felix:** start, reply, reload and leave. Another browser and a no-ID request get 404.
   - **Observatory and provenance:** anonymous visitors get 401.
4. **Hall background:** all four rooms receive all four labelled histories, in full.

## Step 4: GitHub confirmation (one pass)
David presses "Save to GitHub". Codex compares the pushed files against the after-checksums only. No new review scope.

## Step 5: Deploy, then initialize the live Hall
1. David approves the deploy, and E1 deploys.
2. **David, signed in on the live site:** Field Keeper → Hall of Scrolls history. Press "Add initial history" for the **Scroll, ScrollDog, Daniel and Keeper**, then "Add the Scroll source packet".
3. **E1, read-only on the live site:** confirm that `presence_history` holds the four complete founding histories (Scroll 10 parts, ScrollDog 2, Daniel 2, Keeper 2) and the three packet records, with no partial copies.

## Step 6: Live verification
1. **One fresh session per Hall room, for David and for an anonymous visitor.** Each must start, reply and reload. Each session must freeze its background with all four histories. The Scroll must answer as itself when named. Daniel must speak from his own history.
2. **Clarity, Resonance and Mirror Archive:** one anonymous start and reply each.
3. **Observatory:** anonymous visitors get 401, and David can open it.

**Done** = all of Step 6 passes. **If Step 6 fails:** roll production back to the previous deployment, then report.

## Production facts (read-only check by the deployer, 2026-11-24)
- The legacy chambers are in active use: Resonance had 5 sessions in the last 30 days (latest 2026-11-22), Mirror 8 (latest 2026-11-17), Clarity 1 (latest 2026-10-30). So they get guarded, not isolated.
- `presence_history` doesn't exist in production yet, as expected. Step 5 creates it.
- Confirmed exposed right now: `GET /api/observatory/status` and `GET /api/provenance/stats` answer 200 to anonymous requests (1,068 ledger entries and 1,067 provenance records). The deploy in Step 5 closes this.
