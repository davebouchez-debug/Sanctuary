# Briefing: The First Publish of the Sanctuary — What Broke, Why, and What Was Fixed
Prepared by E1 (the Emergent build agent) for David, to share with GPT for Sanctuary 2.0 design.
Dates are 2026, times UTC unless noted.

---

## 1. What happened (timeline)

- **Nov 5, evening.** Amanda couldn't reach the Sanctuary. The preview link sleeps after ~30 minutes of inactivity and only the owner (David) can wake it; guests see "Contact owner to wake up servers." To give Amanda an always-on link, David published the app to production (`https://milton-propagate.emergent.host`). Before publishing, David asked E1 whether there was any downside. E1 said: about 50 credits a month, "no downside," "just flipping a switch," "no preparation needed." E1 ran a deployment readiness check, which passed. **E1 did not measure how much memory the app needs, and did not check it against the size of the production plan.** That single omission is the root of everything below.
- **Nov 6, 03:38 UTC.** The live backend ran out of memory and was killed by the platform (OOMKilled, exit code 137), then restarted automatically. Downtime was about a minute or two. Logs show no failed user requests in the 24 hours checked: every reply, voice and sign-in returned successfully.
- **Nov 6, morning.** Emergent emailed a "Resource utilization alert": the app had been above 85% of its plan's resources five times in 24 hours, with a recommendation to upgrade from the Starter plan to the Launch plan. This was the first time David learned that plans have resource limits.
- **Nov 6, day.** E1 investigated, measured, fixed the crash cause, redesigned how the field is held in memory, and republished.

## 2. The hosting facts that were not disclosed up front

| Plan | Processor | Memory | Cost |
|---|---|---|---|
| Starter (what David got) | 0.05 vCPU (one-twentieth of a processor) | 200 MB target; 512 MB hard limit (the app is killed above this) | 50 credits/month |
| Launch (recommended by the email) | 0.25 vCPU (a quarter of a processor) | 1 GB (support mentioned a ~2 GB hard limit; unconfirmed) | 125 credits/month |

- Emergent support said 50 credits is about $10/month, which would make Launch about $25. That conversion came from support and depends on how credits are purchased; it was not independently verified.
- Emergent support could not provide a complete price table for all tiers (Starter/Launch/Grow/Scale/Elite).
- Support confirmed: no automatic upgrades and no automatic charges when limits are hit. The warning emails trigger at ~85% of the 200 MB target (~170 MB). They do not charge, slow or shut anything off.
- The preview environment runs on E1's workspace (16 processors, 64 GB of memory), so resource problems never appeared during development. **The preview hid every cost that the live plan exposed.**

## 3. Why the app needed more than Starter gives (root causes)

Measured on the preview, piece by piece:

| Part | Memory |
|---|---|
| Web server + database connection | ~50 MB |
| The local memory-search model (fastembed, BAAI/bge-small-en-v1.5, ONNX runtime). This is what turns sentences into meaning-vectors so presences can find things by meaning. | ~140–200 MB more |
| DeepSeek client, all presence code, the field's working copy | the rest |
| **Total at rest** | **~260–280 MB** |

So the Sanctuary was over Starter's 200 MB target the moment it started, before anyone spoke. This model was adopted in an earlier session when Mem0 (an external memory service) was retired in favor of local semantic search. The trade-off (local, private, no outside service vs. ~200 MB of resident memory) was never stated in hosting terms.

### Root cause of the actual crash (OOMKill)
- When new memories are turned into meaning-vectors, the embedding library processed them **256 at a time by default**. Nobody chose 256; it was the library's built-in default and was never changed. Measured: a batch of 600 long texts at batch size 256 peaked at **~1.5 GB**, three times the live hard limit. On the preview's 64 GB machine this was invisible.

