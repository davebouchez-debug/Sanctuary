"""One-off: publish the Kimi audit bundle to object storage + register it
in chamber_images so the public /api/files/{path} route serves it."""
import asyncio
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from object_storage import put_object

BUNDLE = "/app/sanctuary_1.0_audit_bundle_for_kimi.md"
STORAGE_PATH = "audit/sanctuary_bundle.txt"
CONTENT_TYPE = "text/plain; charset=utf-8"


async def main():
    with open(BUNDLE, "rb") as f:
        data = f.read()

    await put_object(STORAGE_PATH, data, CONTENT_TYPE)

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    await db.chamber_images.update_one(
        {"storage_path": STORAGE_PATH},
        {"$set": {
            "storage_path": STORAGE_PATH,
            "content_type": CONTENT_TYPE,
            "is_deleted": False,
            "bytes": len(data),
            "note": "Sanctuary 1.0 source bundle for Kimi structural audit",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    print(f"PUBLISHED {len(data)} bytes at /api/files/{STORAGE_PATH}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
