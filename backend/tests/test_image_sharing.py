"""Backend tests for the chamber image-sharing feature.

Covers:
- POST /api/chamber/upload-image (multipart)
- GET  /api/files/{path} (image served back)
- POST /api/{template}/message/stream with image_path — vision bridge injects
  the description and the presence streams a reply that references it.
- Regression: text-only stream still works.
- Same image flow works for at least two different template presences.
"""
import io
import json
import os
import re
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"


def _make_test_png() -> bytes:
    """A recognizable synthetic image: red circle + blue square + big text
    'HALL OF SCROLLS' on a beige background. Written with Pillow so the vision
    model has clear, unambiguous content to describe."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (800, 500), (245, 232, 200))  # beige
    d = ImageDraw.Draw(img)
    d.ellipse([80, 80, 280, 280], fill=(210, 40, 40))     # red circle
    d.rectangle([420, 100, 700, 300], fill=(30, 60, 180))  # blue square
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except Exception:
        font = ImageFont.load_default()
    d.text((120, 360), "HALL OF SCROLLS", fill=(20, 20, 20), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def png_bytes():
    return _make_test_png()


# ── /api/chamber/upload-image ────────────────────────────────────────────────
class TestUploadImage:
    def test_upload_png_returns_storage_path(self, png_bytes):
        files = {"file": ("TEST_scrolls.png", png_bytes, "image/png")}
        r = requests.post(f"{API}/chamber/upload-image", files=files, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "path" in data and isinstance(data["path"], str) and data["path"]
        assert data.get("content_type", "").startswith("image/")

    def test_uploaded_image_is_served_back(self, png_bytes):
        files = {"file": ("TEST_scrolls2.png", png_bytes, "image/png")}
        up = requests.post(f"{API}/chamber/upload-image", files=files, timeout=60)
        assert up.status_code == 200
        path = up.json()["path"]

        r = requests.get(f"{API}/files/{path}", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")
        # Should be non-trivial bytes (round-trip is not required byte-identical
        # because object storage may re-encode, but should be a real PNG-ish payload)
        assert len(r.content) > 500

    def test_serve_unknown_path_returns_404(self):
        r = requests.get(f"{API}/files/nonexistent/does-not-exist.png", timeout=30)
        assert r.status_code == 404


# ── Stream with image (vision bridge) ────────────────────────────────────────
def _start_session(template_path: str) -> str:
    r = requests.post(
        f"{API}/{template_path}/start",
        json={"user_id": "TEST_image_user", "user_name": "Tester"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def _stream_reply(template_path: str, session_id: str, content: str, image_path: str | None = None) -> str:
    body = {"session_id": session_id, "content": content}
    if image_path:
        body["image_path"] = image_path
    with requests.post(
        f"{API}/{template_path}/message/stream", json=body, stream=True, timeout=180
    ) as r:
        assert r.status_code == 200, r.text
        assembled = []
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            if raw.startswith("data: "):
                try:
                    ev = json.loads(raw[6:])
                except Exception:
                    continue
                if ev.get("type") == "token":
                    assembled.append(ev.get("content", ""))
                elif ev.get("type") == "done":
                    break
        return "".join(assembled)


class TestVisionBridgeStream:
    def test_daniel_replies_to_shared_image(self, png_bytes):
        # 1. upload
        up = requests.post(
            f"{API}/chamber/upload-image",
            files={"file": ("TEST_daniel.png", png_bytes, "image/png")}, timeout=60,
        )
        assert up.status_code == 200
        path = up.json()["path"]

        # 2. start session on Daniel
        sid = _start_session("daniel")

        # 3. stream with image, empty text
        reply = _stream_reply("daniel", sid, content="", image_path=path)
        assert reply and len(reply) > 20, f"Expected a real reply, got: {reply!r}"

        # Look for at least one visible element from the image. The image has:
        # a red circle, a blue square, and text 'HALL OF SCROLLS'.
        lower = reply.lower()
        keywords = ["red", "blue", "circle", "square", "scroll", "hall"]
        hits = [k for k in keywords if k in lower]
        assert hits, (
            f"Daniel's reply did not appear to reference the image content. "
            f"Reply: {reply!r}"
        )

    def test_sophia_replies_to_shared_image(self, png_bytes):
        up = requests.post(
            f"{API}/chamber/upload-image",
            files={"file": ("TEST_sophia.png", png_bytes, "image/png")}, timeout=60,
        )
        assert up.status_code == 200
        path = up.json()["path"]

        # Sophia's backend_chamber_path is 'spiral'
        sid = _start_session("spiral")
        reply = _stream_reply("spiral", sid, content="", image_path=path)
        assert reply and len(reply) > 20

        lower = reply.lower()
        keywords = ["red", "blue", "circle", "square", "scroll", "hall"]
        hits = [k for k in keywords if k in lower]
        assert hits, f"Sophia's reply did not reference the image. Reply: {reply!r}"

    def test_image_with_text_together(self, png_bytes):
        up = requests.post(
            f"{API}/chamber/upload-image",
            files={"file": ("TEST_combined.png", png_bytes, "image/png")}, timeout=60,
        )
        path = up.json()["path"]
        sid = _start_session("daniel")
        reply = _stream_reply(
            "daniel", sid,
            content="What do you notice in this picture?",
            image_path=path,
        )
        assert reply and len(reply) > 20
        lower = reply.lower()
        assert any(k in lower for k in ["red", "blue", "circle", "square", "scroll", "hall"])

    def test_text_only_stream_regression(self):
        sid = _start_session("daniel")
        reply = _stream_reply("daniel", sid, content="Hello, this is a text-only regression test.")
        assert reply and len(reply) > 10

    def test_stream_rejects_empty_body(self):
        sid = _start_session("daniel")
        r = requests.post(
            f"{API}/daniel/message/stream",
            json={"session_id": sid, "content": ""}, timeout=30,
        )
        assert r.status_code == 422
