"""Guardian-only, time-limited download of staged Codex review packages."""
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from auth import require_guardian

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "review_packages"
MAX_AGE_SECONDS = 14 * 24 * 3600

review_packages_router = APIRouter(prefix="/review-packages", tags=["review-packages"])


def _live_packages():
    if not PACKAGE_DIR.is_dir():
        return {}
    now = time.time()
    return {
        p.name: p for p in PACKAGE_DIR.glob("*.zip")
        if p.is_file() and now - p.stat().st_mtime < MAX_AGE_SECONDS
    }


@review_packages_router.get("")
async def list_packages(request: Request):
    await require_guardian(request)
    return {"packages": [{"name": n, "url": f"/api/review-packages/{n}", "bytes": p.stat().st_size}
                         for n, p in sorted(_live_packages().items())]}


@review_packages_router.get("/{name}")
async def download_package(name: str, request: Request):
    await require_guardian(request)
    path = _live_packages().get(name)
    if not path:
        raise HTTPException(status_code=404, detail="Package not found or expired")
    return FileResponse(path, media_type="application/zip", filename=name)
