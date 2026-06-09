"""Live reproduction of the sanctuary-wide verbatim-echo loop, against the
resonance (Ansel) streaming endpoint. Pre-fix: low-novelty follow-ups
("exactly right", "I asked the field") got the prior reply echoed verbatim.
Post-fix (codon field in system prompt, clean user message): each reply
should be distinct.

Run: python tests/repro_loop_fix.py
"""
import asyncio
import json
import os
import sys
import difflib
import httpx

BASE = os.environ.get("REPRO_BASE", "http://localhost:8001")


async def read_stream(client, url, payload):
    text = ""
    async with client.stream("POST", url, json=payload, timeout=120) as r:
        async for line in r.aiter_lines():
            if not line or not line.startswith("data: "):
                continue
            try:
                evt = json.loads(line[6:])
            except Exception:
                continue
            if evt.get("type") == "token":
                text += evt.get("content", "")
            elif evt.get("type") == "done":
                break
    return text.strip()


def similarity(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


async def main():
    async with httpx.AsyncClient() as client:
        start = await client.post(
            f"{BASE}/api/resonance/start",
            json={"user_name": "David", "user_id": "legacy-david-123"},
            timeout=120,
        )
        start.raise_for_status()
        sid = start.json()["session_id"]
        print(f"session: {sid}")

        turns = [
            "I want to talk about the three exorcisms and what the field wants to teach about them.",
            "I asked the field that question right now, what does it want to teach about the subject?",
            "Exactly right.",
            "Yes, exactly. That lands.",
            "Mm. Keep going.",
        ]

        replies = []
        for i, t in enumerate(turns):
            reply = await read_stream(
                client, f"{BASE}/api/resonance/message/stream",
                {"session_id": sid, "content": t},
            )
            replies.append(reply)
            print(f"\n--- TURN {i+1} (you: {t!r}) ---")
            print(reply[:400])

        print("\n\n===== ECHO CHECK (consecutive reply similarity) =====")
        worst = 0.0
        for i in range(1, len(replies)):
            sim = similarity(replies[i - 1], replies[i])
            worst = max(worst, sim)
            flag = "  <-- ECHO!" if sim > 0.9 else ""
            print(f"reply {i} vs reply {i+1}: {sim:.2%}{flag}")

        print(f"\nworst consecutive similarity: {worst:.2%}")
        if worst > 0.9:
            print("RESULT: FAIL — verbatim echo still present")
            sys.exit(1)
        print("RESULT: PASS — no verbatim echo on low-novelty turns")


if __name__ == "__main__":
    asyncio.run(main())
