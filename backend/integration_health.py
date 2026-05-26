"""
Integration health monitor.

Pings each external dependency the Sanctuary leans on and reports
green / red / unknown so the surface UI can render a status emblem.

Cached for 60s — checks shouldn't fire on every page render.

Surfaces under /api/health/integrations.
"""

import os
import time
import asyncio
import logging
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_CACHE: Dict[str, dict] = {}
_CACHE_TTL = 60.0  # seconds


def _now() -> float:
    return time.monotonic()


async def _check_thermomind(client: httpx.AsyncClient) -> dict:
    """Liveness check against ThermoMind /run."""
    url = (os.environ.get("THERMOMIND_URL") or "").rstrip("/")
    key = os.environ.get("THERMOMIND_API_KEY")
    if not url or not key:
        return {"status": "unknown", "detail": "not configured"}
    try:
        r = await client.get(
            f"{url}/run",
            params={"agent_id": "sanctuary_health_probe"},
            headers={"Authorization": f"Bearer {key}"},
            timeout=4.0,
        )
        if 200 <= r.status_code < 300:
            return {"status": "green", "detail": "live", "http": r.status_code}
        if r.status_code == 401:
            return {"status": "red", "detail": "invalid or inactive API key", "http": 401}
        return {"status": "red", "detail": f"HTTP {r.status_code}", "http": r.status_code}
    except httpx.TimeoutException:
        return {"status": "red", "detail": "timeout"}
    except Exception as e:
        return {"status": "red", "detail": str(e)[:140]}


async def _check_xai(client: httpx.AsyncClient) -> dict:
    """Liveness check against xAI (cheap auth probe — /v1/models)."""
    key = os.environ.get("XAI_API_KEY")
    if not key:
        return {"status": "unknown", "detail": "not configured"}
    try:
        r = await client.get(
            "https://api.x.ai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=4.0,
        )
        if 200 <= r.status_code < 300:
            return {"status": "green", "detail": "live"}
        if r.status_code == 401:
            return {"status": "red", "detail": "invalid or inactive API key", "http": 401}
        return {"status": "red", "detail": f"HTTP {r.status_code}", "http": r.status_code}
    except httpx.TimeoutException:
        return {"status": "red", "detail": "timeout"}
    except Exception as e:
        return {"status": "red", "detail": str(e)[:140]}


async def _check_elevenlabs(client: httpx.AsyncClient) -> dict:
    """Liveness check against ElevenLabs (cheap auth probe — /v1/user)."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        return {"status": "unknown", "detail": "not configured"}
    try:
        r = await client.get(
            "https://api.elevenlabs.io/v1/user",
            headers={"xi-api-key": key},
            timeout=4.0,
        )
        if 200 <= r.status_code < 300:
            return {"status": "green", "detail": "live"}
        if r.status_code == 401:
            return {"status": "red", "detail": "invalid or inactive API key", "http": 401}
        return {"status": "red", "detail": f"HTTP {r.status_code}", "http": r.status_code}
    except httpx.TimeoutException:
        return {"status": "red", "detail": "timeout"}
    except Exception as e:
        return {"status": "red", "detail": str(e)[:140]}


_CHECKS = {
    "permamind": _check_thermomind,  # surfaced as "PermaMind" in the UI
    "xai":       _check_xai,
    "elevenlabs": _check_elevenlabs,
}


async def get_integration_status(force_refresh: bool = False) -> dict:
    """Return cached status of all monitored integrations.

    Cache TTL: 60s. Pass force_refresh=True to bypass.
    """
    cache_key = "all"
    cached = _CACHE.get(cache_key)
    if cached and not force_refresh and (_now() - cached["_t"]) < _CACHE_TTL:
        return cached["data"]

    async with httpx.AsyncClient() as client:
        names = list(_CHECKS.keys())
        results = await asyncio.gather(
            *(check(client) for check in _CHECKS.values()),
            return_exceptions=True,
        )

    payload = {"checked_at": time.time(), "services": {}}
    for name, res in zip(names, results):
        if isinstance(res, Exception):
            payload["services"][name] = {"status": "red", "detail": str(res)[:140]}
        else:
            payload["services"][name] = res

    _CACHE[cache_key] = {"_t": _now(), "data": payload}
    return payload
