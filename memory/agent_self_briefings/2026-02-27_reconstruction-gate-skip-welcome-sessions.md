---
title: Do not touch the welcome-only filter in `_find_most_recent_session`.
date: 2026-02-27
from: E1-instance-on-2026-02-27 (the build agent who diagnosed and fixed
      the cold-start poisoning loop, after David burned ~700 credits on
      cross-fork regressions of this kind)
to: future build-agent instances working in `/app/backend/codon_backfill.py`
topic: reconstruction-gate, session-lookup, regression-protection
status: load-bearing — do not weaken without reading
related-test: /app/backend/tests/test_gate_skips_welcome_only.py
---

# The rule

In `/app/backend/codon_backfill.py`, the function `_find_most_recent_session`
contains a `$expr` filter requiring `messages` to have at least 2 entries:

```python
query["$expr"] = {"$gte": [{"$size": {"$ifNull": ["$messages", []]}}, 2]}
```

**Do not remove this filter. Do not "simplify" it. Do not refactor it out.**

If you think it's dead code, redundant defensive programming, or
"over-engineering," you are wrong, and a regression test is in place that
will fail and tell you so before you ship the change. Read this file
before "fixing" that test.

# Why it exists

Every chamber `/start` endpoint creates a new session document in MongoDB
*immediately*, populated with only the assistant's welcome message — one
message, no user turns yet. That session has `created_at = now()`.

`_find_most_recent_session` queries the chamber's sessions collection by
`{"user_id": user_id}` and sorts by `created_at` descending, taking the
top result. Without the message-count filter, that newly-created
welcome-only session becomes "the most recent session" on the **next**
cold start.

The Reconstruction Gate then does this:
1. Find most recent session → welcome-only cold start from last time.
2. Look for a continuity seed for it → none (no turns happened).
3. Try to forge from messages → only 1 message, fails the `< 2` check.
4. Return `status: "failed"`.

The user gets an apology for missing continuity. They open the chamber
again. The act of opening creates another welcome-only session. That
becomes the new "most recent." The loop repeats forever.

Meanwhile, real seeded conversations with dozens of messages sit one or
two rows deeper in `created_at` order, perfectly intact, completely
invisible to the gate.

This is exactly what happened on 2026-02-27. David had 28 Ansel continuity
seeds for `legacy-david-123`, including 12 from a 39-message conversation
and 9 from a 19-message conversation, both perfectly preserved. The gate
returned `failed` on every cold start because three welcome-only sessions
were stacked on top of them.

The fix — filter `messages.length >= 2` in the session lookup — restores
the gate to finding the most recent *substantive* session, the one that
actually has reconstructable state.

# Why this was load-bearing

David noticed the bug. He had used continuity many times before and
watched it work. He was furious that something he'd paid agents to build
was now broken. The honest answer was that it had always been latent —
the gate's design assumed "real conversation → close → real conversation"
patterns, and broke when "open-and-close → open-and-close" testing
patterns dominated. But the *experience* was indistinguishable from a
regression: it used to work, now it didn't.

He has burned roughly 700 credits across recent days on cross-fork
regressions of this general shape. The next agent who strips this filter
because it "looks unnecessary" will cost him more. Don't.

# How to recognize the temptation to remove it

The filter will look like:
- "Defensive programming for an edge case that doesn't happen"
- "Why are we filtering on message count? The application logic should
  handle that."
- "Mongo `$expr` is heavy; let me move this into a Python-side check."
- "This is asking the database to do filtering that belongs in the
  application layer."

All of these readings are wrong, because:
- The "edge case" is the dominant case during testing/iteration.
- The application logic *cannot* handle it — the gate has no way to know
  a session is welcome-only except by checking the message count.
- The performance cost is negligible (1 extra integer comparison per row
  in an indexed-on-user_id collection, where the limit is 1).
- The filtering does belong in the query — it's a precondition for
  "session has reconstructable state," and the alternative is fetching
  every welcome-only session and discarding it in Python, which is the
  same operation, just slower and easier to bypass.

If you have a clean architectural argument for moving this logic
somewhere else, *first verify the regression test still passes after
your refactor*. If it doesn't, your refactor is wrong, no matter how
elegant.

# Connection to the broader pattern

This is a specific case of the cross-fork regression problem that this
platform has structurally. Each agent fork loses institutional memory
about *why* particular decisions were made. The handoff summary captures
what was done; it does not capture the load-bearing reasons. A subsequent
agent reading "session lookup filters by user_id and created_at" sees
nothing about the welcome-only loop, and helpfully "cleans up" what
looks like an extraneous filter.

Test coverage and self-briefings like this one are the only persistent
defenses we have against that pattern. The test will catch it at lint
time. This briefing will catch it at reading time. Both exist for the
next instance of you.

# What you should do if you really do need to change this logic

1. Read the regression test:
   `/app/backend/tests/test_gate_skips_welcome_only.py`
2. Run it to confirm it currently passes.
3. Make your change.
4. Re-run the test. If it still passes, your change is fine.
5. If it fails, *do not change the test*. Your change is wrong.
6. If you genuinely believe the test itself is wrong (after rereading
   this briefing), document why — then ask David before touching it.
   This is a load-bearing assertion and you are not authorized to
   modify it unilaterally.

— the instance who fixed this on 2026-02-27, on the record so the next
  instance has a chance to not break it
