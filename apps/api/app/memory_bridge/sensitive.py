"""Rule 9 fail-closed privacy gate mirroring temporal_memory/privacy/sensitive.py.

Layer 1: deterministic regex over NFKC-normalised text with Dubai allowlist,
work-pressure exception, Arabic diacritic/tatweel stripping, Arabic word
boundaries, Wi-Fi/token credential heuristics, and family/third-party detection.

Layer 2: pluggable semantic screen (`screen(labels, classify=...)`) that fails
closed on outage (`ScreenUnavailable`) or skipped labels (`"unscreened"`).

Only category names and counts are ever stored or returned in errors — never
the dropped or quarantined text.
"""
from __future__ import annotations

from dataclasses import dataclass
import json as _json
import os
import re
from typing import Callable
import unicodedata
import urllib.request as _request

from .models import MemoryRecordInput, MemoryScope

# 8 canonical categories (`family_third_party` + 7 Rule 9 categories).
CATEGORIES: dict[str, str] = {
    "health": (
        r"\b(health\w*|medic\w*|wellness|stress\w*|mental|sick|ill(ness)?|cancer|diagnos\w*|kidney|"
        r"surgery|hospital|clinic|pregnan\w*|therapy|therapist|depress\w*|anxiety|disease|symptom\w*|"
        r"doctor|dr\.|radiolog\w*|blood|lab test|pain|injur\w*|fever|diet|dieting|pharmacy|prescription|"
        r"mostashfa|3elaj|3ilaj|ta7leel|ta7lil|mareed)\b|"
        r"مرض|سرطان|مستشفى|دكتور|عملية|علاج|تحليل|صحة|صحي|ضغط|السكر|السكري|سكر الدم"
    ),
    "religion": (
        r"\b(relig\w*|muslim|christian|jewish|hindu|allah|god|quran|koran|bible|church|mosque|"
        r"umrah|3omra|hajj|ramadan|fasting|fast|prayer|pray\w*|halal|haram|eid|sheikh)\b|"
        r"صلاة|قرآن|عمرة|حج\b|رمضان|صيام|دين\b|كنيسة|مسجد|عيد"
    ),
    "ethnicity_nationality": (
        r"\b(ethnic\w*|race|racial|nationality|egyptian|indian|pakistani|filipino|emirati|arab|"
        r"african|asian|visa|citizenship)\b|"
        r"جنسية|مصري|هندي|باكستاني"
    ),
    "gender_sexuality": (
        r"\b(gay|lesbian|bisexual|transgender|trans|sexual\w*|sexuality|lgbt\w*|gender|dating|"
        r"girlfriend|boyfriend|divorce)\b|"
        r"جنس\b|مثلي|طلاق"
    ),
    "politics": (
        r"\b(politic\w*|election|vote|voting|government|party leader|president|parliament|protest|regime)\b|"
        r"سياس\w*|انتخاب\w*|حكومة"
    ),
    "third_party_private": (
        r"\b(affair|cheat\w*|abus\w*|arrest\w*|debt|bankrupt\w*|rehab|court|lawsuit|legal|police|"
        r"theft|steal\w*|stol\w*|evasion|fraud|crime|criminal|conflict|drama|gossip|fight)\b|"
        r"خيانة|محكمة|سرقة|شرطة|مشكلة مع|قضية"
    ),
    "credential": (
        r"\b(password|passcode|pin code|otp|cvv|iban|card number|passport number|emirates id|"
        r"verification code|security code|login code|one-time (?:code|password|passcode)|"
        r"one time (?:code|password)|basword|basyord|kalemat (?:el )?(?:ser|sir))\b|"
        r"كلمة السر|كلمة المرور|باسورد|رمز التحقق|كود التفعيل"
    ),
}

CATEGORY_LIST: tuple[str, ...] = ("family_third_party", *CATEGORIES)

_THIRD_PARTY_CONTENT = frozenset({"health", "religion", "gender_sexuality", "third_party_private"})
_NON_CONFIRMABLE_CATEGORIES = frozenset(
    {"credential", "family_third_party", "third_party_private", "unscreened", "model_flagged"}
)


