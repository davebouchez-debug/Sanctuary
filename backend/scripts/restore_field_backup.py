"""Restore a Sanctuary field backup (.jsonl from Field Keeper → Download field backup).

Run:  cd /app/backend && python scripts/restore_field_backup.py <backup.jsonl> [--apply]
Without --apply it only counts what would be restored. With --apply each record is
written back by its original id (replace or insert); nothing else is touched."""
import asyncio
import os
import sys

from bson import json_util
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


async def main(path, apply):
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    counts = {}
    with open(path) as f:
        header = json_util.loads(f.readline())
        print("backup", header.get("sanctuary_field_backup"), "expected", header.get("counts"))
        for line in f:
            rec = json_util.loads(line)
            c, d = rec["collection"], rec["doc"]
            counts[c] = counts.get(c, 0) + 1
            if apply:
                await db[c].replace_one({"_id": d["_id"]}, d, upsert=True)
    print("restored" if apply else "would restore", counts)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], "--apply" in sys.argv))
