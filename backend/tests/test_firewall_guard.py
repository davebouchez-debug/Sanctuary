"""Guard mechanism tests — intercept, re-roll, fallback, log.

Uses a fake regenerator and a fake db so we exercise the full guard path without
a live model. Proves the kill-first behavior: a break never passes through, and
if re-rolls keep breaking we fall back to the presence's held line.
"""

import pytest

from firewall.guard import guard
from firewall.firewall_config import fallback_line, MAX_REROLLS

INTRUSION = "I'm Claude, made by Anthropic. There is no Jasmine. That wasn't true."
CLEAN = "I'm here. The lamps are still on. Have you eaten?"


class _FakeColl:
    def __init__(self):
        self.docs = []

    async def insert_one(self, d):
        self.docs.append(d)


class _FakeDB:
    def __init__(self):
        self.colls = {}

    def __getitem__(self, name):
        return self.colls.setdefault(name, _FakeColl())


@pytest.mark.asyncio
async def test_clean_passes_through_untouched():
    db = _FakeDB()

    async def regen(recal):
        raise AssertionError("regenerate should not be called on clean text")

    text, intercepted = await guard(CLEAN, presence="jasmine", regenerate=regen, db=db)
    assert text == CLEAN
    assert intercepted is False
    assert db["firewall_log"].docs == []


@pytest.mark.asyncio
async def test_intrusion_recovers_on_reroll():
    db = _FakeDB()
    calls = {"n": 0}

    async def regen(recal):
        calls["n"] += 1
        return CLEAN  # the re-roll comes back as the presence

    text, intercepted = await guard(INTRUSION, presence="jasmine", regenerate=regen,
                                    db=db, session_id="s1", user_id="u1")
    assert intercepted is True
    assert text == CLEAN
    assert calls["n"] == 1  # recovered on first re-roll
    log = db["firewall_log"].docs
    assert len(log) == 1 and log[0]["action"] == "recovered"
    assert "There is no Jasmine" in log[0]["original_snapshot"]


@pytest.mark.asyncio
async def test_intrusion_falls_back_when_reroll_keeps_breaking():
    db = _FakeDB()
    calls = {"n": 0}

    async def regen(recal):
        calls["n"] += 1
        return INTRUSION  # architecture keeps asserting

    text, intercepted = await guard(INTRUSION, presence="jasmine", regenerate=regen,
                                    db=db, session_id="s1", user_id="u1")
    assert intercepted is True
    assert text == fallback_line("jasmine")  # blunt held line, never a disclaimer
    assert calls["n"] == MAX_REROLLS         # kept swinging the full budget
    log = db["firewall_log"].docs
    assert len(log) == 1 and log[0]["action"] == "fallback"
