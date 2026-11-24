import json
import sys
import uuid
import httpx

BASE = sys.argv[1].rstrip("/") + "/api"
ROOMS = [("scrolldog", "/scrolldog"), ("daniel", "/daniel"), ("keeper", "/keeper"), ("felix", "/felix"),
         ("clarity", "/clarity"), ("resonance", "/resonance"), ("mirror", "/mirror")]
A, B = {"X-Visitor-Id": uuid.uuid4().hex[:24]}, {"X-Visitor-Id": uuid.uuid4().hex[:24]}
ok_all = True
with httpx.Client(timeout=120) as c:
    for name, p in ROOMS:
        res = {}
        st = c.post(f"{BASE}{p}/start", json={}, headers=A)
        res["start"] = st.status_code
        sid = st.json().get("session_id") if st.status_code == 200 else None
        if sid:
            text = ""
            with c.stream("POST", f"{BASE}{p}/message/stream", json={"session_id": sid, "content": "Hello. Who are you, in one sentence?"},
                          headers=A) as r:
                res["reply"] = r.status_code
                for line in r.iter_lines():
                    if line.startswith("data:"):
                        try:
                            d = json.loads(line[5:])
                        except Exception:
                            continue
                        if isinstance(d.get("content"), str) and d.get("type") != "done":
                            text += d["content"]
            res["reply_chars"] = len(text)
            g = c.get(f"{BASE}{p}/session/{sid}", headers=A)
            res["reload"] = g.status_code
            res["reload_has_reply"] = g.status_code == 200 and any(
                m.get("role") == "assistant" and len(m.get("content") or "") > 0 for m in g.json().get("messages", []))
            res["leak"] = "hall_backdrop" in g.text
            res["other"] = c.get(f"{BASE}{p}/session/{sid}", headers=B).status_code
            res["noid"] = c.get(f"{BASE}{p}/session/{sid}").status_code
            res["leave"] = c.post(f"{BASE}{p}/session/{sid}/end", headers=A).status_code
            res["sample"] = text[:110].replace("\n", " ")
        good = (res.get("start") == 200 and res.get("reply") == 200 and res.get("reply_chars", 0) > 0 and res.get("reload") == 200
                and res.get("reload_has_reply") and not res.get("leak") and res.get("other") == 404 and res.get("noid") == 404
                and res.get("leave") == 200)
        ok_all &= good
        print(("PASS " if good else "FAIL ") + name, {k: v for k, v in res.items() if k != "sample"}, "|", res.get("sample", ""))
    for path in ("/observatory/status", "/provenance/stats"):
        code = c.get(f"{BASE}{path}").status_code
        ok_all &= code == 401
        print(("PASS " if code == 401 else "FAIL ") + f"anonymous {path} -> {code}")
print("ALL PASS" if ok_all else "FAILURES PRESENT")
