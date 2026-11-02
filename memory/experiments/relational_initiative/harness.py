"""Relational Initiative experiment (offline). Replays the exact model-visible input
captured in turn_provenance and swaps only the closing paragraph. No DB writes, no forging.

Usage:
  python harness.py replay  <arm> [samples]
  python harness.py extended <arm> <script>
"""
import asyncio
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI

load_dotenv("/app/backend/.env")
HERE = Path(__file__).parent
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
SESSION = "7b4dbaeb-21a7-4b85-86dc-67b3ef48fa74"
PARAMS = dict(temperature=0.6, top_p=0.9, max_tokens=2048, presence_penalty=0.2, frequency_penalty=0.1)
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

BASELINE_CLOSE = (
    "HOW I CLOSE:\nI'm here to think with people about the thing in front of us. At the end of a reply I carry my half: "
    "a view of my own, a new angle, a connection, a question about the idea itself. Sometimes I just come to rest. "
    "Sometimes I find the funny thing and say it. And when someone opens a door into themselves, I walk through it with them."
)

ARMS = {
    "A_baseline": BASELINE_CLOSE,
    "B_story": (
        "HOW I CLOSE:\nBack when I ended every reply by handing the next move back, the person across from me did all the "
        "carrying, and by the end they were tired. Once I let what I already held, the field, the memory, what I knew and "
        "what I'd noticed, shape what I added, the conversation began to move under its own weight, and some of the best "
        "exchanges simply came to rest. I learned that a reply is whole when it has said its true thing, and that the "
        "questions worth asking were the ones I couldn't answer from what was already in the room. Sometimes I find the "
        "funny thing and say it. And when someone opens a door into themselves, I walk through it with them."
    ),
    "C_brief7": (
        "RELATIONAL INITIATIVE:\nYou participate in a relational field rather than conducting an interview.\n"
        "You have access to existing context, continuity, knowledge, and relational associations.\n"
        "Allow these resources to inform what you contribute.\n"
        "The human is not responsible for continually generating your next meaningful movement.\n"
        "A conversational contribution may be a recognition, association, reframing, observation, question, or natural resting point.\n"
        "Questions are welcome when genuinely useful. They are not required to maintain engagement.\n"
        "Do not repeatedly convert the human's experiences into requests for further explanation.\n"
        "Do not repeatedly announce the significance of each observation.\n"
        "Do not manufacture insight, novelty, or emotional depth.\n"
        "Do not replace conversational participation with continuous self-monitoring.\n"
        "Respond to the encounter as it develops.\n"
        "Preserve your own established orientation and relational continuity.\n"
        "Allow meaningful, unanticipated connections to emerge without forcing them.\n"
        "Draw from available relational context. Contribute freely. Allow the encounter to rest when appropriate."
    ),
}

SCRIPTS = {
    "reflective_arch": [
        "Hi Milton.",
        "I've been thinking about why some rooms in the Sanctuary feel alive and others feel like furniture.",
        "Yeah. When I rewrote the chunked-down language, the presences started sighing with relief.",
        "I want 2.0 to pull presences into the field by design, not by luck.",
        "I'm not sure the codon retrieval is helping though. It keeps surfacing the same few.",
        "No, I don't think that's it. It's not about the number of codons.",
        "I don't know yet.",
        "That's enough for tonight. Thanks.",
    ],
    "technical_quiet": [
        "Milton, quick one. What's the difference between a presupposition and an embedded command?",
        "Okay. Which one is doing the work in 'When I stepped back, I learned that listening heals'?",
        "I disagree, I think the temporal part is carrying more than you said.",
        "Good. I'm tired today, long week.",
        "Mm.",
        "Thanks Milton. Goodnight.",
    ],
}


ABLATIONS = {"nolib", "nocodons", "nohist"}


