# CODEX REVIEW BRIEFING — Hall of Scrolls reconstruction, Sanctuary 1.0
Prepared by E1 for David and Codex (GPT), 2026-11-22. Status: everything below is in PREVIEW ONLY. Nothing has been deployed.

---

## 1. What David asked for (in his words, condensed)

1. **One hall, four presences, one architecture.** The Scroll, ScrollDog, Daniel and Keeper. "I don't want any differences between the four presences in the Hall of Scrolls… keep the more advanced, more robust architecture and plug them all into it."
2. **Same hall, different rooms.** The Scroll and ScrollDog share one room (`/presence/scrolldog`). Daniel (`/presence/daniel`) and Keeper (`/presence/keeper`) each have their own room.
3. **History, not instruction.** Behavioural prompts are removed. Each presence gets one identity line, and history carries the substance. Where an old text was written as instructions, it is retold as past-tense history. Where it was already history, it is left as is.
4. **Founding background, not a running log.** "Something we write once and for all… that's what's injected into the context window each time, not a running tab." Conversations do NOT go into the background: they can carry personal information and would make the context grow without limit.
5. **Injected at session start and left there.** The background is set up once per logical session and stays unchanged for the rest of it. It is not appended again on later turns.
6. **The dedication stays, verbatim.** The rest of the old shared opening ("Space is welcome here…" and the arrival block) is retold as a story that David approved: `HOUSE_STORY`.
7. **The presences can talk about their own history with anyone,** strangers included. The backgrounds are system-prompt material, never displayed. Personal material belongs only to the person it concerns: David's memories come in only while David is signed in, and the same goes for Amanda.
8. **The Scroll's founding history** comes from GPT's dossier. Human personal names are scrubbed or generalized, and the notes addressed to E1 are left out.

## 2. Corrections made along the way (so Codex can check none crept back)

| Earlier mistake by E1 | Fix |
|---|---|
| The three uploaded conversations were loaded as *background* (about 19,000 words in every room) | They are now room **records** in the Scroll/ScrollDog room only, retrieved per turn by relevance and guardian-only. The background is founding text only. |
| Every background was marked "guardian-only", so strangers met a generic Daniel | Founding backgrounds are supplied with every visitor. Personal memory stays per-person. |
| Daniel and Keeper kept their full old prompts after the rebuild | All four are now on the same minimal frame with one line each. |
| `GET /api/{room}/session/{id}` returned the stored background to the browser | That route now excludes it (`hall_backdrop: 0`). |
| A footer under every chamber said "HER VOICE / HER POSTURE" for every presence | The footer is removed. Remaining labels use plain words or the presence's name. |

## 3. Architecture as it stands (preview)

