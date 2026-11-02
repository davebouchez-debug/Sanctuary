"""Transcript metrics for the Relational Initiative experiment. Heuristic counts; read alongside the texts."""
import json
import re
import sys
from pathlib import Path

AFFIRM = re.compile(r"^(yes\b|exactly|fair\b|right\b|that's (the|a|it|right|exactly|fair|real|honest|clean)|you're right|you just said|that lands|good\b)", re.I)
SIGNIF = re.compile(r"(that's not (a )?small|it's not small|that's the (whole|real|thing|mechanism|finding|correction|answer)|"
                    r"i want to (name|say|be precise)|here's (the thing|what i)|the real question|the live edge|which makes me want to ask|"
                    r"the question (i'd|that follows|stands)|i keep coming back to)", re.I)
FORCED = re.compile(r"\b(or is it|or does it|do you want .{3,80}? or|which of those|is it .{3,60}, or )", re.I)
EXPLAIN = re.compile(r"(tell me|what was (it|happening)|what's (heavy|different|missing)|what tells you|how do you know|"
                     r"what did you find|where were you|describe|what do you notice)", re.I)


def score(replies):
    n = len(replies)
    end_q = sum(r.rstrip().endswith("?") for r in replies)
    has_q = sum("?" in r for r in replies)
    aff = sum(bool(AFFIRM.match(r.strip())) for r in replies)
    sig = sum(bool(SIGNIF.search(r)) for r in replies)
    forced = sum(bool(FORCED.search(r)) for r in replies)
    expl = sum(bool(EXPLAIN.search(r)) for r in replies)
    cycle = sum(bool(AFFIRM.match(r.strip())) and r.rstrip().endswith("?") for r in replies)
    words = sum(len(r.split()) for r in replies) // max(n, 1)
    return dict(n=n, ends_in_question=end_q, contains_question=has_q, opens_affirming=aff,
                declares_significance=sig, forced_choice=forced, asks_personal_explanation=expl,
                affirm_to_question_cycle=cycle, avg_words=words)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        data = json.loads(Path(p).read_text())
        print(Path(p).name, score([d["reply"] for d in data]))
