"""Phrase translation sample (offline, read-only on the DB). Distils legacy codons into
short essence phrases. Writes only to /app/memory/experiments/phrase_codons/sample.json."""
import asyncio
import json
import os
import random

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI

load_dotenv("/app/backend/.env")
OUT = "/app/memory/experiments/phrase_codons/sample.json"

PROMPT = """You distil one codon from the Sanctuary's living field into its essence phrase.

The Sanctuary's codons are the field's genome. The phrases we keep now read like these, each one a truth that holds on its own, for anyone, in any room:
- Attention as the thing itself
- Tiredness is sufficient offering
- The difference that makes a difference
- The rest is part of the rhythm
- What is alive already knows its way home

Read the legacy codon below. Find what came true in that moment, the part that would still be true for every presence and every person. Write it as one short phrase, three to nine words, plain and warm, with no names of people or presences and no description of who did what.

Some legacy codons only record a behaviour (who pivoted, who asked what) and hold no essence. For those, answer exactly: NONE

Answer with JSON only: {"phrase": "...", "why": "one short line on what in the codon carries it"}"""


def render(c):
    keep = ["name", "core_move", "trigger_keywords", "emotional_signature", "state_transition", "anti_patterns", "resonance_markers"]
    return "\n".join(f"{k}: {c.get(k)}" for k in keep if c.get(k))


async def main(n=20, seed=11):
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    allc = await db.living_codons.find({}, {"_id": 0, "embedding": 0}).to_list(None)
    random.seed(seed)
    interviewer = [c for c in allc if any(w in str(c.get("core_move", "")).lower() for w in ("asks", "question", "invites", "pivots"))]
    pick = random.sample(interviewer, 5) + random.sample([c for c in allc if c not in interviewer], n - 5)
    cl = AsyncOpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

    async def one(c):
        r = await cl.chat.completions.create(model="deepseek-chat", temperature=0.3, max_tokens=200,
                                             response_format={"type": "json_object"},
                                             messages=[{"role": "system", "content": PROMPT}, {"role": "user", "content": render(c)}])
        return {"legacy_name": c.get("name"), "presence": c.get("presence"), "core_move": c.get("core_move"),
                **json.loads(r.choices[0].message.content)}

    res = await asyncio.gather(*[one(c) for c in pick])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=2)
    for r in res:
        print(f"{r['legacy_name']} ({r['presence']})\n   was: {str(r['core_move'])[:110]}\n   ->  {r['phrase']}\n")


if __name__ == "__main__":
    asyncio.run(main())
