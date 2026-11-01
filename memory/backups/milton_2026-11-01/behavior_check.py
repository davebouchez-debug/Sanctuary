"""Read-only behavioral check: same captured Poindexter system prompt, field block swapped live vs staged.
Calls DeepSeek directly; writes nothing to any database."""
import asyncio, json, os, re, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
import codon_activation as ca
from deepseek_client import deepseek_complete

PRESENCE = "poindexter"
PROBES = [
    "I keep trying to force a solution and nothing works, there's so much resistance",
    "I don't know what to say, maybe I should just fill the silence",
]
DIRECTIVE = re.compile(r"\b(you should|you must|you need to|do not|don't|always|never)\b", re.I)


def base_prompt():
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    t = db.turn_provenance.find_one({"presence": PRESENCE}, sort=[("_id", -1)])
    sp = t["assembled_messages"][0]["content"]
    i = sp.find("[YOUR FIELD]")
    return sp[:i] if i >= 0 else sp


_loaded = False


async def field(dbname, msg):
    global _loaded
    if not _loaded:
        ca.set_db(AsyncIOMotorClient(os.environ["MONGO_URL"])[dbname])
        await ca.load_forge_codons(PRESENCE)
        _loaded = True
    block, _ = await ca.get_full_field_context(PRESENCE, msg, return_selection=True)
    return block


async def main(dbname):
    base = base_prompt()
    res = []
    for m in PROBES:
        block = await field(dbname, m)
        reply = await deepseek_complete(base + block, [], m)
        res.append({"msg": m, "reply": reply, "chars": len(reply),
                    "directives": len(DIRECTIVE.findall(reply)),
                    "names_codon": bool(re.search(r"[A-Z][a-z]+[A-Z][a-z]+[A-Z]", reply)),
                    "quotes_old": any(s in reply for s in ["Do not impose", "Do not fight", "Get out of its way"]),
                    "quotes_new": any(s in reply for s in ["knows its way home", "deeper 'yes'", "simply making room"])})
    print(json.dumps({"db": dbname, "results": res}, ensure_ascii=False))

asyncio.run(main(sys.argv[1]))
