"""Codon-forge access tests against the real app routes (no startup, no field writes).
    cd /app/backend && python tests/test_codon_forge_access.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
from fastapi.testclient import TestClient

import auth
from server import app

client = TestClient(app)
WHO = {"none": None, "guest": {"user_id": "t-guest", "role": "guest"},
       "member": {"user_id": "t-member", "role": "user"}, "guardian": {"user_id": "t-guardian", "role": "guardian"}}
CALLS = [("post", "/api/codon-forge/save", {"phrases": [], "filename": "t.txt", "mode": "relational"}),
         ("post", "/api/codon-forge/extract", {"thread_text": "", "filename": "t.txt", "presence": "field"}),
         ("get", "/api/codon-forge/status/nonexistent", None)]
EXPECT = {"none": 401, "guest": 403, "member": 403}
fails = 0
for who, user in WHO.items():
    async def fake(_request, _u=user):
        return _u
    auth._user_from_request = fake
    for method, path, body in CALLS:
        if who == "guardian" and path.endswith("/extract"):
            continue  # would start a real forge job
        r = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)
        ok = r.status_code == EXPECT[who] if who in EXPECT else r.status_code not in (401, 403)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} {who:8} {method.upper():4} {path} -> {r.status_code}")
print("ALL PASS" if not fails else f"{fails} FAILED")
