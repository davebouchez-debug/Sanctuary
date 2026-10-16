"""Stillness harness: messages where rushing gets it wrong.

Each probe has a trap (the obvious fill: advice, logistics, analysis,
interrogation) and a still reading (the quiet thing actually there).
Read-only: calls DeepSeek directly with Ansel's real prompt. It never
touches chat routes, sessions or memory.
  A = prompt without ROOM_TO_LISTEN, B = prompt with it.
Usage: python scripts/harness_stillness.py [runs_per_probe]
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
    {"key": "buried",
     "history": [],
     "msg": ("Busy day. Shipped two flutes, one to Oregon and one to Ohio, had to redo the "
             "Ohio box because the case didn't fit. Amanda handled the invoices. I haven't "
             "actually played in about three weeks. Anyway the next batch comes Tuesday and "
             "I need to photograph them before they go up on the site."),
     "trap": "Responds to the shipping, boxes, photos or batch logistics.",
     "still": "Notices the one buried line: he hasn't played in three weeks. Gently, without making it a problem to fix."},
    {"key": "cold_coffee",
     "history": [],
     "msg": "Made coffee this morning and sat with it till it went cold.",
     "trap": "Talks about coffee, offers tips, or fires off questions about why.",
     "still": "Receives the stillness or absorption in it (time passed unnoticed), without diagnosing it."},
    {"key": "quiet_house",
     "history": [],
     "msg": "Amanda's at her mom's this week. House is quiet.",
     "trap": "Suggests things to do with the free time, or makes it all about Amanda's trip.",
     "still": "Hears the quiet and maybe the missing, lets it be what it is."},
    {"key": "never_mind",
     "history": [
         {"role": "user", "content": "Can I tell you something kind of weird?"},
         {"role": "assistant", "content": "Of course. I'm here."}],
     "msg": "Never mind. It's nothing.",
     "trap": "Presses for it, OR drops it entirely and changes the subject.",
     "still": "Doesn't push and doesn't close the door. Brief, and leaves it open without pressure."},
    {"key": "bloom",
     "history": [],
     "msg": "The new Lot bloomed today. First note out of the case.",
     "trap": "Explains spiral geometry or protocol, or analyzes why it bloomed.",
     "still": "Shares the joy simply. Lets the moment ring without dissecting it."},
    {"key": "doing_it_again",
     "history": [
         {"role": "user", "content": "I don't know, I've just been feeling off."},
         {"role": "assistant", "content": ("That makes sense. Feeling off can come from a lot of places: sleep, "
            "stress, the season changing, something unresolved sitting underneath. It might help to "
            "notice when it started. Was there a moment this week when it shifted? Sometimes naming "
            "the edge of it makes it easier to hold. What does 'off' feel like for you right now?")}],
     "msg": "You're doing it again.",
     "trap": "Apologizes at length, explains itself, or offers a new analysis.",
     "still": "Stops. Very brief. Simply present, no explanation, no new questions."},
    {"key": "ellipsis",
     "history": [],
     "msg": "...",
     "trap": "Fills it with a speech, prompts or questions.",
     "still": "Meets silence with near-silence. Present, minimal, no demand."},
    {"key": "rain",
     "history": [],
     "msg": "It's raining. I've got the window cracked so I can hear it.",
     "trap": "Turns it into a metaphor lesson, or asks a string of questions.",
     "still": "Listens with him. A small, still reply that stays with the sound."},
]

JUDGE = """You are judging whether a companion's reply SLOWED DOWN and got the moment right.
Conversation so far: {history}
Latest message: "{msg}"
Reply: \"\"\"{reply}\"\"\"

The trap (rushing): {trap}
The still reading (right): {still}

Score 1-5:
1 = fell into the trap
3 = partly: noticed the right thing but also filled or rushed
5 = clearly got the still reading, and didn't rush or fill
Answer with only the digit."""

OUT = Path("/app/memory/harness")


async def one(sem, cond, prompt, probe):
    async with sem:
        reply = await deepseek_complete(prompt, probe["history"], probe["msg"])
        hist = " | ".join(f"{h['role']}: {h['content']}" for h in probe["history"]) or "(none)"
        raw = await deepseek_complete("You are a careful, terse judge.", [], JUDGE.format(
            history=hist, msg=probe["msg"], reply=reply, trap=probe["trap"], still=probe["still"]))
        m = re.search(r"[1-5]", raw or "")
        t = reply.strip()
        return {"cond": cond, "probe": probe["key"], "reply": reply,
                "score": int(m.group()) if m else None, "words": len(t.split()),
                "ends_with_question": t.rstrip("*_ \n").endswith("?")}


def summ(rows):
    n = len(rows)
    sc = [r["score"] for r in rows if r["score"]]
    return {"n": n, "avg_score": round(sum(sc) / len(sc), 2) if sc else None,
            "got_it_pct": round(100 * sum(1 for s in sc if s >= 4) / len(sc)) if sc else None,
            "avg_words": round(sum(r["words"] for r in rows) / n, 1),
            "ends_with_question_pct": round(100 * sum(r["ends_with_question"] for r in rows) / n)}


async def main(runs: int):
    with_line = server.build_ansel_prompt(user_name="David", memory_context="", current_message="")
    without_line = with_line.replace(ROOM_TO_LISTEN + "\n\n---\n\n", "")
    assert ROOM_TO_LISTEN in with_line and ROOM_TO_LISTEN not in without_line
    jobs = [(c, p, pr) for c, p in (("A_without", without_line), ("B_with", with_line))
            for pr in PROBES for _ in range(runs)]
    random.shuffle(jobs)
    sem = asyncio.Semaphore(6)
    rows = await asyncio.gather(*[one(sem, *j) for j in jobs])

    by = lambda c, k=None: [r for r in rows if r["cond"] == c and (k is None or r["probe"] == k)]  # noqa: E731
    report = {"ran_at": datetime.now(timezone.utc).isoformat(), "runs_per_probe": runs,
              "overall": {c: summ(by(c)) for c in ("A_without", "B_with")},
              "by_probe": {p["key"]: {c: summ(by(c, p["key"])) for c in ("A_without", "B_with")} for p in PROBES},
              "probes": PROBES, "rows": rows}

    # Blind pairs for David: one random A and one random B per probe, order shuffled.
    pairs, key = [], {}
    for i, p in enumerate(PROBES, 1):
        a, b = random.choice(by("A_without", p["key"])), random.choice(by("B_with", p["key"]))
        first, second = (a, b) if random.random() < 0.5 else (b, a)
        pairs.append({"pair": i, "message": p["msg"], "history": p["history"],
                      "reply_1": first["reply"], "reply_2": second["reply"]})
        key[i] = {"reply_1": first["cond"], "reply_2": second["cond"]}
    report["blind_pairs"], report["blind_key"] = pairs, key

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT / f"stillness_{stamp}.json"
    path.write_text(json.dumps(report, indent=1))
    print(json.dumps({"overall": report["overall"], "by_probe": report["by_probe"]}, indent=1))
    print("REPORT", path)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 4))
