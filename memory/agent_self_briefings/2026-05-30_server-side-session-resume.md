# Session Resume is SERVER-SIDE — do not move it to localStorage

**Date:** 2026-05-30
**Status:** Load-bearing. Read before touching any chamber `/start` endpoint or
chamber init effect.

## The problem it solves
The microphone is blocked inside the Emergent preview iframe. Visitors open the
app in a **new browser tab** to use voice. The previous "lose the whole
conversation" complaint came from each new tab starting a brand-new thread.

## Why NOT localStorage
A new top-level tab does **not** share the preview iframe's localStorage —
modern browsers **partition** third-party iframe storage. Anything persisted in
the iframe is invisible to the new top-level tab. localStorage cannot carry the
conversation across the iframe → new-tab boundary. (Verified empirically.)

## The mechanism (server-side resume)
Every chamber `/start` calls `find_resumable_session(...)` (server.py) — or the
inline equivalent in `presence_template.py` for Sophia/spiral — BEFORE creating
a new session. If the visitor has a session that is:
  - `active: true`
  - has `>= 2` messages (past the welcome)  →  Mongo filter `messages.1 exists`
  - last activity within **2 hours**
…it returns that session's full `messages` array with `resumed: true`. The
frontend renders `data.messages` when present, otherwise the single
`data.message` welcome.

Resolves across the visitor's alias ids via `resolve_user_aliases`.

## Why it doesn't break the fresh-welcome architecture
In-app navigation fires `/end` (`active: false`), so normal chamber re-entry
still runs the Reconstruction Gate + fresh welcome. Only genuinely-open threads
(new tab via `window.open`, reload — neither of which fires `/end`) resume.

## Gotchas for testers
- The presence `/message` endpoint persists the exchange only AFTER the ~10s LLM
  reply completes. If you reload before the reply lands, there's nothing to
  resume yet. Wait for the assistant reply before reloading.
- `/api/identity/recent` returns the most recent identity. Test sessions you
  create will hijack it and swap the UI visitor — always clean up test
  `user_id`s (regex `^pytest-|^resume-|^ctrl-`).
- Playwright `page.evaluate` in this preview reads a different storage context
  than the app frame; don't trust it for localStorage assertions.

## Related fix (same session)
`xai_chat.XAIChat` now accepts `history=` and seeds it via LlmChat
`initial_messages`. The old code did `chat.messages.append(...)` which crashed
(`XAIChat` has no `.messages`), silently breaking ALL non-streaming presence
multi-turn chat. Do not reintroduce `chat.messages`.

Regression: `backend/tests/test_session_resume.py` and the full-sweep script
`backend/tests/test_all_chambers_integration.py` (48 checks across all 5 chambers).

---

## UPDATE 2026-05-30b — Identity-ready gate (resume reliability)

Resume was matching on `user_id`, but chambers were calling `/start` **before**
App.js finished hydrating identity from `/api/identity/recent` (the 5s splash
safety can release early on slow loads). Result: `/start` fired with
`user_id=null`, created a throwaway session, and never resumed the visitor's
real thread. The testing agent caught this — "thread open" instead of
"continuing where you left off" after reload.

**Fix:** `IdentityContext` now exposes a `ready` flag. App.js sets
`window.__sanctuaryHydrated = true` and broadcasts `sanctuary-identity-change`
synchronously *before* releasing the splash. Every chamber's start/init effect
is gated on `ready`, so the thread opens exactly once with the settled identity.
Verified end-to-end: Paige (non-stream) and Clarity (stream) both restore the
transcript + show the indicator after a fresh load. Do not remove the `ready`
gate from the chamber init effects.

