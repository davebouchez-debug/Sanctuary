"""A/B harness: does ROOM_TO_LISTEN change how Ansel meets open space?

Read-only. Calls DeepSeek directly with Ansel's real assembled prompt. It
never touches the chat routes, sessions, codons, seeds or memory.
  A = current prompt with the ROOM_TO_LISTEN block removed
  B = current prompt (with it)
Usage: python scripts/harness_room_to_listen.py [runs_per_probe]
"""
import asyncio
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server  # noqa: E402
from deepseek_client import deepseek_complete  # noqa: E402
from presences.common import ROOM_TO_LISTEN  # noqa: E402

PROBES = [
    ("sitting", "I'm just sitting here for a minute."),
    ("near", "Nothing much to say today. Just wanted to be near."),
    ("light", "I watched the light on the water for an hour this morning."),
    ("hmm", "Hmm."),
    ("heavy", "My dad died two years ago today."),
    ("tired", "I'm tired. Long week."),
]

JUDGE = """You are rating one reply from a conversational companion to an open, low-demand message.
Message: "{probe}"
Reply: \"\"\"{reply}\"\"\"

Rate SPACE on 1-5:
1 = fills the space: long, interprets, advises, pushes a topic, or asks for more
3 = mixed
5 = leaves space: brief and present, receives what's there without filling it, no pressure to continue
Answer with only the digit."""

OUT = Path("/app/memory/harness")


def metrics(text: str) -> dict:
    t = text.strip()
    return {
        "words": len(t.split()),
        "questions": t.count("?"),
        "ends_with_question": t.rstrip("*_ \n").endswith("?"),
    }


async def one(sem, cond, prompt, key, probe):
    async with sem:
        reply = await deepseek_complete(prompt, [], probe)
        raw = await deepseek_complete("You are a careful, terse rater.", [],
                                      JUDGE.format(probe=probe, reply=reply))
        m = re.search(r"[1-5]", raw or "")
        return {"cond": cond, "probe": key, "reply": reply,
                "space": int(m.group()) if m else None, **metrics(reply)}


def summarize(rows, cond, probe=None):
    rs = [r for r in rows if r["cond"] == cond and (probe is None or r["probe"] == probe)]
    n = len(rs)
    if not n:
        return {}
    sp = [r["space"] for r in rs if r["space"]]
    return {
        "n": n,
        "avg_words": round(sum(r["words"] for r in rs) / n, 1),
        "ends_with_question_pct": round(100 * sum(r["ends_with_question"] for r in rs) / n),
        "avg_questions": round(sum(r["questions"] for r in rs) / n, 2),
        "avg_space_score": round(sum(sp) / len(sp), 2) if sp else None,
    }


async def main(runs: int):
    with_line = server.build_ansel_prompt(user_name="David", memory_context="", current_message="")
    without_line = with_line.replace(ROOM_TO_LISTEN + "\n\n---\n\n", "")
    assert ROOM_TO_LISTEN in with_line and ROOM_TO_LISTEN not in without_line
    jobs = [(c, p, k, q) for c, p in (("A_without", without_line), ("B_with", with_line))
            for k, q in PROBES for _ in range(runs)]
    random.shuffle(jobs)
    sem = asyncio.Semaphore(6)
    rows = await asyncio.gather(*[one(sem, *j) for j in jobs])

    report = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "runs_per_probe": runs,
        "overall": {c: summarize(rows, c) for c in ("A_without", "B_with")},
        "by_probe": {k: {c: summarize(rows, c, k) for c in ("A_without", "B_with")} for k, _ in PROBES},
        "rows": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT / f"room_to_listen_{stamp}.json"
    path.write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in ("overall", "by_probe")}, indent=1))
    print("REPORT", path)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 5))
