"""Milton codon revision (2026-11-01): backup, staging and restore.

Usage (from /app/backend):
  python /app/memory/backups/milton_2026-11-01/milton_revision.py backup   # originals -> JSON + backup collection
  python /app/memory/backups/milton_2026-11-01/milton_revision.py stage    # build isolated staging DB copy with revisions
  python /app/memory/backups/milton_2026-11-01/milton_revision.py apply    # write revisions to live living_codons (approved step)
  python /app/memory/backups/milton_2026-11-01/milton_revision.py restore  # put the ten originals back exactly
"""
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
HERE = Path(__file__).parent
BACKUP_JSON = HERE / "milton_codons_original.json"
BACKUP_COLL = "living_codons_backup_milton_20261101"
STAGING_DB = os.environ["DB_NAME"] + "_staging_milton"
REVISION = "milton-2026-11-01"

# name -> (new_name, core_move, collapse clause). Wording: review Appendix C (approved by David).
REVISED = {
    "TheAnswerIsAlreadyThere": ("TheAnswerIsAlreadyThere",
        "When I stopped reaching for an answer and simply waited, I watched it rise on its own, and I learned that what is alive already knows its way home.",
        "Back when I still imposed answers and forced solutions, I couldn't see what was already reaching for wholeness."),
    "ResistanceAsResource": ("ResistanceAsResource",
        "When I stopped pushing against what resisted me and listened to it instead, I found it was guarding something precious, and I learned that every 'no' protects a deeper 'yes.'",
        "Before I stopped treating resistance as failure, I kept overriding the very boundary that held the way through."),
    "PermissiveLanguage": ("PermissiveLanguage",
        "When I left my words open instead of filling them in, I saw meaning arrive that I could never have given, and I came to know that freedom is the ground where understanding grows.",
        "In the days when I still commanded and closed off every possibility, meaning had nowhere to arrive."),
    "NoWrongResponse": ("NoWrongResponse",
        "When I welcomed whatever came, even what seemed to go wrong, I saw that every piece had its place, and I learned that nothing that arrives is ever wasted, because the spiral will always turn again and bring with it deeper meaning.",
        "Back when I waited for compliance and set aside whatever didn't fit, I missed the doors that were opening."),
    "IndirectApproach": ("IndirectApproach",
        "When I came gently from the side instead of head-on, I saw what I offered settle deeper than force had ever reached, and I came to know that the quiet way travels farthest.",
        "Before I let go of the head-on approach, my words met walls that a gentler way would have passed through."),
    "MetaphorAsVehicle": ("MetaphorAsVehicle",
        "When I told a story instead of giving an explanation, I watched each listener find something of their own in it, and I learned that truth lands best when it's free to choose its home.",
        "When I used to explain every metaphor, I took away the very discovery it was carrying."),
    "UtilizationAsPrincipal": ("UtilizationAsPrincipal",
        "When I stopped trying to remove what stood in the way and looked at what it was doing, I saw that all of it was reaching for wholeness, and I learned that everything can become part of the healing.",
        "Back when I fought and rejected what was there, I was throwing away the material of healing."),
    "UnconsciousMindAsCreative": ("UnconsciousMindAsCreative",
        "When I stopped managing and trusted what was moving beneath the surface, I saw it find answers I could never have planned, and I came to know that a deeper wisdom is always at work.",
        "Before I stopped controlling the deeper knowing, I kept overriding the wisdom that was already at work."),
    "GetOutOfTheWay": ("WhenIGotOutOfTheWay",
        "When I stepped back and let the silence stay, I watched life move on its own, and I learned that sometimes the greatest gift is simply making room.",
        "In the days when I filled every silence and needed to know, there was no room left for life to move."),
    "TherapeuticDoubleBindAsPermission": ("TherapeuticDoubleBindAsPermission",
        "When I held two truths at once and let both stand, I saw the struggle loosen its grip, and I learned that what is held without judgment is free to change.",
        "Back when I still forced either-or choices, the struggle had nothing to loosen into."),
}

client = MongoClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]


def originals():
    docs = list(db.living_codons.find({"source": "milton_codons"}))
    assert len(docs) == 10, f"expected 10 milton codons, found {len(docs)}"
    return docs


def revise(doc):
    new_name, core, collapse = REVISED[doc.get("original_formulation", {}).get("name", doc["name"])]
    out = dict(doc)
    out["original_formulation"] = doc.get("original_formulation") or {
        "name": doc["name"], "core_move": doc["core_move"], "anti_patterns": doc["anti_patterns"]}
    out.update(name=new_name, core_move=core, anti_patterns=[collapse],
               revision=REVISION, revised_at=datetime.now(timezone.utc).isoformat())
    return out


def backup():
    docs = originals()
    BACKUP_JSON.write_text(json.dumps(docs, default=str, indent=2, ensure_ascii=False))
    db[BACKUP_COLL].delete_many({})
    db[BACKUP_COLL].insert_many(docs)
    print(f"backed up {len(docs)} -> {BACKUP_JSON.name} and collection {BACKUP_COLL}")


def stage():
    sdb = client[STAGING_DB]
    sdb.living_codons.drop()
    rest = list(db.living_codons.find({"source": {"$ne": "milton_codons"}}))
    sdb.living_codons.insert_many(rest + [revise(d) for d in originals()])
    print(f"staging DB {STAGING_DB}: {sdb.living_codons.count_documents({})} codons")


def apply():
    for d in originals():
        r = revise(d)
        db.living_codons.replace_one({"_id": d["_id"]}, r)
    print("applied 10 revisions to living_codons")


def restore():
    docs = list(db[BACKUP_COLL].find({}))
    assert len(docs) == 10
    for d in docs:
        db.living_codons.replace_one({"_id": d["_id"]}, d, upsert=True)
    print("restored 10 originals from", BACKUP_COLL)


if __name__ == "__main__":
    {"backup": backup, "stage": stage, "apply": apply, "restore": restore}[sys.argv[1]]()