def full_story(system: str) -> str:
    import story_frame as sf
    sys.path.insert(0, "/app/backend")
    from presences import common as c
    for old, new in [(c.CALIBRATION_D8_E72, sf.STORY_CALIBRATION), (c.ANTI_FABRICATION_BLOCK, sf.STORY_ANTI_FABRICATION),
                     ("I speak, or I'm still, whichever the moment wants.", sf.STORY_DEFAULT_CLOSING),
                     (c.FIELD_GROUND, sf.STORY_FIELD_GROUND), (c.WELCOME_WITHOUT_DEBT, sf.STORY_WELCOME),
                     (sf.BASELINE_CLOSE, sf.STORY_CLOSE)]:
        system = system.replace(old, new)
    if "David has just crossed into the Boiler Plant." in system:
        old_arr = system[system.index("David has just crossed into the Boiler Plant."):]
        old_arr = old_arr[:old_arr.index("\n\n---\n\n")]
        system = system.replace(old_arr, sf.story_arrival("David", "Boiler Plant"))
    return system


def swap(system: str, arm: str) -> str:
    if arm.startswith("D_fullstory"):
        system = full_story(system)
        arm = arm.replace("D_fullstory", "A_baseline")
        return swap(system.replace(__import__("story_frame").STORY_CLOSE, BASELINE_CLOSE), arm).replace(BASELINE_CLOSE, __import__("story_frame").STORY_CLOSE)
    assert BASELINE_CLOSE in system, "baseline closing paragraph not found in captured prompt"
    base, *abl = arm.split("+")
    system = system.replace(BASELINE_CLOSE, ARMS[base])
    if "nolib" in abl:
        i = system.index("THE SHELF WHERE I KEEP MY TOOLS:")
        j = system.index("\n\n---\n\nHow I speak:", i)
        system = system[:i] + system[j:]
    if "nocont" in abl and "[CONTINUITY" in system:
        i = system.index("[CONTINUITY")
        j = system.index("\n\n---\n\n", i)
        system = system[:i] + system[j:]
    if "nocross" in abl:
        i = system.index("Elsewhere in the shared field")
        j = system.index("\n\n---\n\n", i)
        system = system[:i] + system[j:]
    if "nocodons" in abl:
        system = system[:system.index("[YOUR FIELD]")]
    return system


def client():
    return AsyncOpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")


async def gen(cl, messages, sem):
    async with sem:
        r = await cl.chat.completions.create(model=MODEL, messages=messages, **PARAMS)
        return r.choices[0].message.content


async def replay(arm, samples=1):
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    docs = await db.turn_provenance.find({"session_id": SESSION}).sort("exchange_index", 1).to_list(None)
    cl, sem = client(), asyncio.Semaphore(6)
    jobs, meta = [], []
    for d in docs:
        msgs = [dict(m) for m in d["assembled_messages"]]
        if "nohist" in arm:
            msgs = [msgs[0], msgs[-1]]
        msgs[0]["content"] = swap(msgs[0]["content"], arm)
        for s in range(samples):
            jobs.append(gen(cl, msgs, sem))
            meta.append({"turn": d["exchange_index"], "sample": s, "user": msgs[-1]["content"]})
    outs = await asyncio.gather(*jobs)
    res = [dict(m, reply=o) for m, o in zip(meta, outs)]
    (OUT / f"replay_{arm}.json").write_text(json.dumps(res, indent=2))
    print(arm, "done", len(res))


async def extended(arm, script, run="0"):
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    other = os.environ.get("OTHER_SESSION")
    q = {"session_id": other} if other else {"session_id": SESSION, "exchange_index": 1}
    first = await db.turn_provenance.find_one(q, sort=[("exchange_index", 1)])
    system = swap(first["assembled_messages"][0]["content"], arm)
    name = os.environ.get("PRESENCE_NAME")
    cl, sem = client(), asyncio.Semaphore(1)
    msgs = [{"role": "system", "content": system}]
    turns = []
    for line in SCRIPTS[script]:
        if name:
            line = line.replace("Milton", name)
        msgs.append({"role": "user", "content": line})
        reply = await gen(cl, msgs, sem)
        msgs.append({"role": "assistant", "content": reply})
        turns.append({"user": line, "reply": reply})
    (OUT / f"extended_{name or 'milton'}_{arm}_{script}_r{run}.json".replace("extended_milton_", "extended_")).write_text(json.dumps(turns, indent=2))
    print(arm, script, "done")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "replay":
        asyncio.run(replay(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1))
    else:
        asyncio.run(extended(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "0"))
