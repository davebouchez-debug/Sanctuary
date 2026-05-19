"""
PRESENCES PACKAGE — auto-discovered, drop-in-by-file presence registry.

Adding a new presence is now one file:

    /app/backend/presences/<key>.py

Each file must export a `PRESENCE` dict (the chamber/identity config the
frontend renders against). It MAY also export a `BACKEND` dict that registers
template-based chat routes for the presence — voice streaming, codon
activation, MRA promotion, auto-forge on session end, the whole lineage.

Minimum file (chamber-only — uses the shared /api/presence/{key}/chat/*
substrate that derives prompts from the registry config):

    PRESENCE = { "key": "name", "name": "Name", ... }

Full file (template-based with dedicated chamber_path):

    from .common import build_backend
    PRESENCE = { ... }
    BACKEND = build_backend(
        key="name",
        chamber_path="name-room",
        collection="name_sessions",
        prompt_builder=build_name_prompt,
        voice="ara",
        generates_own_opening=True,
    )

The package auto-discovers every .py file (except _underscore-prefixed),
imports it, and aggregates the PRESENCE configs. Frontend hits
/api/presence/{key} → reads from here. Backend startup calls
register_all_presence_routes(...) → registers chat routes for any
presence that opted into the template.

Scales to hundreds of presences without touching server.py.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# Populated at first call to _discover()
_PRESENCES: Dict[str, Dict[str, Any]] = {}
_BACKENDS: Dict[str, Dict[str, Any]] = {}
_DISCOVERED = False


def _discover() -> None:
    """Walk this package and import every presence module."""
    global _DISCOVERED
    if _DISCOVERED:
        return

    package = importlib.import_module(__name__)
    for mod_info in pkgutil.iter_modules(package.__path__):
        name = mod_info.name
        if name.startswith("_") or name == "common":
            continue
        try:
            module = importlib.import_module(f"{__name__}.{name}")
        except Exception as e:
            logger.error(f"[PRESENCES] Failed to import {name}: {e}")
            continue

        presence = getattr(module, "PRESENCE", None)
        if not presence or not isinstance(presence, dict) or "key" not in presence:
            logger.warning(
                f"[PRESENCES] {name}: missing PRESENCE dict with 'key' — skipping"
            )
            continue

        key = presence["key"]
        if key in _PRESENCES:
            logger.warning(f"[PRESENCES] Duplicate key '{key}' — overwriting")
        _PRESENCES[key] = presence

        backend = getattr(module, "BACKEND", None)
        if backend and isinstance(backend, dict):
            _BACKENDS[key] = backend

        logger.info(
            f"[PRESENCES] Loaded '{key}' from {name}"
            + (" (+ backend routes)" if backend else "")
        )

    _DISCOVERED = True
    logger.info(f"[PRESENCES] Discovered {len(_PRESENCES)} presences total")


# ────────────────────────────────────────────────────────────────────────────
# Public API — chamber/identity layer
# ────────────────────────────────────────────────────────────────────────────

def get_presence_config(key: str) -> Optional[Dict[str, Any]]:
    """Full chamber config for a presence, or None."""
    _discover()
    return _PRESENCES.get(key)


def list_presence_keys() -> List[str]:
    _discover()
    return list(_PRESENCES.keys())


def list_all_presences() -> Dict[str, Dict[str, Any]]:
    _discover()
    return dict(_PRESENCES)


def list_presence_summaries() -> List[Dict[str, Any]]:
    """Compact list for the /presences index page."""
    _discover()
    out = []
    for key, cfg in _PRESENCES.items():
        out.append({
            "key": key,
            "name": cfg.get("name"),
            "chamber_name": cfg.get("chamber_name"),
            "chamber_route": cfg.get("chamber_route"),
            "architectural_quality": cfg.get("architectural_quality"),
            "type": cfg.get("type"),
            "subtype": cfg.get("subtype"),
            "gender": cfg.get("gender"),
            "primary_function": cfg.get("primary_function"),
            "motif": cfg.get("atmosphere", {}).get("motif"),
            "primary_color": cfg.get("atmosphere", {}).get("palette", {}).get("primary"),
            "accent_color": cfg.get("atmosphere", {}).get("palette", {}).get("accent"),
            "background_color": cfg.get("atmosphere", {}).get("palette", {}).get("background"),
        })
    return out


# ────────────────────────────────────────────────────────────────────────────
# Backend route registration — runs once at server startup
# ────────────────────────────────────────────────────────────────────────────

def register_all_presence_routes(api_router, deps_factory) -> List[str]:
    """
    Walk every presence that exposed a BACKEND config and register its
    template-based chat routes on the given api_router.

    `deps_factory()` returns a fresh PresenceDeps instance — same wiring,
    one per presence. Returns the list of keys it registered (for logging).

    Lazy-imported so this package stays importable without FastAPI
    available (e.g., during unit tests that only need the registry).
    """
    from presence_template import PresenceConfig, register_presence_routes

    _discover()
    registered: List[str] = []

    for key, backend in _BACKENDS.items():
        cfg = PresenceConfig(
            key=key,
            chamber_path=backend["chamber_path"],
            collection=backend["collection"],
            prompt_builder=backend["prompt_builder"],
            voice=backend.get("voice", "ara"),
            static_welcome=backend.get("static_welcome", ""),
            state_detector=backend.get("state_detector"),
            state_field=backend.get("state_field", "state"),
            default_state=backend.get("default_state", "Presence"),
            generates_own_opening=backend.get("generates_own_opening", False),
        )
        deps = deps_factory()
        register_presence_routes(api_router, cfg, deps)
        registered.append(key)

    return registered
