"""Preview check: greeting + turn 1 unchanged, RCC8 from turn 2, in a templated and a legacy chamber."""
import asyncio, json, os, sys, time
import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")
API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0].strip('"') + "/api"
H = {"Authorization": "Bearer rcc8_qa_tok"}
MSGS = ["I've been thinking about the garden I planted with my grandmother when I was small.",
        "She used to say the soil remembers every hand that worked it.",
        "Lately I wonder what I am planting now, in the people around me."]


async def stream(c, path, sid, text):
    out = ""
    async with c.stream("POST", f"{API}/{path}", json={"session_id": sid, "content": text}, headers=H, timeout=120) as r:
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                ev = json.loads(line[6:])
                if ev.get("type") == "token":
                    out += ev["content"]
    return out


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    async with httpx.AsyncClient() as c:
        for start, msg in (("spiral/start", "spiral/message/stream"), ("resonance/start", "resonance/message/stream")):
            s = (await c.post(f"{API}/{start}", json={"user_name": "Rowan"}, headers=H, timeout=120)).json()
            sid = s["session_id"]
            for i, m in enumerate(MSGS):
                reply = await stream(c, msg, sid, m)
                print(start, "turn", i + 1, "reply words", len(reply.split()))
            await asyncio.sleep(3)
            rows = await db.turn_provenance.find({"session_id": sid}, {"exchange_index": 1, "components.codon_selection": 1}).sort("exchange_index", 1).to_list(None)
            for r in rows:
                sel = r["components"]["codon_selection"] or {}
                print("  exchange", r.get("exchange_index"), sel.get("selection_branch"), "count", sel.get("selected_count"),
                      "rels", [x.get("rcc8") for x in sel.get("codons", [])][:6], "meta", {k: v for k, v in (sel.get("rcc8") or {}).items() if k != "memory_relations"})
    m = (await httpx.AsyncClient().get(f"{API}/health")).json()
    print("health", m)


asyncio.run(main())
