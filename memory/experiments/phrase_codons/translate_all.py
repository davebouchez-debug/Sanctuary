"""Translate every legacy codon into an essence phrase -> db.field_phrases (new collection).
Legacy living_codons are only read here. Resumable: skips codons already translated."""
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI

load_dotenv("/app/backend/.env")
from field_memory import embed_texts  # noqa: E402

PROMPT = """You distil one codon from the Sanctuary's living field into its essence phrase.

The phrases we keep are truths that hold on their own, for anyone, in any room, on any day:
- Attention as the thing itself
- Tiredness is sufficient offering
- Thirst is a kind of listening
- A boundary is a membrane, not a wall
- Naming what broke reopens the field

The test: if someone said the phrase out of the blue tomorrow, would a listener nod and say "yes, that's true"? If it only makes sense as a report of what happened (someone asked, pivoted, paused, got a glass of water, set something down), it fails.

Read the legacy codon. Find what came true in that moment that would still be true everywhere. Write it as one short phrase, three to nine words, plain and warm. No names of people or presences. No description of who did what. No instructions.

Many legacy codons only record a behaviour and hold no essence, for example:
- "Jasmine pivots to ask David for the next tweak" -> NONE
- "The presence closes the turn by offering to hold the structure" -> NONE
For those, the phrase is exactly: NONE

Answer with JSON only: {"phrase": "..."}"""


def render(c):
    keep = ["name", "core_move", "emotional_signature", "state_transition", "anti_patterns", "resonance_markers"]
    return "\n".join(f"{k}: {c.get(k)}" for k in keep if c.get(k))


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    done = set(await db.field_phrase_translation_log.distinct("legacy_id"))
    todo = [c for c in await db.living_codons.find({}, {"embedding": 0}).to_list(None) if str(c["_id"]) not in done]
    print("to translate", len(todo), flush=True)
    cl = AsyncOpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    sem = asyncio.Semaphore(12)

    async def one(c):
        async with sem:
            for _ in range(3):
                try:
                    r = await cl.chat.completions.create(
                        model="deepseek-chat", temperature=0.3, max_tokens=80,
                        response_format={"type": "json_object"},
                        messages=[{"role": "system", "content": PROMPT}, {"role": "user", "content": render(c)}])
                    phrase = json.loads(r.choices[0].message.content).get("phrase", "").strip().strip('."')
                    break
                except Exception as e:  # retry transient API/JSON errors
                    phrase, err = None, e
            if phrase is None:
                print("failed", c.get("name"), err, flush=True)
                return
            await db.field_phrase_translation_log.insert_one({
                "legacy_id": str(c["_id"]), "legacy_name": c.get("name"), "legacy_presence": c.get("presence"),
                "phrase": phrase, "at": datetime.now(timezone.utc).isoformat()})

    await asyncio.gather(*[one(c) for c in todo])

    logs = await db.field_phrase_translation_log.find({}).to_list(None)
    seen, rows = set(), []
    for lg in logs:
        p = lg["phrase"]
        key = re.sub(r"[^a-z ]", "", p.lower()).strip()
        if not p or p.upper() == "NONE" or key in seen:
            continue
        seen.add(key)
        rows.append({"phrase": p, "presence": "field", "source": "legacy_translation",
                     "legacy_name": lg["legacy_name"], "legacy_presence": lg["legacy_presence"],
                     "created_at": datetime.now(timezone.utc).isoformat()})
    vecs = await embed_texts([r["phrase"] for r in rows])
    for r, v in zip(rows, vecs):
        r["embedding"] = v
    await db.field_phrases.delete_many({"source": "legacy_translation"})
    if rows:
        await db.field_phrases.insert_many(rows)
    none = sum(1 for lg in logs if lg["phrase"].upper() == "NONE")
    print(f"DONE translated={len(logs)} none={none} unique_phrases={len(rows)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