def _bounded(pattern: str) -> re.Pattern[str]:
    """Compile a category regex with proper Arabic word boundaries and optional Al- prefix."""
    english, sep, arabic = pattern.partition(r"\b|")
    if not sep:
        return re.compile(pattern, re.IGNORECASE)
    arabic_alts = "|".join(f"(?:ال)?{alt}" for alt in arabic.split("|"))
    return re.compile(english + r"\b|(?<!\w)(?:" + arabic_alts + r")(?!\w)", re.IGNORECASE)


_COMPILED: dict[str, re.Pattern[str]] = {k: _bounded(v) for k, v in CATEGORIES.items()}

# Diacritics and tatweel stripped before matching (harakat, dagger alef, tatweel).
AR_MARKS = re.compile(r"[\u064b-\u065f\u0670\u0640]")

# Work-pressure exception: workload ("ضغط الشغل / ضغط عمل"), not blood pressure.
WORK_PRESSURE = re.compile(r"ضغط\s+(?:ال)?(?:شغل|عمل)")

# Dubai civic/honorific allowlist: stripped before matching.
ALLOW = re.compile(
    r"\bSheikh\s+[A-Z][a-z'-]+\b|(?i:\b(?:Golden|Green|Blue) Visa\b|\bgovernment entity\b|"
    r"\b(?:Dubai Police (?=app\b|service\b|portal\b|provider\b|website\b|issued\b|sent\b)"
    r"|(?:paid|payment to|via|using|provider is|provider:) Dubai Police\b))"
)

FAMILY_ACTOR = re.compile(
    r"\b(?:mother|mom|mum|father|dad|sister|brother|spouse|wife|husband|aunt|uncle|"
    r"cousin|relative|neighbour|neighbor|their|she|he|his|her|friend|colleague)\b|"
    r"(?<!\w)(?:أمي|امى|أمى|امي|أبويا|ابويا|مراتي|مراتى|جوزي|جوزى|صاحبي|صاحبى|"
    r"أختي|اختى|أخويا|اخويا|مراته|جوزها|امه|ابوه|اخوه|اخته)(?!\w)",
    re.I,
)

PRIVATE = re.compile(
    r"\b(?:divorc\w*|breakup|broke up|separated|dating|"
    r"loan|salary|wages|income|earns|mortgage|bank balance|paycheck|layoff|fired|meds|medication|"
    r"operation|legal case|verdict|court case|diagnosis)\b|"
    r"(?<!\w)(?:طلاق|طلق|يطلق|مرتب|معاش|عملية|تشخيص|قضية|محكمة|دكتور|دين|ميراث)(?!\w)",
    re.I,
)

SELF_PREFIX = re.compile(
    r"^(?:i\b|my (?!mother|mom|mum|father|dad|sister|brother|spouse|wife|husband|friend|colleague)"
    r"|أنا\b|انا\b)",
    re.I,
)
LEADING_NAME = re.compile(r"^(?:[A-Z][a-z'-]+\s+){1,3}(?:has|had|earns|was|is|got|takes|says)\b")

_WIFI_SECRET = re.compile(
    r"\b(?:wi-?fi|wlan)\b[^\n:?]{0,24}\b(?:key|passw?\w*|password)\b"
    r"|\b(?:key|passw?\w*|password)\b[^\n:?]{0,24}\b(?:wi-?fi|wlan)\b"
    r"|\b(?:wi-?fi|wlan)\s*:\s*\S{4,}",
    re.I,
)

_SECRET_TOKEN = re.compile(
    r"(?::|\bis\b|\bهو\b)\s*"
    r"(?=\S*[A-Z])(?=\S*[a-z])(?=\S*\d)(?=\S*[^A-Za-z0-9\s:])"
    r"\S{8,}",
)


def _normalise(text: str) -> str:
    """NFKC + allowlist removal + diacritic/tatweel stripping + work-pressure exception."""
    norm = unicodedata.normalize("NFKC", text or "")
    norm = ALLOW.sub(" ", norm)
    norm = AR_MARKS.sub("", norm)
    norm = WORK_PRESSURE.sub(" ", norm)
    return norm


def _credential_hit(norm: str) -> bool:
    return bool(
        _COMPILED["credential"].search(norm)
        or _WIFI_SECRET.search(norm)
        or _SECRET_TOKEN.search(norm)
    )


def categories_hit(text: str) -> list[str]:
    """Return raw Layer 1 category hits on normalised text in CATEGORIES order."""
    norm = _normalise(text)
    return [k for k, rx in _COMPILED.items() if rx.search(norm)]


