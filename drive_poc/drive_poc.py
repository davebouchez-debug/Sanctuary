"""Google Drive proof of concept — synthetic ZIP only, standalone (not imported by the app).

    python drive_poc.py run                 # build synthetic ZIP, upload once per day-name, verify, download, verify
    python drive_poc.py verify <file_id>    # independent retrieval + checksum check (any token with read access)
    python drive_poc.py selftest            # offline + bad-credential failure checks (no Google account needed)

Credentials come only from environment / backend/.env:
GDRIVE_POC_CLIENT_ID, GDRIVE_POC_CLIENT_SECRET, GDRIVE_POC_REFRESH_TOKEN (scope drive.file).
"""
import hashlib
import io
import json
import os
import sys
import uuid
import zipfile
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", ".env"))
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER_NAME = "Sanctuary 1.0 Deliveries (POC)"
FOLDER_MIME = "application/vnd.google-apps.folder"


class PocError(Exception):
    pass


def synthetic_zip(day: str) -> bytes:
    lines = [json.dumps({"_id": {"$oid": f"6740b00000000000000000{i:02d}"}, "phrase": f"Synthetic test phrase {i}",
                         "presence": "field", "created_at": f"{day}T00:00:00+00:00", "source": "synthetic"})
             for i in range(1, 4)]
    body = ("\n".join(lines) + "\n").encode()
    manifest = json.dumps({"schema": "sanctuary-codon-export/1", "synthetic": True, "record_count": len(lines),
                           "files": {"field_phrases.jsonl": {"bytes": len(body),
                                                             "sha256": hashlib.sha256(body).hexdigest()}}},
                          indent=1, sort_keys=True).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in (("manifest.json", manifest), ("field_phrases.jsonl", body)):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            z.writestr(info, data, zipfile.ZIP_DEFLATED)
    return buf.getvalue()


def access_token(c: httpx.Client, refresh_token: str = None) -> str:
    cid, secret = os.environ.get("GDRIVE_POC_CLIENT_ID"), os.environ.get("GDRIVE_POC_CLIENT_SECRET")
    refresh_token = refresh_token or os.environ.get("GDRIVE_POC_REFRESH_TOKEN")
    if not (cid and secret and refresh_token):
        raise PocError("credentials_missing")
    r = c.post(TOKEN_URL, data={"grant_type": "refresh_token", "client_id": cid, "client_secret": secret,
                                "refresh_token": refresh_token})
    if r.status_code != 200:
        raise PocError(f"token_refresh_failed:{r.status_code}:{r.json().get('error', 'unknown')}")
    return r.json()["access_token"]


def _check(r: httpx.Response, step: str):
    if r.status_code >= 300:
        raise PocError(f"{step}_failed:{r.status_code}")
    return r.json() if r.content and "json" in r.headers.get("content-type", "") else r


def find(c, h, name, parent=None, mime=None):
    q = [f"name = '{name}'", "trashed = false"] + ([f"'{parent}' in parents"] if parent else []) + \
        ([f"mimeType = '{mime}'"] if mime else [])
    r = _check(c.get(f"{API}/files", headers=h, params={"q": " and ".join(q), "spaces": "drive",
                                                       "fields": "files(id,name,size,md5Checksum,appProperties)"}),
               "list")
    return r["files"]


def ensure_folder(c, h) -> str:
    found = find(c, h, FOLDER_NAME, mime=FOLDER_MIME)
    if found:
        return found[0]["id"]
    return _check(c.post(f"{API}/files", headers=h, json={"name": FOLDER_NAME, "mimeType": FOLDER_MIME},
                         params={"fields": "id"}), "create_folder")["id"]


def upload(c, h, folder, name, data: bytes) -> dict:
    boundary = uuid.uuid4().hex
    meta = {"name": name, "parents": [folder], "appProperties": {"sha256": hashlib.sha256(data).hexdigest()}}
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
            f"--{boundary}\r\nContent-Type: application/zip\r\n\r\n").encode() + data + f"\r\n--{boundary}--".encode()
    return _check(c.post(UPLOAD, headers={**h, "Content-Type": f"multipart/related; boundary={boundary}"},
                         params={"uploadType": "multipart", "fields": "id,name,size,md5Checksum,appProperties"},
                         content=body), "upload")


