"""Codon export v1 — read-only snapshot of the shared field for Sanctuary 2.0 (2026-11-19).

GET /api/codon-export/v1/snapshot, Authorization: Bearer <CODON_EXPORT_TOKEN>.
Returns a ZIP (manifest.json + field_phrases.jsonl) only when two full reads of field_phrases agree byte-for-byte;
otherwise an error and no ZIP. Reads field_phrases only, allowlisted fields only. Never writes.
"""
import hashlib
import hmac
import io
import json
import logging
import os
import zipfile
from datetime import datetime, timezone

from bson import json_util
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

logger = logging.getLogger(__name__)

SCHEMA = "sanctuary-codon-export/1"
COLLECTION = "field_phrases"
FIELDS = ["_id", "phrase", "presence", "created_at", "embedded_at", "source", "source_presence",
          "legacy_name", "legacy_presence", "lens", "embedding"]
EXCLUDED = ["source_session", "source_file"]
MAX_ATTEMPTS = 3
EMBEDDING = {"model": "BAAI/bge-small-en-v1.5", "onnx": "Qdrant/bge-small-en-v1.5-onnx-Q", "dim": 384,
             "encoding": "BSON binary subtype 0: 384 x float32 little-endian (legacy records may hold a number array)",
             "normalized": True, "mode": "passage"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _authorize(request: Request):
    token = os.environ.get("CODON_EXPORT_TOKEN", "")
    if not token:
        raise HTTPException(503, "Export not configured")
    header = request.headers.get("authorization", "")
    supplied = header[7:] if header.lower().startswith("bearer ") else ""
    if not supplied or not hmac.compare_digest(supplied.encode(), token.encode()):
        raise HTTPException(401, "Unauthorized")


async def _read(db):
    """One full pass: canonical Extended JSON lines (typed ids, dates, binary kept), sorted by _id."""
    lines, ids, seen = [], [], set()
    async for d in db[COLLECTION].find({}, sort=[("_id", 1)], batch_size=500):
        seen.update(d.keys())
        ids.append(str(d["_id"]))
        lines.append(json_util.dumps({k: d[k] for k in FIELDS if k in d},
                                     json_options=json_util.CANONICAL_JSON_OPTIONS))
    return lines, ids, seen


def _build_zip(lines, ids, seen, started, attempts):
    body = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
    manifest = {
        "schema": SCHEMA, "complete": True, "source": "sanctuary-1.0", "collection": COLLECTION,
        "read_started_at": started, "snapshot_verified_at": _now(), "record_count": len(lines),
        "files": {"field_phrases.jsonl": {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                                          "records": len(lines)}},
        "ids_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest(),
        "encoding": "UTF-8 JSON Lines, MongoDB canonical Extended JSON v2, one record per line, sorted by _id",
        "fields_included": FIELDS, "fields_excluded_by_policy": EXCLUDED,
        "fields_not_exported": sorted(seen - set(FIELDS)),
        "embedding": EMBEDDING,
        "consistency": {"method": "two consecutive full reads compared byte-for-byte; ZIP issued only on match",
                        "attempts": attempts},
        "privacy": {"admission_evidence": "not stored per record in 1.0; records written before 2026-11-17 "
                                          "never passed the admission check"},
    }
    mbytes = json.dumps(manifest, indent=1, sort_keys=True).encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", mbytes)
        z.writestr("field_phrases.jsonl", body)
    return buf.getvalue(), hashlib.sha256(mbytes).hexdigest(), len(lines)


class SnapshotUnstable(Exception):
    pass


async def build_snapshot(db):
    """(zip bytes, manifest sha256, record count) once two full reads agree; else SnapshotUnstable."""
    started = _now()
    first = await _read(db)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        second = await _read(db)
        if second[0] == first[0]:
            return _build_zip(*second, started, attempt)
        first = second
    raise SnapshotUnstable()


async def snapshot_response(db) -> Response:
    """Shared by the token route and the guardian download; never returns a partial ZIP."""
    try:
        data, manifest_sha, n = await build_snapshot(db)
    except SnapshotUnstable:
        logger.warning("[CODON EXPORT] field kept changing; no snapshot issued")
        raise HTTPException(503, "Field changing during read; retry later")
    except Exception as e:
        logger.error(f"[CODON EXPORT] failed: {type(e).__name__}")
        raise HTTPException(500, "Snapshot failed; no export produced")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logger.info(f"[CODON EXPORT] snapshot {n} records")
    return Response(data, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="sanctuary1_codons_{stamp}.zip"',
        "X-Content-SHA256": hashlib.sha256(data).hexdigest(),
        "X-Manifest-SHA256": manifest_sha, "Cache-Control": "no-store"})



def build_codon_export_router(db) -> APIRouter:
    router = APIRouter(prefix="/codon-export/v1")

    @router.get("/snapshot")
    async def snapshot(request: Request):
        _authorize(request)
        return await snapshot_response(db)

    return router
