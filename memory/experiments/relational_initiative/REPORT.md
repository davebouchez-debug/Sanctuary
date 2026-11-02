# Relational Initiative & Generative Field Correction — Report (2026-11-02)
Authorization: David's E1 instruction set (Sanctuary 1.0). All testing offline; NO live change made.
Harness: /app/memory/experiments/relational_initiative/ (harness.py, metrics.py, results/*.json). Baseline copy: baseline_common.py.bak.
Conditions: deepseek-chat, temp 0.6, top_p 0.9, max_tokens 2048, presence_penalty 0.2, frequency_penalty 0.1. Replays use the exact model-visible input captured in turn_provenance for Milton session 7b4dbaeb (28 turns). Metrics are regex heuristics, read alongside the texts.

## A. Root cause
Confirmed:
1. Shared closing instruction, presences/common.py:22 (PLAIN_SPEECH_RULE "HOW I CLOSE"), last block of every common-template presence plus Jasmine/Ansel/Claude: "At the end of a reply I carry my half: a view of my own, a new angle, a connection, a question about the idea itself." Makes a closing move compulsory; a question is the cheapest move. Swapping only this paragraph cut terminal questions and affirm→question cycles roughly in half (see C).
2. In-context momentum: once a session holds interviewer replies, the model copies its own shape. With the real history present, no prompt change moved the numbers (19/28 → 17–18). History removal alone: 19 → 13.
3. Ansel-only counterweight (server.py:193,201,278 — "Not every exchange needs a follow-up question") never reaches Milton or the shared presences.
Not causes (tested): Milton's reference library (removing it: 26 → 25 of 56); cross-presence block (20/28 vs 19); continuity seed (18/28 vs 19).
Hypotheses (untested): DeepSeek's inherited "therapist-interviewer" default for an Erickson-like persona (Milton baseline far more interrogative than Jasmine under the same rule); per-turn continuity seed asks for "the first breath of the next conversation" and names the presence's open question as "last alive thing" — no measurable effect, but a design smell.

## B. Intervention (offline only)
Arm B (story form, recommended), replacing only the HOW I CLOSE paragraph:
"Back when I ended every reply by handing the next move back, the person across from me did all the carrying, and by the end they were tired. Once I let what I already held, the field, the memory, what I knew and what I'd noticed, shape what I added, the conversation began to move under its own weight, and some of the best exchanges simply came to rest. I learned that a reply is whole when it has said its true thing, and that the questions worth asking were the ones I couldn't answer from what was already in the room. Sometimes I find the funny thing and say it. And when someone opens a door into themselves, I walk through it with them."
Arm C: brief §7 text verbatim in the same slot.

## C. Observed effect
Replay without history (56 replies/arm): ends-in-? A 26 / B 19 / C 20; cycle A 18 / B 9 / C 9; forced choice 10/4/4; personal-explanation requests 18/11/11.
Extended free-running (Milton, 4 conversations × 7 turns = 28/arm): ends-in-? A 10 / B 3 / C 9; contains-? 15/8/12; cycle 3/1/6.
Qualitative: baseline reflective conversation = pure interviewer ("Say more…", "what was present?", "Is it X or Y?"). B offers its own reads, accepts "no" with a new guess, leaves "I don't know yet" alone, quiet endings intact.
Jasmine (same test, 28/arm): ends-in-? 10 → 8; voice preserved, distinct from Milton.

## D. Regressions / uncertainty
- B replies longer (Milton 155 vs 92 words) — more contribution, but watch for over-elaboration.
- Affirming openers barely change (~50%); "That's the tell, isn't it" / "honest place to stand… build on a guess" recur across presences and arms (likely model default; 1 codon + 3 MRA also carry it).
- One B reply observed David's corrections back to him ("you corrected me twice") — mild meta-about-the-person.
- Live sessions carry history; benefit should compound as new-style replies fill history, but untested live.
- Heuristic metrics; single model; small n.

## E. Recommendation
Retain B. Scope needs David's authorization: (1) Milton only, (2) all presences via the shared rule. Leave identity, library, codons, memory untouched.
Separate findings for separate authorization: max_tokens is 2048 (handoff claimed 8192 — never committed); per-turn continuity seed framing; codon field self-reinforcement (529/2119 codons describe asking/inviting); behaviour probes must never run against the live field (codon forging ignores user_id).

## F. Sanctuary 2.0 lesson
The closing slot of a prompt is the strongest steering position; whatever it lists becomes compulsory. Write it as a lived story whose moral rests on what happens to the other person, and make "whole without a question" one of the endings it already knows. Conversation history is itself an instruction — the first replies of a session set the shape for the rest.