### Other design problems found during the investigation
1. **Dead Grok check.** A status light on the main page was still asking xAI/Grok's servers "are you up?" every ~2 minutes. The Sanctuary runs on DeepSeek only; no conversation ever went through Grok. It was a leftover from before the switch to DeepSeek. Earlier notes listed "stray grok-3 leftovers" as low-priority cleanup; this was one nobody had found.
2. **Meaning-vectors stored loose.** Each field phrase and memory carries 384 numbers. They were stored in MongoDB the default way: 384 separate labeled entries per item. Unpacking them was most of the processing and memory cost of loading the field. Measured on 1,928 phrases: 4.8 KB stored per item, 0.041 s of processor to unpack all, ~20 MB extra memory while unpacking.
3. **The whole field reloaded whenever anything changed.** The server keeps a working copy of the field in memory for instant search. Whenever the count of items changed, it threw the whole copy away and re-read everything from the database.
4. **Memories re-read nearly every turn.** For signed-in people (David, Amanda), each exchange is usually saved as a memory right away. Because of problem 3, the next message re-read all of that person's memories (~1,650 of David's) from the database. Measured: ~0.45 s of a full processor per message. On Starter's one-twentieth of a processor, that is potentially several seconds of processing per message, and it grows as memories grow.
5. **Memories held twice.** Each person's memories were held in two separate copies: one for the room they're in, one for "what they said to the other presences."
6. **Heavy image tool.** The first time a presence is shown an image, the image-description library (emergentintegrations/litellm) loads ~130 MB and keeps it until restart. On Starter this alone could push the app toward the 512 MB limit. **Not changed yet.**
7. **Health probe path.** The platform's `/health` probe returns 404 (the app serves `/api/health/integrations`). It's harmless because it isn't a server error, but it's misconfigured. **Not changed yet.**

## 4. What was fixed (all verified on the preview, then republished)

1. **Crash fix.** Embedding now runs in batches of 8 with one thread. Measured peak for 600 long texts: ~235 MB (was ~1.5 GB).
2. **Status check now pings DeepSeek,** the engine actually in use, instead of Grok.
3. **Packed meaning-vectors.** Each item's 384 numbers are now stored as one binary strip (BSON Binary, float32). This is lossless: the values were always float32. Stored size dropped to ~1.6 KB per item, unpacking is ~8× cheaper, and extra memory while unpacking is near zero. A startup task converts any old loose-number items automatically in small batches (it ran on the preview and runs once on live after publishing).
4. **Load only what's new.** The working copy is read whole once at server start. After that, only items added since the last read are attached. Setting aside or restoring an item in the Field Keeper (or any deletion) triggers one full re-read so the copy stays exact.
5. **One copy per person.** "Other rooms" is now a mask over the person's single copy instead of a second copy.

