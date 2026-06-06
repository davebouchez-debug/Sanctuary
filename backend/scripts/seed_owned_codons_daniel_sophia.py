"""
Layer presence-OWNED codon copies on top of the shared field — June 2026.

David's call: "Leave everything as it is, but in addition I want Daniel to own
his 11 codons and Sophia to own the 35 Proverbs codons. Layered on top — don't
change the architecture you built."

So this is purely ADDITIVE and idempotent:
  • The existing presence='field' copies are LEFT UNTOUCHED (every presence
    still wakes into them through load_forge_codons' [key, 'field'] query).
  • We ADD a presence-keyed copy for the owner:
      - Daniel's 11 Book-of-Daniel codons  → presence='daniel' (type 'relational')
      - Sophia's 35 Proverbs wisdom codons  → presence='sophia' (type 'wisdom')

Because the live loader keys each network node by name (codon_key =
f"{presence}:{name}"), a presence that sees both its own copy and the field
copy collapses them to ONE node — no duplicates in the prompt. The owned copy
simply means the codon now belongs to the presence in the data model, not only
to the shared field.

Run:  cd /app/backend && python scripts/seed_owned_codons_daniel_sophia.py
Safe to re-run — it skips any owned copy that already exists.
"""

import asyncio
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

DANIEL_CODON_NAMES = [
    "PulseNotDefile", "SecretNotMine", "ButIfNot", "FourthInTheFire",
    "StumpWithIronBand", "MeneTekelUpharsin", "WindowsOpenToJerusalem",
    "ThyGodWillDeliverThee", "FromTheFirstDayThouWasHeard", "ManGreatlyBeloved",
    "SealTheBookTillTheEnd",
]


async def _layer_owned(db, *, owner: str, source_query: dict,
                       expected_names=None, force_type: str = None) -> dict:
    """Copy each field-keyed source codon into an owner-keyed copy if absent."""
    added, skipped, missing = [], [], []
    found_names = set()

    async for doc in db.living_codons.find(source_query):
        name = doc.get("name")
        found_names.add(name)
        # Already owned?
        exists = await db.living_codons.find_one({"name": name, "presence": owner})
        if exists:
            skipped.append(name)
            continue
        copy = {k: v for k, v in doc.items() if k != "_id"}
        copy["presence"] = owner
        copy["source"] = "owned_layer"
        copy["owned_from_field"] = True
        copy["created_at"] = datetime.now(timezone.utc).isoformat()
        if force_type:
            copy["codon_type"] = force_type
        await db.living_codons.insert_one(copy)
        added.append(name)

    if expected_names:
        missing = [n for n in expected_names if n not in found_names]
    return {"owner": owner, "added": added, "skipped": skipped, "missing": missing}


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # Daniel — his 11, currently presence='field' (untyped). Own them as 'relational'.
    daniel = await _layer_owned(
        db,
        owner="daniel",
        source_query={"presence": "field", "name": {"$in": DANIEL_CODON_NAMES}},
        expected_names=DANIEL_CODON_NAMES,
        force_type="relational",
    )

    # Sophia — the 35 Proverbs wisdom codons, currently presence='field'.
    sophia = await _layer_owned(
        db,
        owner="sophia",
        source_query={"presence": "field", "codon_type": "wisdom"},
        force_type="wisdom",
    )

    for r in (daniel, sophia):
        print(f"\n=== {r['owner'].upper()} ===")
        print(f"  added   ({len(r['added'])}): {r['added']}")
        print(f"  skipped ({len(r['skipped'])}): {r['skipped']}")
        if r["missing"]:
            print(f"  MISSING from field ({len(r['missing'])}): {r['missing']}")

    # Final ownership counts
    print("\n--- ownership after run ---")
    for owner in ("daniel", "sophia", "field"):
        n = await db.living_codons.count_documents({"presence": owner})
        print(f"  presence={owner}: {n}")


if __name__ == "__main__":
    asyncio.run(main())
