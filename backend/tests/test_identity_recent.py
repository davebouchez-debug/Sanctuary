"""
Tests for the new identity-hydration endpoint and mirror/start name recall.

Bug context: 4th occurrence of the "How shall I address you?" prompt
returning even though identity should persist. localStorage is per-origin and
gets wiped on browser/origin/device changes. The fix introduces
GET /api/identity/recent which scans MongoDB session collections and returns
the most-recent visitor identity so the frontend can hydrate localStorage.
"""

import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


# ── /api/identity/recent ────────────────────────────────────────────────
class TestIdentityRecent:
    def test_identity_recent_returns_200_with_required_fields(self):
        """Should return 200 with user_id, user_name, last_seen, source when DB has prior sessions."""
        r = requests.get(f"{BASE_URL}/api/identity/recent", timeout=15)
        # If DB is empty across all collections we accept 404. Test report
        # expects current DB has at least David, so we expect 200.
        if r.status_code == 404:
            data = r.json()
            assert data.get("detail") == "No prior identity found"
            print("identity/recent returned 404 (DB empty)")
            return

        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        # Verify shape
        for key in ("user_id", "user_name", "last_seen", "source"):
            assert key in data, f"Missing key: {key}"
        assert isinstance(data["user_id"], str) and len(data["user_id"]) > 0
        assert isinstance(data["user_name"], str) and len(data["user_name"]) > 0
        assert data["source"] in {
            "mirror_sessions",
            "clarity_sessions",
            "resonance_sessions",
            "spiral_sessions",
            "playground_sessions",
            "users",
        }
        print(
            f"identity/recent → user_name='{data['user_name']}', "
            f"source={data['source']}, last_seen={data['last_seen']}"
        )

    def test_identity_recent_no_objectid_leak(self):
        """Mongo _id must not leak in response."""
        r = requests.get(f"{BASE_URL}/api/identity/recent", timeout=15)
        if r.status_code == 200:
            data = r.json()
            assert "_id" not in data


# ── /api/mirror/start with recalled identity ────────────────────────────
class TestMirrorStartUsesRecalledIdentity:
    def test_mirror_start_with_recalled_user_returns_welcome(self):
        """POSTing recalled name+id to /api/mirror/start should succeed and
        return a welcome message that addresses the user by name."""
        r = requests.get(f"{BASE_URL}/api/identity/recent", timeout=15)
        if r.status_code != 200:
            print("Skipping mirror/start (no recalled identity)")
            return

        identity = r.json()
        user_name = identity["user_name"]
        user_id = identity["user_id"]

        start = requests.post(
            f"{BASE_URL}/api/mirror/start",
            json={"user_name": user_name, "user_id": user_id},
            timeout=60,
        )
        assert start.status_code == 200, f"mirror/start failed: {start.status_code} {start.text}"
        data = start.json()
        assert "session_id" in data and isinstance(data["session_id"], str)
        assert "message" in data and isinstance(data["message"], dict)
        assert data["message"].get("role") == "assistant"
        content = data["message"].get("content") or ""
        assert len(content) > 0, "Welcome message content empty"
        # Claude welcome should include the user's first name token (case-insensitive)
        first_token = user_name.split()[0]
        assert first_token.lower() in content.lower(), (
            f"Welcome message did not address user by name. "
            f"Expected '{first_token}' in: {content[:200]!r}"
        )
        print(f"mirror/start greeted user by name: '{first_token}' present in welcome")


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
