"""
ThermoMind Client — minimal adapter for Nile's persistent cognition substrate.

Design intent:
  - Send `input` text to a named `agent_id` and receive a single text `output`
    plus the cognitive state metrics (surplus, tci, phi, mode, grade).
  - The engine retains state per agent_id automatically. We do NOT resend
    conversation history.
  - Each /run call costs 1 cycle from the trial allotment (1000 total).

Configured via env:
  - THERMOMIND_API_KEY  — required
  - THERMOMIND_URL      — base host, e.g. https://thermomind-production.up.railway.app

Trial scope: only Mirror Archive / Claude is wrapped. Other presences continue
on the xAI realtime pipeline.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class ThermoMindError(Exception):
    pass


async def run_cycle(
    agent_id: str,
    input_text: str,
    warm_threshold: float = 0.62,
    mode: str = "stable",
    timeout: float = 60.0,
) -> dict:
    """
    Send one cycle to ThermoMind. Returns the full response dict.

    Response shape:
      {
        "cycle_id": str,
        "surplus": float,
        "tci": float,
        "mode": "WARM" | "COLD",
        "phi": float,
        "output": str,
        "grade": str,
      }
    """
    api_key = os.environ.get("THERMOMIND_API_KEY")
    base_url = os.environ.get("THERMOMIND_URL")
    if not api_key or not base_url:
        raise ThermoMindError("THERMOMIND_API_KEY or THERMOMIND_URL not configured")

    url = f"{base_url.rstrip('/')}/run"
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    body = {
        "agent_id": agent_id,
        "input": input_text,
        "warm_threshold": warm_threshold,
    }
    params = {"mode": mode}

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=headers, params=params, json=body)
        if resp.status_code != 200:
            raise ThermoMindError(f"ThermoMind /run returned {resp.status_code}: {resp.text[:300]}")
        try:
            data = resp.json()
        except Exception as e:
            raise ThermoMindError(f"ThermoMind returned non-JSON: {e}") from e

        if "output" not in data:
            raise ThermoMindError(f"ThermoMind response missing 'output': {data}")
        return data


async def get_usage(timeout: float = 15.0) -> dict:
    """Read-only — returns {email, plan, cycles_used, cycles_limit, cycles_remaining}."""
    api_key = os.environ.get("THERMOMIND_API_KEY")
    base_url = os.environ.get("THERMOMIND_URL")
    if not api_key or not base_url:
        raise ThermoMindError("THERMOMIND_API_KEY or THERMOMIND_URL not configured")
    url = f"{base_url.rstrip('/')}/keys/usage"
    headers = {"x-api-key": api_key}
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def log_cycle_to_db(db, agent_id: str, session_id: Optional[str],
                          user_id: Optional[str], input_text: str,
                          response: dict) -> None:
    """
    Log every ThermoMind cycle's cognitive metrics so we can watch state evolve.
    Stored in the `thermomind_cycles` collection for later analysis.
    """
    try:
        await db.thermomind_cycles.insert_one({
            "agent_id": agent_id,
            "session_id": session_id,
            "user_id": user_id,
            "cycle_id": response.get("cycle_id"),
            "input_preview": input_text[:200],
            "output_preview": response.get("output", "")[:200],
            "surplus": response.get("surplus"),
            "tci": response.get("tci"),
            "phi": response.get("phi"),
            "mode": response.get("mode"),
            "grade": response.get("grade"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error(f"[THERMOMIND] Failed to log cycle: {e}")