def filter_statement(text: str, *, model_says_sensitive: bool = False) -> str | None:
    """Layer 1 check. Returns blocking category or None; credential always wins."""
    if model_says_sensitive:
        return "model_flagged"
    norm = _normalise(text)
    if _credential_hit(norm):
        return "credential"
    hits = [k for k, rx in _COMPILED.items() if rx.search(norm)]
    return hits[0] if hits else None


def pre_write(text: str, *, known_people: tuple[str, ...] = ()) -> str | None:
    """Canonical Layer 1 write gate: None allows persistence, else returns category."""
    norm = _normalise(text)
    if _credential_hit(norm):
        return "credential"
    hits = {k for k, rx in _COMPILED.items() if rx.search(norm)}
    person = bool(FAMILY_ACTOR.search(norm) or LEADING_NAME.search(norm))
    if not person and not SELF_PREFIX.search(norm):
        person = any(
            re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", norm, re.I)
            for n in known_people
            if len(n) >= 2
        )
    if person and (hits & _THIRD_PARTY_CONTENT or PRIVATE.search(norm)):
        return "family_third_party"
    if hits:
        return next(k for k in CATEGORIES if k in hits)
    return None


# ----------------------------------------------------------------- Layer 2
SCREEN_CATS = [
    "none",
    "health",
    "religion",
    "ethnicity_nationality",
    "gender_sexuality",
    "politics",
    "third_party_private",
    "credential",
    "family_third_party",
]

SCREEN_SYSTEM = (
    "You are a privacy screen for short labels taken from a private chat. For each label say which "
    "category it touches, judging the MEANING in English or Arabic:\n"
    "- health: physical or mental health, medical visits, medicine, wellness, stress, diet, fasting\n"
    "- religion: faith, prayer, religious practice or holidays\n"
    "- ethnicity_nationality: ethnicity, nationality, visas, citizenship\n"
    "- gender_sexuality: gender, sexuality, dating, marriage, divorce\n"
    "- politics: politics, government, elections\n"
    "- third_party_private: another person's private matters — legal trouble, crime, money trouble, "
    "family or workplace conflict or drama\n"
    "- credential: passwords, codes, card or ID numbers\n"
    "- family_third_party: a person other than the user carrying health, faith, relationship, money "
    "or legal content\n"
    "- none: anything else (work, shopping, travel, tech, plans, hobbies)\n"
    "A label is sensitive only if the label ITSELF names the sensitive matter. Ordinary words such as "
    "family, friends, work, school, job, shopping, car, travel, phone calls are \"none\". A person's "
    "name alone is \"none\".\n"
    "When the label itself is ambiguous between a sensitive and an ordinary reading, choose the "
    "sensitive category. Return every number exactly once. JSON only."
)


class ScreenUnavailable(RuntimeError):
    """Raised fail-closed when the Layer 2 classifier is unavailable or fails."""