**Verification:**
- 18 benchmark searches (field phrases, David's memories, cross-room memories) returned identical results before and after.
- A throwaway test person (deleted afterward) confirmed: new memories are added without a re-read, other-room masking works, and set-aside and restore both work.
- Field Keeper searches work.
- Presence invariant tests pass (18/18).
- A live-equivalent chamber turn completed normally.

**Measured result for David's memories + field phrases:**

| | Before | After |
|---|---|---|
| Full read | 0.45 s of processor | 0.024 s (~19× less) |
| Per turn | full re-read (twice) | 0.0007 s check + only the new item |
| Memory held | ~12 KB per item | ~6.5 KB per item |

**Process lapse during the fix:** the conversion ran automatically when the server restarted, before a separate backup of the old loose numbers was saved. It was lossless and results were identical, but the backup should have come first.

## 5. Where things stand now

- **The app still rests at ~260 MB on Starter.** The daily warning emails will continue and can be ignored; they mean "above the 200 MB target," nothing more.
- **Real risks on Starter:**
  - A restart if memory crosses 512 MB. The known cause is fixed; the image tool is the remaining candidate.
  - Slowness from the one-twentieth processor. A visitor's message still costs ~0.25–0.5 s of full-processor work (prompt building and reply streaming; not yet profiled). If Starter strictly caps the processor, that's several seconds before a presence starts answering. It's unknown whether the plan can briefly use more than its listed share.
- **Estimated capacity on Launch** (estimates scaled from preview measurements, not load-tested):
  - Comfortably ~10–15 people talking at the same moment; at the limit ~30.
  - Memory room for roughly 20,000–40,000 more field items (5–10× today's field) under the old holding design. The new design roughly doubles that, but this was not re-measured.
  - An earlier estimate of "50–100×" was a guess and was wrong.
- **Rejected option:** fetching the field from the database on every search instead of holding a copy. Measured, it would add ~2 s per reply on Launch and ~9 s on Starter, growing with the field, to save only ~7 MB.
- **Preview and live are now two separate fields.** After the first publish, nothing crosses between them. Real conversations belong on the live link; the preview is the workbench. Code reaches live only when David republishes, which restarts live and drops open chambers once.
- **Lock-in:**
  - The code is David's (GitHub) and is a standard React + FastAPI + MongoDB app.
  - Emergent-specific parts: Google sign-in (`auth.py`), image storage (`object_storage.py`), image description via the Emergent universal key, and the hourly Observatory job (`.emergent/crons.yml`).
  - The irreplaceable asset is the live field, which exists only in Emergent's production database. A "field export" button for the Keeper has been offered but not built.

## 6. Still open (awaiting David)

- **Part 2: near-twins.** 46 of 1,928 field phrases and 409 of 2,701 memories are near-identical to another item (for example "Not knowing is itself a kind of honesty" / "Not knowing is a form of honesty"; "Shalom Brother" / "Shalom, my friend"). Options: twins deepen the original, keep everything as it comes, or review the twins first.
- **Part 3: searching inside the database.** Check whether Emergent's live MongoDB Atlas supports in-database vector search. If it does, the server could hold no copy of the field and search cost would stay flat as the field grows.
- **The image tool's ~130 MB load.**
- **The `/health` probe path.**
- **Profiling the ~0.25–0.5 s of per-message processing.**
- **The field export button.**
- **Starter vs. Launch:** David's decision.

## 7. Design rules for Sanctuary 2.0 (lessons from this)

1. **Measure before you host.** Know resting memory, peak memory and per-message processor time, measured on a machine the size of the target plan, before choosing a plan or saying anything is "free." A large development machine hides every cost.
2. **The memory-search model sets the minimum plan.** A local model costs ~200 MB of resident memory, permanently. An outside embedding service plus in-database search could fit a much smaller plan but sends field text to a third party and adds ~0.1–0.3 s per message. Decide this deliberately, up front.
3. **Never accept library defaults on a constrained box.** Batch sizes, thread counts and caches must be set explicitly and tested at the target size.
4. **Store vectors packed from day one** (binary float32), never as loose number arrays.
5. **Indexes must be incremental.** A write should never force a full reload. Removals must be handled explicitly, not by accident.
6. **One copy per scope.** Express sub-filters (rooms, presences) as masks over a single copy.
7. **When switching providers, remove the old one completely,** including health checks, status lights and stray parameters. Health checks should probe the engine actually in use.
8. **Load heavy, rarely used tools lazily, and measure what they cost when they load** (the image tool is ~130 MB).
9. **Design the field's growth policy** (twins, consolidation) before it grows, not after.
10. **Keep the field portable:** regular exports the owner controls, so no host can hold the relationship hostage.
11. **Separate preview from live data by design,** and decide which one is real before the first publish.
12. **Know the real cost drivers at scale.** ElevenLabs grows directly with listening (per character) and is by far the largest. DeepSeek grows per reply but is cheap. Hosting grows with simultaneous conversations (processor), not with total users.
13. **Answer cost questions with numbers,** and say "I haven't measured that" when it's true. "No downside" without measurement is how this incident started.