def verify(c, h, file_id: str, expected_sha256: str = None) -> dict:
    meta = _check(c.get(f"{API}/files/{file_id}", headers=h,
                        params={"fields": "id,name,size,md5Checksum,appProperties"}), "metadata")
    data = _check(c.get(f"{API}/files/{file_id}", headers=h, params={"alt": "media"}), "download").content
    sha, md5 = hashlib.sha256(data).hexdigest(), hashlib.md5(data).hexdigest()
    expected = expected_sha256 or (meta.get("appProperties") or {}).get("sha256")
    zipfile.ZipFile(io.BytesIO(data)).testzip()
    return {"file_id": file_id, "name": meta["name"], "bytes": len(data), "sha256": sha,
            "size_matches": int(meta["size"]) == len(data), "md5_matches": meta.get("md5Checksum") == md5,
            "sha256_matches": sha == expected, "ok": int(meta["size"]) == len(data)
            and meta.get("md5Checksum") == md5 and sha == expected}


def run() -> dict:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    name, data = f"sanctuary1_poc_synthetic_{day.replace('-', '')}.zip", synthetic_zip(day)
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "file": name, "bytes": len(data),
              "sha256": hashlib.sha256(data).hexdigest()}
    with httpx.Client(timeout=60) as c:
        h = {"Authorization": f"Bearer {access_token(c)}"}
        folder = ensure_folder(c, h)
        existing = find(c, h, name, parent=folder)
        if existing:
            report["upload"] = "skipped_duplicate"
            fid = existing[0]["id"]
        else:
            up = upload(c, h, folder, name, data)
            fid = up["id"]
            report["upload"] = "uploaded"
            report["md5_reported_matches"] = up.get("md5Checksum") == hashlib.md5(data).hexdigest()
            if not report["md5_reported_matches"]:
                c.patch(f"{API}/files/{fid}", headers=h, json={"trashed": True})
                raise PocError("integrity_mismatch_after_upload")
        report["verify"] = verify(c, h, fid, report["sha256"])
        report["duplicates_in_folder"] = len(find(c, h, name, parent=folder))
    report["ok"] = report["verify"]["ok"] and report["duplicates_in_folder"] == 1
    return report


def selftest() -> dict:
    out = {}
    a, b = synthetic_zip("2026-11-20"), synthetic_zip("2026-11-20")
    out["zip_deterministic"] = a == b
    out["zip_valid"] = zipfile.ZipFile(io.BytesIO(a)).testzip() is None
    saved = {k: os.environ.pop(k, None) for k in ("GDRIVE_POC_CLIENT_ID", "GDRIVE_POC_CLIENT_SECRET",
                                                   "GDRIVE_POC_REFRESH_TOKEN")}
    try:
        with httpx.Client(timeout=30) as c:
            try:
                access_token(c)
            except PocError as e:
                out["missing_credentials_reported"] = str(e) == "credentials_missing"
            os.environ.update({"GDRIVE_POC_CLIENT_ID": "invalid.apps.googleusercontent.com",
                               "GDRIVE_POC_CLIENT_SECRET": "invalid"})
            try:
                access_token(c, refresh_token="invalid")
            except PocError as e:
                out["google_reachable_and_bad_credentials_reported"] = str(e).startswith("token_refresh_failed:4")
                out["bad_credentials_error"] = str(e)
            r = c.get(f"{API}/files", headers={"Authorization": "Bearer invalid"})
            out["drive_api_reachable_rejects_bad_token"] = r.status_code == 401
    finally:
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v:
                os.environ[k] = v
    out["ok"] = all(v for k, v in out.items() if k != "bad_credentials_error")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    try:
        if cmd == "run":
            result = run()
        elif cmd == "verify":
            with httpx.Client(timeout=60) as c:
                result = verify(c, {"Authorization": f"Bearer {access_token(c)}"}, sys.argv[2])
        else:
            result = selftest()
    except PocError as e:
        result = {"ok": False, "error": str(e)}
    except httpx.HTTPError as e:
        result = {"ok": False, "error": f"network:{type(e).__name__}"}
    print(json.dumps(result, indent=1))
    sys.exit(0 if result.get("ok") else 1)
