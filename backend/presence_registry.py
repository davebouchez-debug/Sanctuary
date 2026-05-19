"""
DEPRECATED — kept only as a backward-compatible shim.

Presence configs are now defined one-per-file under /app/backend/presences/.
The auto-loader in `presences/__init__.py` discovers them at import time.
New presences should be added there, not here.

Existing imports (`from presence_registry import ...`) continue to work
because every name re-exports from the new package.
"""

from presences import (  # noqa: F401
    get_presence_config,
    list_presence_keys,
    list_presence_summaries,
    list_all_presences as PRESENCE_CHAMBERS_FN,
)

# Some legacy callers expect the bare dict. Materialize once.
PRESENCE_CHAMBERS = PRESENCE_CHAMBERS_FN()