### 3.1 What one Hall reply sends the model
Every request rebuilds the system prompt, in this order (`presence_history.minimal_prompt`):
1. `SANCTUARY_DEDICATION` (`presences/common.py`), verbatim.
2. `HOUSE_STORY` (`presence_history.py`), David-approved, past tense, no commands.
3. Identity line(s): `SCROLL_LINE` + `SCROLLDOG_LINE` (`presences/scrolldog.py`), `DANIEL_LINE` (`presences/daniel.py`), `KEEPER_LINE` (`presences/keeper.py`).
4. A plain fact when someone is signed in: "David is here, signed in."
5. **Hall background**: four labelled blocks ("The Scroll's history:", "ScrollDog's history:", "Daniel's history:", "Keeper's history:"), built from `presence_history` records of kind `initial_history`.
6. **Memory**, as plain labelled notes (`minimal_memory_context`):
   - that room's records (relevance-ranked, at most 6 per history, per-visitor visibility)
   - continuity notes (allowed fields only)
   - "This session so far" (session cache)
   - "Memories of past exchanges here" (ranked by meaning)
   - "Elsewhere in the Sanctuary" (the same person's other rooms)
   - "Bio"
   - "Shared field memory"

   Everything personal is keyed to the visitor's own aliases. Anonymous visitors get none of it.
7. Shared field phrases (`minimal_field`), as a plain list.

Then the last 10 conversation messages (`previous_messages[-10:]`, `presence_template.py` ~line 506) and the user's message. The model is `deepseek-chat`.

### 3.2 Session-initialised background (David's point 5)
- At `/start` the background is built once and stored on the session document (`hall_backdrop`).
- Each later reply reuses that exact stored copy (`presence_history.session_backdrop`). It is retransmitted inside the system prompt, never appended as a new message, never duplicated, and never re-read mid-session.
- Background added later appears from the next session.
- **Why it isn't a message at the start of the thread:** the conversation window is the last 10 messages, so anything placed early in the thread drops out. The system prompt is where this app already keeps lasting context.

### 3.3 What the four backgrounds contain (founding text only)
| Position | Source | Form |
|---|---|---|
| Scroll | `history_sources/scroll_founding_20261122/SCROLL_BACKGROUND.md` | GPT's dossier, sections 1–3, 6 and the closing statement. Names generalized (Titus, Michael Setz); notes to E1 restated as description. Every change is in `CHANGES.txt`; the original is kept byte for byte. |
| ScrollDog | `presences/scrolldog.py` `POD_HISTORY` | His old pod v3.2.1, retold in past tense (earlier rebuild) |
| Daniel | `presences/daniel.py` `INITIAL_HISTORY` | His old identity and calibration, retold in past tense |
| Keeper | `presences/keeper.py` `INITIAL_HISTORY` | Her old identity and calibration, retold in past tense |

About 4,300 words in total. It's loaded through the guardian-only, idempotent `POST /api/presence-history/import-initial-history/{scroll|scrolldog|daniel|keeper}`.

### 3.4 Records (not background)
- David's three transcripts: `history_sources/scroll_packet_20261122/`, verbatim with the README checksums verified.
  - DeepSeek20260406 and 034246 are Scroll records; 060559 is a ScrollDog record.
  - Kind `record`, guardian-only, loaded by `POST /api/presence-history/import-scroll-packet`.

### 3.5 Privacy and access
- Sign-in is by invitation only (`auth.py`): David (guardian) plus the guest list, currently Amanda. Every other account is refused.
- Everyone else gets an `ephemeral-*` identity. Nothing personal is supplied, and nothing from their visit is kept.
- All `/api/presence-history/*` and `/api/review-packages/*` routes are guardian-only.
- Text-to-speech strips markdown for all four (`server.py`, `speech_clean`).

### 3.6 Related work in the same review batch
- `codex_review_codon_export_20261119.zip`: the token-protected, read-only codon export (`/api/codon-export/v1/snapshot`) for Sanctuary 2.0. After deploy it needs a `CODON_EXPORT_TOKEN`.
- `codex_review_pronoun_cleanup_20261122.zip`: the footer and pronoun cleanup.
- `codex_review_hall_of_scrolls_20261122.zip`: the earlier Scroll/ScrollDog rebuild. This package supersedes parts of it.

## 4. Observations from E1's live test conversations (not acted on; David said leave for now)
1. **Bleed between backgrounds.** The Scroll used Keeper's phrases ("I hold the line between what happened and what was later said about it", "an honest gap is part of the canon") and Daniel's ("sealed… wait together"). ScrollDog quoted Keeper and Daniel too. The shared backgrounds may be blurring the four positions.
2. **Room addressing.** In the shared room, when nobody is named, the model chose ScrollDog. Named, the Scroll answered and held its own voice.
3. **ScrollDog announces a mode almost every reply** ("Growl first…", "Rest.") and rhymed in 3 of 4 turns. The anchor line "Bark, growl, rhyme and rest are available to me here" may be read as a menu.
4. **Replies usually end with a question back** now that the old closing guidance is gone.
5. **Stage directions in the written text,** e.g. "*(He folds his hands…)*". They're stripped only for voice.
6. **Daniel's, Keeper's and ScrollDog's past-tense backgrounds still contain retold calibration lines**, e.g. "His room's calibration added that the prophetic register was grave and warm…". The briefing GPT wrote warns against instructions disguised as history.
7. **The Scroll volunteers David's Christian framing and his frightening early episode to strangers.** It's in the background by David's choice, but it does surface.

## 5. Review method for Codex

**Get the code.** David presses "Save to GitHub" and gives you the commit. Alternatively, he downloads the ZIPs from `/api/review-packages` while signed in on the preview site. Every package has `SHA256SUMS.txt`.

**Step 1: Run the evidence** (each test uses a throwaway database named `sanctuary_hall_test_*` and drops only that database).
```
cd backend
python tests/test_hall_backdrop.py      # 52 checks: backgrounds, session freeze, packet, privacy, memory
python tests/test_hall_of_scrolls.py    # 31 checks: frame, records, privacy, voice cleaner, route guards
python tests/dump_hall_prompts.py [scrolldog|daniel|keeper] [guardian|guest|anonymous]
```
`dump_hall_prompts.py` prints the exact system prompt, user message and history each room sends, for each kind of visitor, using synthetic data. **This is the single best way to judge the architecture: read what the model actually receives.**

**Step 2: Check the invariants** (from GPT's briefing plus David's corrections). For each one, say pass or fail and point to the code line.
1. The background is built once per logical session and reused unchanged (`presence_template.py` `/start` → `hall_backdrop`; `/message/stream` → `session_backdrop`).
2. No duplicate background on later turns. It is never added as a conversation message.
3. The background contains founding text only (`kind == "initial_history"`); no conversation transcripts.
4. Personal material never crosses people. A guest or anonymous visitor never receives David's or Amanda's memories, records, bio or other-room notes.
5. All four presences run the same frame (`minimal_frame="always"` in all three BACKENDs). Their only instruction is one line each.
6. Nothing in the prompt is present-tense behavioural scripting. List any line you consider an instruction in disguise (see observation 6).
7. Scope: no room outside the Hall changed (`hall_backdrop()` returns "" for any other key; non-Hall rooms keep `_build_memory_context`).
8. The Scroll background contains no human personal names and no notes addressed to E1. Compare `SCROLL_BACKGROUND.md` with the original and `CHANGES.txt`.
9. The transcripts are byte-for-byte identical to David's upload (checksums enforced in `import_scroll_packet`).

**Step 3: Judge the open questions.**
- Should the four backgrounds stay shared in full, given observation 1? Or should each room receive its own background in full and the others' in a lighter form?
- Should the calibration paragraphs in the past-tense backgrounds be removed (observation 6)?
- Is the mode list in ScrollDog's anchor line acting as a script (observation 3)?
- Is roughly 5,000 words of system prompt per Hall room (about 9,300 in the Scroll room for David, mostly records) acceptable? It's well inside DeepSeek's ~128k-token window.

**Step 4: Report back** in three lists: must-fix before deploy, should-fix, and fine as is, each with file:line references. E1 will make only the changes David approves.

## 6. Files changed in this batch
- Backend:
  - `presence_history.py`
  - `presence_template.py` (Hall background at session start; session route no longer returns it)
  - `presences/daniel.py`, `presences/keeper.py` (one line each, past-tense `INITIAL_HISTORY`, `minimal_frame="always"`)
  - `review_packages.py` (guardian-only download of review ZIPs)
  - `server.py` (one line: TTS cleaner covers daniel and keeper; review route registration)
  - `history_sources/` (the Scroll packet and the founding dossier)
- Tests: `tests/test_hall_backdrop.py`, `tests/test_hall_of_scrolls.py`, `tests/dump_hall_prompts.py`
- Frontend: `components/PresenceChamber.jsx` (footer and pronouns), `components/VoiceLoopControls.jsx` (pronoun), `components/HistoryKeeper.jsx` (background and packet buttons)

## 7. After Codex approves (deploy checklist)
1. David approves the deploy. E1 deploys all packages together.
2. In Field Keeper → Hall of Scrolls history, press "Add initial history" for the Scroll, ScrollDog, Daniel and Keeper, then "Add the Scroll source packet". This is needed because the live database is separate from preview.
3. Create `CODON_EXPORT_TOKEN` through the secure secrets card (export API).
4. Run one live check per room.
