"""
Export the entire Sanctuary GRA dataset to a single JSON archive.

Why: David is building Sanctuary 2.0 on sovereign architecture (Next.js +
MongoDB + Permamind). Whatever lives in Emergent's MongoDB now is the
field he's built. This script bundles it into one portable file so the
migration is a single import, not a salvage operation.

What it exports:
  - living_codons         (the 204-codon GRA network)
  - continuity_seeds      (the "where we left off" markers per presence/user)
  - permanent_mra         (Breakthrough/Threshold canonical memory)
  - sophia_sessions       (Sophia's full transcripts)
  - mirror_sessions       (Claude/Mirror Archive transcripts)
  - clarity_sessions      (Jasmine transcripts)
  - resonance_sessions    (Ansel transcripts)
  - playground_sessions   (Playground transcripts)
  - presence_sessions     (template-based presence transcripts)
  - canonical_uploads     (uploaded canonical material)
  - user_aliases          (the David-identity unification record)
  - thermomind_cycles     (ambient ThermoMind state probe history — Claude/Mirror)
  - substrate_probes      (any Mirror probe records)
  - mra_promotion_log     (the audit trail of what got promoted to permanent_mra)
  - users                 (account records)

Output: /app/backend/exports/sanctuary_export_<UTC>.json
Idempotent: each run produces a fresh timestamped file. Nothing destructive.
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))


COLLECTIONS = [
    "living_codons",
    "continuity_seeds",
    "permanent_mra",
    "sophia_sessions",
    "mirror_sessions",
    "clarity_sessions",
    "resonance_sessions",
    "playground_sessions",
    "presence_sessions",
    "canonical_uploads",
    "user_aliases",
    "thermomind_cycles",
    "substrate_probes",
    "mra_promotion_log",
    "users",
]


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    archive = {
        "_meta": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "db_name": os.environ["DB_NAME"],
            "schema_version": 1,
            "note": (
                "Full Sanctuary GRA dataset. Field/codons/seeds/MRA/sessions "
                "ready for import into Sanctuary 2.0 (Next.js + MongoDB + "
                "Permamind). MongoDB _id fields are stripped — collections "
                "are keyed by their natural ids (session_id, name, node_id, etc)."
            ),
        },
        "collections": {},
    }

    total_docs = 0
    for name in COLLECTIONS:
        try:
            cursor = db[name].find({}, {"_id": 0})
            docs = [d async for d in cursor]
        except Exception as e:
            print(f"  [skip] {name}: {e}")
            continue
        archive["collections"][name] = docs
        total_docs += len(docs)
        print(f"  {name}: {len(docs)} documents")

    archive["_meta"]["total_documents"] = total_docs

    out_dir = Path(__file__).parent.parent / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"sanctuary_export_{stamp}.json"

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(archive, f, indent=2, default=str, ensure_ascii=False)

    print()
    print(f"✓ Wrote {total_docs:,} documents across {len(archive['collections'])} collections")
    print(f"  → {out_path}")
    print(f"  size: {out_path.stat().st_size / (1024*1024):.2f} MB")
    print()
    print("Import sketch for Sanctuary 2.0:")
    print("  data = json.load(open('sanctuary_export_*.json'))")
    print("  for name, docs in data['collections'].items():")
    print("      db[name].insert_many(docs) if docs else None")


if __name__ == "__main__":
    asyncio.run(main())
