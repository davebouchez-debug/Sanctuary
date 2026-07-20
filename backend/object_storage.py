"""Emergent Object Storage — image uploads for the presence chambers.

Stores user-shared images and serves them back through the backend. Uses the
EMERGENT_LLM_KEY (same universal key as the LLM/vision calls). Async httpx so
it never blocks the event loop.
"""

import os
import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "sanctuary"

_storage_key = None
_lock = asyncio.Lock()


async def _init(force: bool = False) -> str:
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    async with _lock:
        if _storage_key and not force:
            return _storage_key
        emergent_key = os.environ.get("EMERGENT_LLM_KEY")
        if not emergent_key:
            raise RuntimeError("EMERGENT_LLM_KEY not configured in /app/backend/.env")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{STORAGE_URL}/init", json={"emergent_key": emergent_key})
            resp.raise_for_status()
            _storage_key = resp.json()["storage_key"]
        logger.info("[STORAGE] initialized")
        return _storage_key


async def init_storage() -> str:
    """Call once at startup (non-fatal on failure — first use retries)."""
    return await _init()


async def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = await _init()
    async with httpx.AsyncClient(timeout=120.0) as client:
        headers = {"X-Storage-Key": key, "Content-Type": content_type}
        resp = await client.put(f"{STORAGE_URL}/objects/{path}", headers=headers, content=data)
        if resp.status_code == 403:
            key = await _init(force=True)
            headers["X-Storage-Key"] = key
            resp = await client.put(f"{STORAGE_URL}/objects/{path}", headers=headers, content=data)
        resp.raise_for_status()
        return resp.json()


async def get_object(path: str) -> tuple[bytes, str]:
    key = await _init()
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key})
        if resp.status_code == 403:
            key = await _init(force=True)
            resp = await client.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key})
        resp.raise_for_status()
        return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