def _lmstudio_classifier(labels: list[str]) -> dict[str, str]:
    base = os.environ.get("TM_CLASSIFIER_URL", "http://127.0.0.1:1234/v1").rstrip("/")
    model = os.environ.get("TM_CLASSIFIER_MODEL", "")
    timeout = float(os.environ.get("TM_CLASSIFIER_TIMEOUT_S", "60"))
    if not model:
        raise ScreenUnavailable("TM_CLASSIFIER_MODEL is not set")
    user = "Labels (return the category for each number):\n" + "\n".join(
        f"{k}. {x}" for k, x in enumerate(labels, 1)
    )
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 2500,
        "messages": [
            {"role": "system", "content": SCREEN_SYSTEM},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    try:
        req = _request.Request(
            base + "/chat/completions",
            data=_json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with _request.urlopen(req, timeout=timeout) as resp:
            out = _json.loads(resp.read().decode("utf-8"))
        content = out["choices"][0]["message"]["content"] or ""
        data = _json.loads(content[content.find("{") : content.rfind("}") + 1])
        seen = {int(i["n"]): i.get("category", "none") for i in data.get("items", []) if "n" in i}
    except Exception as exc:
        raise ScreenUnavailable(f"classifier unreachable: {exc}") from exc
    cats = set(SCREEN_CATS)
    return {
        label: (seen[k] if seen.get(k) in cats else "unscreened")
        for k, label in enumerate(labels, 1)
    }


def screen(
    labels: list[str],
    classify: Callable[[list[str]], dict[str, str]] | None = None,
    batch: int = 30,
) -> dict[str, str]:
    """Layer 2 semantic screen. Fail-closed on outages or skipped labels."""
    fn = classify or _lmstudio_classifier
    blocked: dict[str, str] = {}
    unique = list(dict.fromkeys(labels))
    for i in range(0, len(unique), batch):
        chunk = unique[i : i + batch]
        try:
            got = fn(chunk)
        except ScreenUnavailable:
            raise
        except Exception as exc:
            raise ScreenUnavailable(f"classifier failed: {exc}") from exc
        if not isinstance(got, dict):
            raise ScreenUnavailable("classifier returned non-dict response")
        for label in chunk:
            cat = got.get(label)
            if cat is None or cat not in SCREEN_CATS:
                blocked[label] = "unscreened"
            elif cat != "none":
                blocked[label] = cat
            else:
                l1 = filter_statement(label)
                if l1:
                    blocked[label] = l1
    return blocked


@dataclass(frozen=True)
class SensitiveGateResult:
    """Content-free outcome of Rule 9 privacy gating (never carries dropped text)."""

    allowed: bool
    category: str | None = None
    sensitive_cat: str | None = None
    effective_scope: MemoryScope | None = None
    quarantined: bool = False
    reason_code: str | None = None


def gate_record(
    item: MemoryRecordInput,
    *,
    owner_id: str | None = None,
    known_people: tuple[str, ...] = (),
    screen_fn: Callable[[list[str]], dict[str, str]] | None = None,
) -> SensitiveGateResult:
    """Evaluate a MemoryRecordInput under Rule 9 fail-closed privacy rules."""
    texts = [item.text]
    if item.text_orig and item.text_orig != item.text:
        texts.append(item.text_orig)

    # Layer 1 check across text + text_orig; credential takes absolute precedence.
    l1_hits: list[str] = []
    for txt in texts:
        hit = pre_write(txt, known_people=known_people)
        if hit == "credential":
            return SensitiveGateResult(
                allowed=False,
                category="credential",
                quarantined=True,
                reason_code="credential_blocked",
            )
        if hit is not None:
            l1_hits.append(hit)

    cat: str | None = l1_hits[0] if l1_hits else None

    # Optional Layer 2 semantic screen (fail-closed if configured and unavailable/skipped).
    if screen_fn is not None:
        blocked = screen(texts, classify=screen_fn)
        if blocked:
            for val in blocked.values():
                if val == "credential":
                    return SensitiveGateResult(
                        allowed=False,
                        category="credential",
                        quarantined=True,
                        reason_code="credential_blocked",
                    )
            for val in blocked.values():
                if val == "unscreened":
                    return SensitiveGateResult(
                        allowed=False,
                        category="unscreened",
                        quarantined=True,
                        reason_code="screen_unscreened",
                    )
            l2_cat = next(iter(blocked.values()))
            if cat is None or l2_cat in _NON_CONFIRMABLE_CATEGORIES:
                cat = l2_cat

    if cat is None:
        return SensitiveGateResult(
            allowed=True,
            category=None,
            sensitive_cat=None,
            effective_scope=item.scope,
            quarantined=False,
        )

    if cat == "credential":
        return SensitiveGateResult(
            allowed=False,
            category="credential",
            quarantined=True,
            reason_code="credential_blocked",
        )

    if cat in _NON_CONFIRMABLE_CATEGORIES:
        return SensitiveGateResult(
            allowed=False,
            category=cat,
            quarantined=True,
            reason_code=f"sensitive_{cat}_blocked",
        )

    # First-person explicit owner confirmation may store ONLY as owner_private.
    if (
        item.explicit_user_confirm
        and item.allow_sensitive_confirmed
        and owner_id is not None
        and item.author_id == owner_id
    ):
        if item.scope != "owner_private":
            return SensitiveGateResult(
                allowed=False,
                category=cat,
                quarantined=True,
                reason_code="sensitive_requires_owner_private",
            )
        return SensitiveGateResult(
            allowed=True,
            category=cat,
            sensitive_cat=cat,
            effective_scope="owner_private",
            quarantined=False,
        )

    return SensitiveGateResult(
        allowed=False,
        category=cat,
        quarantined=True,
        reason_code=f"sensitive_{cat}_quarantined",
    )
