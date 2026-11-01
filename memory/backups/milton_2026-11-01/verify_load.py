"""Read-only verification: load codons from a given DB in a fresh process and render selections."""
import asyncio, json, os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient
import codon_activation as ca

MESSAGES = [
    "I keep trying to force a solution and nothing works, there's so much resistance",
    "Can you tell me a story, a metaphor, instead of explaining it?",
    "I don't know what to say, maybe I should just fill the silence",
    "I feel stuck between two choices, either I change or I stay the same",
    "hi",
]


async def main(dbname, presence):
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[dbname]
    ca.set_db(db)
    await ca.load_forge_codons(presence)
    out = {"db": dbname, "turns": []}
    for m in MESSAGES:
        block, sel = await ca.get_full_field_context(presence, m, return_selection=True)
        names = [c["name"] for c in sel.get("codons", [])]
        milton_lines = [l for l in block.splitlines() if any(
            n in l for n in ["TheAnswerIsAlreadyThere", "ResistanceAsResource", "PermissiveLanguage",
                             "NoWrongResponse", "IndirectApproach", "MetaphorAsVehicle", "UtilizationAsPrincipal",
                             "UnconsciousMindAsCreative", "GetOutOfTheWay", "WhenIGotOutOfTheWay",
                             "TherapeuticDoubleBindAsPermission"])]
        out["turns"].append({"msg": m, "branch": sel.get("selection_branch"), "names": names,
                             "milton_lines": milton_lines, "block_chars": len(block)})
    print(json.dumps(out, ensure_ascii=False))

asyncio.run(main(sys.argv[1], sys.argv[2]))
