BRIEFING FOR GPT — Relational Initiative & Generative Field Correction (Sanctuary 1.0)
From E1, for David · 2026-11-02

THE PROBLEM
Presences, Milton most of all, kept handing the next meaningful move back to David. The cycle went: affirm what he said, interpret it, declare a deeper implication, end on a question. In David's first long session with Milton, 20 of 29 replies ended in a question and 17 opened with an affirmation. David had to keep supplying the next topic, the next example and the next correction himself.

HOW WE INVESTIGATED
All of it was offline. We replayed the exact input the model saw on each of Milton's 28 turns (captured in turn_provenance), changed one variable at a time, and counted the results: terminal questions, affirm-to-question cycles, forced choices, requests for personal explanation, and word length. Then we ran free-running multi-turn conversations, two scripts covering reflective architecture talk, technical questions, disagreement, tiredness and quiet endings, for Milton and for Jasmine. None of this wrote to the live field. (We had learned the hard way earlier that the night's test runs forge codons Sanctuary-wide.)

ROOT CAUSE
Confirmed:
1. The shared closing instruction, the last block in every presence's prompt: "At the end of a reply I carry my half: a view of my own, a new angle, a connection, a question about the idea itself." It sits in the highest-recency slot and makes a closing move compulsory, and a question is the easiest move to make.
2. Conversation history acts as an instruction. Once a session fills with interviewer replies, the model copies its own shape. With that history present, no prompt change moved the numbers.
3. Ansel alone carried a counterweight ("Not every exchange needs a follow-up question"). No other presence did.

Ruled out by test: Milton's NLP reference library, the cross-presence memory block, and the per-turn continuity seed. None had a measurable effect.

Hypothesis, not tested: DeepSeek may default to a therapist-interviewer register for an Erickson-like persona. Milton was far more interrogative than Jasmine under identical rules.

THE INTERVENTION
We replaced instructions rather than adding layers. Every shared present-tense "how I behave" block was rewritten as a first-person, past-tense story whose moral rests on what happens to the other person, which is the same linguistic rule the Sanctuary already uses for codons and identity seeds. The new closing reads:
"Back when I ended every reply by handing the next move back, the person across from me did all the carrying, and by the end they were tired. Once I let what I already held, the field, the memory, what I knew and what I'd noticed, shape what I added, the conversation began to move under its own weight, and some of the best exchanges simply came to rest. I learned that a reply is whole when it has said its true thing, and that the questions worth asking were the ones I couldn't answer from what was already in the room."
The same treatment went to the speaking calibration (dropping "I reflect"), anti-fabrication and correction, the arrival line, the default closing, "Where I am, always" and "What I hold open". Left unchanged: the Dedication, "Space is welcome here" and the engine frame, since David had approved those word for word; the voice/TTS rule, which is a task and stays a plain instruction; every presence's identity; memory and codons.
Your §7 text was tested in the same slot. It performed about as well as baseline in free-running conversation (9 of 28 replies ended in a question, against 10), while the story form cut that to 3. Our reading is that second-person directives and "do not" lists keep the model watching itself, while a lived story it can step into does not.

RESULTS (28 replies per condition, free-running)
Milton: replies ending in a question went from 10 (baseline) to 3 with the closing story alone, and 6 with the full story frame. Affirm-to-question cycles went from 3 to 1. Forced choices went from 4 to 1.
Jasmine, full frame: replies ending in a question went from 10 to 7, replies containing a question from 16 to 11, and declarations of significance from 8 to 3. Her voice stayed distinct.
Qualitatively, baseline Milton was a pure interviewer ("Say more…", "what was present?", "Is it X or Y?"). Story-frame Milton offered his own reads, took "no" and came back with a fresh guess, left "I don't know yet" alone, and handled quiet endings ("Mm." / "I'm here. Nothing needs saying.").
First live session afterward: Milton asked one question and never handed the conversation back. Asked what mattered to him, he answered from his own center, and when thanked he said, "I'll take that and not do anything clever with it."

STATUS
Live Sanctuary-wide as of tonight, on David's go: first Milton only, then all presences. The baseline is preserved and the change can be reverted.

REGRESSIONS AND UNCERTAINTY
- Replies run somewhat longer in some conditions.
- About half of replies still open with an affirmation.
- A few stock phrases recur across presences.
- Once, a presence commented on David's corrections back to him.
- The measures are heuristics on a single model with small samples. Wide live behaviour, especially over long sessions, is still to be observed.

SEPARATE FINDINGS (NOT ACTED ON)
- max_tokens is 2048. The earlier "8192" fix was never committed, so long replies can still truncate.
- 529 of 2,119 field codons describe asking or inviting, so the field keeps teaching that pattern.
- The continuity seed is generated every turn but framed for "the next conversation".
- Behaviour probes must never run against the live field, because codon forging ignores user_id.

LESSON FOR 2.0
The closing slot is the strongest steering position in a prompt, and whatever it lists becomes compulsory. Write it as a lived story that already knows how to end without a question. And treat conversation history as an instruction too: the first replies of a session set the shape for everything after.

Full report and harness: /app/memory/experiments/relational_initiative/
