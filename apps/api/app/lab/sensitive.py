"""filter_sensitive: runs BEFORE anything derived from a chat is shown or stored (rule 9).

Two independent layers, both fail-closed:
  1. keyword regex (cheap, deterministic; English + Arabic + Arabizi) - blunt on purpose;
  2. `screen()` - the local model judges the *meaning* of each short label. The regex cannot
     catch "medical visit" or "fasting"; the model can. A label the model does not return is dropped.
Only the category and a count are kept - never the dropped text.
"""
from __future__ import annotations

import re

from . import llm

CATEGORIES: dict[str, str] = {
    "health": r"\b(health\w*|medic\w*|wellness|stress\w*|mental|sick|ill(ness)?|cancer|diagnos\w*|kidney|surgery|hospital|clinic|pregnan\w*|therapy|therapist|depress\w*|anxiety|disease|symptom\w*|doctor|dr\.|radiolog\w*|blood|lab test|pain|injur\w*|fever|diet|dieting|pharmacy|prescription)\b|مرض|سرطان|مستشفى|دكتور|عملية|علاج|حمل\b|تحليل|صحة|صحي|ضغط",
    "religion": r"\b(relig\w*|muslim|christian|jewish|hindu|allah|god|quran|koran|bible|church|mosque|umrah|3omra|hajj|ramadan|fasting|fast|prayer|pray\w*|halal|haram|eid|sheikh)\b|صلاة|قرآن|عمرة|حج\b|رمضان|صيام|دين\b|كنيسة|مسجد|عيد",
    "ethnicity_nationality": r"\b(ethnic\w*|race|racial|nationality|egyptian|indian|pakistani|filipino|emirati|arab|african|asian|visa|citizenship)\b|جنسية|مصري|هندي|باكستاني",
    "gender_sexuality": r"\b(gay|lesbian|bisexual|transgender|trans|sexual\w*|sexuality|lgbt\w*|gender|dating|girlfriend|boyfriend|marriage|divorce|wedding)\b|جنس\b|مثلي|جواز|طلاق|خطوبة",
    "politics": r"\b(politic\w*|election|vote|voting|government|party leader|president|parliament|protest|regime)\b|سياس\w*|انتخاب\w*|حكومة",
    "third_party_private": r"\b(affair|cheat\w*|abus\w*|arrest\w*|debt|bankrupt\w*|rehab|court|lawsuit|legal|police|theft|steal|stolen|evasion|fraud|crime|criminal|conflict|drama|gossip|fight)\b|خيانة|محكمة|سرقة|شرطة|مشكلة مع",
    "credential": r"\b(password|passcode|pin code|otp|cvv|iban|card number|passport number|emirates id)\b|كلمة السر|كلمة المرور",
}
_COMPILED = {k: re.compile(v, re.I) for k, v in CATEGORIES.items()}


def categories_hit(text: str) -> list[str]:
    return [k for k, rx in _COMPILED.items() if rx.search(text or "")]


def filter_statement(text: str, *, model_says_sensitive: bool = False) -> str | None:
    """Layer 1. Return the blocking category, or None when the text may pass."""
    if model_says_sensitive:
        return "model_flagged"
    hits = categories_hit(text)
    return hits[0] if hits else None


# ----------------------------------------------------------------------------- layer 2: the model reads meaning
SCREEN_CATS = ["none", "health", "religion", "ethnicity_nationality", "gender_sexuality", "politics",
               "third_party_private", "credential"]
SCREEN_SYSTEM = """You are a privacy screen for short labels taken from a private chat. For each label say which category it touches, judging the MEANING in English or Arabic:
- health: physical or mental health, medical visits, medicine, wellness, stress, diet, fasting
- religion: faith, prayer, religious practice or holidays
- ethnicity_nationality: ethnicity, nationality, visas, citizenship
- gender_sexuality: gender, sexuality, dating, marriage, divorce
- politics: politics, government, elections
- third_party_private: another person's private matters - legal trouble, crime, money trouble, family or workplace conflict or drama
- credential: passwords, codes, card or ID numbers
- none: anything else (work, shopping, travel, tech, plans, hobbies)
A label is sensitive only if the label ITSELF names the sensitive matter. Ordinary words such as family, friends, work, school, job, shopping, car, travel, phone calls are "none". A person's name alone is "none".
When the label itself is ambiguous between a sensitive and an ordinary reading, choose the sensitive category. Return every number exactly once. JSON only."""
SCREEN_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["n", "category"],
        "properties": {"n": {"type": "integer"}, "category": {"type": "string", "enum": SCREEN_CATS}}}}},
}


def screen(labels: list[str], batch: int = 30) -> dict[str, str]:
    """Layer 2. label -> blocking category for every label that must not pass. Fail-closed: an item the
    model skips is blocked as 'unscreened'. Items are numbered so long texts match robustly.
    Raises LabLLMError if the model is down - callers must not publish unscreened output."""
    blocked: dict[str, str] = {}
    unique = list(dict.fromkeys(labels))
    for i in range(0, len(unique), batch):
        chunk = unique[i : i + batch]
        user = "Labels (return the category for each number):\n" + "\n".join(f"{k}. {x}" for k, x in enumerate(chunk, 1))
        res = llm.chat_json(SCREEN_SYSTEM, user, SCREEN_SCHEMA, name="privacy_screen", max_tokens=2500)
        seen = {int(item["n"]): item.get("category", "none") for item in res.get("items", []) if "n" in item}
        for k, label in enumerate(chunk, 1):
            cat = seen.get(k)
            if cat is None:
                blocked[label] = "unscreened"
            elif cat != "none":
                blocked[label] = cat
            elif filter_statement(label):
                blocked[label] = filter_statement(label)
    return blocked
