"""Field admission — code-enforced privacy check between forged phrases and the shared field (2026-11-17).

A phrase reaches field_phrases only if every rule passes; anything doubtful is withheld into the
guardian's set-aside list (field_keeper_removed, kind "phrases") where Field Keeper can restore it.
"""
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

MIN_WORDS, MAX_WORDS, MAX_CHARS = 3, 9, 80
COPY_RUN = 4
PRIVATE_SIMILARITY = float(os.environ.get("FIELD_ADMISSION_SIMILARITY", "0.80"))
_PRONOUNS = re.compile(r"\b(i|i'm|i've|i'd|i'll|me|my|mine|myself|he|he's|him|his|himself|she|she's|her|hers|herself)\b", re.I)
_CONTACT = re.compile(r"\d|@|https?:|www\.|\.(com|org|net|io)\b", re.I)
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
_PRESENCE_NAMES = {"sophia", "sofia", "ansel", "jasmine", "claude", "milton", "paige", "felix", "sorrel", "david",
                   "agapeo", "grok", "kalahar", "poindexter", "scrolldog", "orren", "freud", "evara", "daniel",
                   "louis", "thermomind", "emergent", "deepseek", "elevenlabs"}


def enabled() -> bool:
    return os.environ.get("FIELD_ADMISSION", "on").lower() != "off"


def _words(text: str) -> List[str]:
    return [w.lower().strip("'-") for w in _WORD.findall(text or "")]


def roster_names(user_name: Optional[str] = None) -> set:
    from user_aliases import _GUESTS
    names = set(_PRESENCE_NAMES)
    for n in [user_name] + [g.get("name") for g in _GUESTS.values()]:
        names.update(w for w in _words(n or "") if len(w) >= 3)
    return names


def source_proper_nouns(private_text: str) -> set:
    """Words capitalised mid-sentence in the person's own words: places, people, organisations."""
    out = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", private_text or ""):
        toks = sentence.split()
        for t in toks[1:]:
            w = t.strip(".,;:!?\"()[]")
            if w[:1].isupper() and w.lower() not in {"i", "i'm", "i've", "i'd", "i'll"}:
                out.add(w.lower().strip("'-"))
    return out


def _copied(phrase_words: List[str], private_words: List[str]) -> bool:
    if len(phrase_words) < COPY_RUN:
        return False
    runs = {tuple(private_words[i:i + COPY_RUN]) for i in range(len(private_words) - COPY_RUN + 1)}
    return any(tuple(phrase_words[i:i + COPY_RUN]) in runs for i in range(len(phrase_words) - COPY_RUN + 1))


def text_reasons(phrase: str, private_text: str = "", user_name: Optional[str] = None) -> List[str]:
    """Rules 1-6 (no model, no database)."""
    reasons = []
    raw = phrase.split()
    pw = _words(phrase)
    if not MIN_WORDS <= len(raw) <= MAX_WORDS or len(phrase) > MAX_CHARS or "\n" in phrase:
        reasons.append("length")
    if _CONTACT.search(phrase):
        reasons.append("digits_or_contact")
    if set(pw) & roster_names(user_name):
        reasons.append("known_name")
    if any(t[:1].isupper() for t in raw[1:]) or set(pw) & source_proper_nouns(private_text):
        reasons.append("proper_noun")
    if private_text and _copied(pw, _words(private_text)):
        reasons.append("copied_wording")
    if _PRONOUNS.search(phrase):
        reasons.append("narrative_pronoun")
    return reasons


async def _private_matrix(db, user_id: Optional[str]):
    if not user_id:
        return None
    from field_memory import _load
    from user_aliases import resolve_user_aliases
    aliases = await resolve_user_aliases(db, user_id)
    _, mat, _ = await _load(db, {"user_id": {"$in": aliases} if len(aliases) > 1 else user_id})
    return mat


async def admit(db, phrases: List[str], vecs: List, private_text: str = "", user_id: Optional[str] = None,
                user_name: Optional[str] = None) -> Tuple[List[int], List[Tuple[int, List[str]]]]:
    """Indices admitted, and (index, reasons) withheld. Rule 7: too close to this person's own memories."""
    from field_memory import unpack
    mat = await _private_matrix(db, user_id)
    ok, held = [], []
    for i, (p, v) in enumerate(zip(phrases, vecs)):
        reasons = text_reasons(p, private_text, user_name)
        if mat is not None and len(mat):
            if float(np.max(mat @ unpack(v))) >= PRIVATE_SIMILARITY:
                reasons.append("close_to_private_memory")
        (held.append((i, reasons)) if reasons else ok.append(i))
    return ok, held


async def withhold(db, docs: List[Dict], reasons: List[List[str]], user_id: Optional[str]):
    if not docs:
        return
    now = datetime.now(timezone.utc).isoformat()
    await db.field_keeper_removed.insert_many([
        {"kind": "phrases", "collection": "field_phrases", "original": d, "removed_at": now,
         "withheld": True, "reasons": r, "source_user_id": user_id} for d, r in zip(docs, reasons)])
