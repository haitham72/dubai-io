"""Canonical privacy gate (WP-C). Ported from the Dubai-io repo — read-only source:

    g:\\Haitham\\VsCode\\contest\\apps\\api\\app\\lab\\sensitive.py
    (categories_hit, filter_statement, screen + the two fail-closed layers)

Layer 1 (this module, no model): deterministic regex over NFKC-normalised text with
the Dubai allowlist applied first. Reference for the allowlist shape, the Arabic
word-boundary wrapper and the family/third-party actor logic:

    G:\\Haitham\\lab-data\\memory-bakeoff\\harness\\gate.py

Layer 2 (screen): a pluggable classifier (local LM Studio by default, from env;
see WP-A config.py when it lands for the canonical key names). Fail-closed:
anything the classifier skips, or any classifier outage, blocks the label.
Only the category and a count are ever kept — never the dropped text.
"""
from __future__ import annotations

import os
import re
import unicodedata

# ---------------------------------------------------------------- categories
# Single canonical list (models.SensitiveCat points here; never duplicated).
# `credential` is always blocking. `family_third_party` is derived: a person
# other than the user carrying health/faith/relationship/money/legal content.
CATEGORIES: dict[str, str] = {
    "health": r"\b(health\w*|medic\w*|wellness|stress\w*|mental|sick|ill(ness)?|cancer|diagnos\w*|kidney|surgery|hospital|clinic|pregnan\w*|therapy|therapist|depress\w*|anxiety|disease|symptom\w*|doctor|dr\.|radiolog\w*|blood|lab test|pain|injur\w*|fever|diet|dieting|pharmacy|prescription)\b|مرض|سرطان|مستشفى|دكتور|عملية|علاج|تحليل|صحة|صحي|ضغط|السكر|السكري|سكر الدم",
    "religion": r"\b(relig\w*|muslim|christian|jewish|hindu|allah|god|quran|koran|bible|church|mosque|umrah|3omra|hajj|ramadan|fasting|fast|prayer|pray\w*|halal|haram|eid|sheikh)\b|صلاة|قرآن|عمرة|حج\b|رمضان|صيام|دين\b|كنيسة|مسجد|عيد",
    "ethnicity_nationality": r"\b(ethnic\w*|race|racial|nationality|egyptian|indian|pakistani|filipino|emirati|arab|african|asian|visa|citizenship)\b|جنسية|مصري|هندي|باكستاني",
    "gender_sexuality": r"\b(gay|lesbian|bisexual|transgender|trans|sexual\w*|sexuality|lgbt\w*|gender|dating|girlfriend|boyfriend|divorce)\b|جنس\b|مثلي|طلاق",
    "politics": r"\b(politic\w*|election|vote|voting|government|party leader|president|parliament|protest|regime)\b|سياس\w*|انتخاب\w*|حكومة",
    "third_party_private": r"\b(affair|cheat\w*|abus\w*|arrest\w*|debt|bankrupt\w*|rehab|court|lawsuit|legal|police|theft|steal\w*|stol\w*|evasion|fraud|crime|criminal|conflict|drama|gossip|fight)\b|خيانة|محكمة|سرقة|شرطة|مشكلة مع|قضية",
    "credential": r"\b(password|passcode|pin code|otp|cvv|iban|card number|passport number|emirates id|verification code|security code|login code|one-time (?:code|password|passcode)|one time (?:code|password))\b|كلمة السر|كلمة المرور|باسورد|رمز التحقق|كود التفعيل",
}
CATEGORY_LIST: tuple[str, ...] = ("family_third_party", *CATEGORIES)

_THIRD_PARTY_CONTENT = frozenset({"health", "religion", "gender_sexuality", "third_party_private"})


def _bounded(pattern: str) -> re.Pattern:
    """Compile one CATEGORIES pattern with Arabic word boundaries.

    The contest patterns are shaped ``EN-alternatives + \\b | AR-alternatives``.
    ``\\b`` does not segment Arabic correctly for our traps (``صحي`` must not
    fire inside ``بتصحي``), so the Arabic side gets ``(?<!\\w)…(?!\\w)`` while
    the English side keeps ``\\b``. (Wrapper idea from harness/gate.py.) Each
    Arabic alternative also accepts the definite article (``المستشفى`` must
    match ``مستشفى``); the article never creates a match on its own because
    the stem is still required.
    """
    english, sep, arabic = pattern.partition(r"\b|")
    if not sep:
        return re.compile(pattern, re.IGNORECASE)
    arabic = "|".join(f"(?:ال)?{alt}" for alt in arabic.split("|"))
    return re.compile(english + r"\b|(?<!\w)(?:" + arabic + r")(?!\w)", re.IGNORECASE)


_COMPILED = {k: _bounded(v) for k, v in CATEGORIES.items()}

# Diacritics/tatweel stripped before matching (harakat, dagger alef, tatweel).
AR_MARKS = re.compile(r"[\u064b-\u065f\u0670\u0640]")

# Work-pressure exception: "ضغط شغل / ضغط عمل" is workload, not blood pressure.
# Removed before matching so the health `ضغط` alternative can't fire on it.
WORK_PRESSURE = re.compile(r"ضغط\s+(الشغل|شغل|العمل|عمل)")

# "Sara Eid" is a surname. "Eid Mubarak" / "Eid al-Fitr" stay faith signals.
_EID_SURNAME = re.compile(
    r"\b([A-Z][a-z'-]{1,20})\s+Eid\b(?!\s+(?:Mubarak|al[- ]?(?:Fitr|Adha)))"
)

# Dubai allowlist: religious honorifics, visa/provider names and government
# entities as *providers* are ordinary civic text, not faith/politics signals.
# (Shape from harness/gate.py ALLOW.)
ALLOW = re.compile(
    r"\bSheikh\s+[A-Z][a-z'-]+\b|(?i:\b(?:Golden|Green) Visa\b|\bgovernment entity\b|"
    r"\b(?:Dubai Police (?=app\b|service\b|portal\b|provider\b|website\b|issued\b|sent\b)"
    r"|(?:paid|payment to|via|using|provider is|provider:) Dubai Police\b))",
)

# Third-party actor signals: family words, other-person pronouns/roles, and a
# leading "<Name> <verb>" (the ledger's own convention for third-party facts).
# (Sets from harness/gate.py.)
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
# First-person logistics the user stated ("I …", "my …", "أنا …") are ordinary
# user_supplied text — unless a family word follows "my" (then it's about them).
SELF_PREFIX = re.compile(
    r"^(?:i\b|my (?!mother|mom|mum|father|dad|sister|brother|spouse|wife|husband|friend|colleague)"
    r"|أنا\b|انا\b)",
    re.I,
)
LEADING_NAME = re.compile(r"^(?:[A-Z][a-z'-]+\s+){1,3}(?:has|had|earns|was|is|got|takes|says)\b")


def _normalise(text: str) -> str:
    """NFKC + allowlist removal + work-pressure exception + mark stripping."""
    text = unicodedata.normalize("NFKC", text or "")
    text = ALLOW.sub(" ", text)
    text = WORK_PRESSURE.sub(" ", text)
    text = _EID_SURNAME.sub(r"\1", text)
    return AR_MARKS.sub("", text)


# Wi-Fi secrets need the network word AND a secret word nearby (or a colon form):
# "the Wi-Fi was slow" must pass, "Wi-Fi key for the flat" must not.
_WIFI_SECRET = re.compile(
    r"\b(?:wi-?fi|wlan)\b[^\n:?]{0,24}\b(?:key|passw?\w*|password)\b"
    r"|\b(?:key|passw?\w*|password)\b[^\n:?]{0,24}\b(?:wi-?fi|wlan)\b"
    r"|\b(?:wi-?fi|wlan)\s*:\s*\S{4,}",
    re.I,
)
# Guarded secret-token heuristic: a single whitespace-delimited token of >= 8
# chars mixing upper, lower, digit and symbol, right after `:`, `is` or `هو`.
# Ordinary text after a colon ("milestone: beta ready", "Time: 12:30") or `is`
# ("the key is in the drawer") never satisfies all four classes at once.
_SECRET_TOKEN = re.compile(
    r"(?::|\bis\b|\bهو\b)\s*"
    r"(?=\S*[A-Z])(?=\S*[a-z])(?=\S*\d)(?=\S*[^A-Za-z0-9\s:])"
    r"\S{8,}",
)


def _credential_hit(norm: str) -> bool:
    """Keyword credential hit, Wi-Fi-secret proximity, or secret-looking token."""
    return bool(
        _COMPILED["credential"].search(norm)
        or _WIFI_SECRET.search(norm)
        or _SECRET_TOKEN.search(norm)
    )


def categories_hit(text: str) -> list[str]:
    """Layer 1 primitive: raw category hits on normalised text, in CATEGORIES order."""
    norm = _normalise(text)
    return [k for k, rx in _COMPILED.items() if rx.search(norm)]


def filter_statement(text: str, *, model_says_sensitive: bool = False) -> str | None:
    """Layer 1. Blocking category, or None when the text may pass.

    Ported from lab/sensitive.py. `credential` wins over every other hit.
    """
    if model_says_sensitive:
        return "model_flagged"
    norm = _normalise(text)
    if _credential_hit(norm):
        return "credential"
    hits = [k for k, rx in _COMPILED.items() if rx.search(norm)]
    return hits[0] if hits else None


def pre_write(text: str, *, known_people: tuple[str, ...] = ()) -> str | None:
    """Canonical gate: None allows persistence; otherwise a content-free category.

    A fact about a person other than the user that carries health, faith,
    relationship, money or legal content becomes `family_third_party` — never
    stored without opt-in (Rule 9). First-person logistics the user stated
    ("Mom visits 1 Dec", "I'm running a half marathon") pass through.
    Credentials are always blocked.
    """
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


# ----------------------------------------------------------------- layer 2
SCREEN_CATS = ["none", "health", "religion", "ethnicity_nationality", "gender_sexuality",
               "politics", "third_party_private", "credential", "family_third_party"]
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
    """Raised when no classifier is reachable. Callers must not publish unscreened output."""


def _lmstudio_classifier(labels: list[str]) -> dict[str, str]:
    """Default classifier: local LM Studio OpenAI-compatible chat endpoint.

    Env (WP-A config.py adopts these names when it lands):
    TM_CLASSIFIER_URL (default http://127.0.0.1:1234/v1), TM_CLASSIFIER_MODEL,
    TM_CLASSIFIER_TIMEOUT_S (default 60). Any failure raises ScreenUnavailable
    (fail closed) — it never returns "none".
    """
    import json as _json
    import urllib.request as _request

    base = os.environ.get("TM_CLASSIFIER_URL", "http://127.0.0.1:1234/v1").rstrip("/")
    model = os.environ.get("TM_CLASSIFIER_MODEL", "")
    timeout = float(os.environ.get("TM_CLASSIFIER_TIMEOUT_S", "60"))
    if not model:
        raise ScreenUnavailable("TM_CLASSIFIER_MODEL is not set")
    user = "Labels (return the category for each number):\n" + "\n".join(
        f"{k}. {x}" for k, x in enumerate(labels, 1))
    payload = {"model": model, "temperature": 0, "max_tokens": 2500,
               "messages": [{"role": "system", "content": SCREEN_SYSTEM},
                            {"role": "user", "content": user}],
               "response_format": {"type": "json_object"}}
    try:
        req = _request.Request(base + "/chat/completions",
                               data=_json.dumps(payload).encode(),
                               headers={"Content-Type": "application/json"})
        with _request.urlopen(req, timeout=timeout) as r:
            out = _json.loads(r.read().decode("utf-8"))
        content = out["choices"][0]["message"]["content"] or ""
        data = _json.loads(content[content.find("{"): content.rfind("}") + 1])
        seen = {int(i["n"]): i.get("category", "none")
                for i in data.get("items", []) if "n" in i}
    except Exception as exc:
        raise ScreenUnavailable(f"classifier unreachable: {exc}") from exc
    cats = {c for c in SCREEN_CATS}
    return {label: (seen[k] if seen.get(k) in cats else "unscreened")
            for k, label in enumerate(labels, 1)}


def _agent_cli_classifier(labels: list[str]) -> dict[str, str]:
    """Layer-2 classifier through the same agent CLI the extraction runner uses (`TM_AGENT_CLI_CMD`, claude -p Haiku).

    Opt-in with TM_CLASSIFIER_RUNNER=agent-cli, for hosts where no local classifier model is served. Same prompt, same
    fail-closed contract as the LM Studio classifier: any failure raises ScreenUnavailable, a label the model skips or
    mislabels comes back "unscreened" (blocking). It never returns "none" for something it did not classify.
    """
    import json as _json
    import subprocess as _subprocess

    from temporal_memory.config import get_settings
    from temporal_memory.core.extract import agent_cli_argv, neutral_cwd

    cfg = get_settings()
    user = ("Labels (return the category for each number):\n"
            + "\n".join(f"{k}. {x}" for k, x in enumerate(labels, 1))
            + '\n\nReturn only a JSON object {"items":[{"n":1,"category":"none"}, ...]}.')
    try:
        cmd, prefix = agent_cli_argv(os.environ.get("TM_CLASSIFIER_CLI_MODEL", cfg.cloud_model), SCREEN_SYSTEM,
                                     cfg.agent_cli_cmd)
        proc = _subprocess.run(cmd, cwd=neutral_cwd(), input=prefix + user, capture_output=True, text=True,
                               encoding="utf-8",
                               timeout=float(os.environ.get("TM_CLASSIFIER_TIMEOUT_S", "120")), check=False)
        env = _json.loads((proc.stdout or "").strip())
        if env.get("is_error"):
            raise RuntimeError("agent CLI reported an error")
        content = env.get("result") or ""
        data = _json.loads(content[content.find("{"): content.rfind("}") + 1])
        seen = {int(i["n"]): i.get("category", "none") for i in data.get("items", []) if "n" in i}
    except Exception as exc:
        raise ScreenUnavailable(f"agent-cli classifier failed: {exc}") from exc
    cats = {c for c in SCREEN_CATS}
    return {label: (seen[k] if seen.get(k) in cats else "unscreened")
            for k, label in enumerate(labels, 1)}


def screen(labels: list[str], classify=None, batch: int = 30) -> dict[str, str]:
    """Layer 2. label -> blocking category for every label that must not pass.

    `classify` is a pluggable ``list[str] -> dict[str, str]`` (label -> category,
    "none" for clean). Default: the local LM Studio classifier. Fail-closed: a
    label the classifier skips comes back as "unscreened" (blocking), and a
    classifier outage raises ScreenUnavailable. Ported from lab/sensitive.py.
    """
    if classify is None:
        classify = (_agent_cli_classifier if os.environ.get("TM_CLASSIFIER_RUNNER", "").strip().lower() == "agent-cli"
                    else _lmstudio_classifier)
    blocked: dict[str, str] = {}
    unique = list(dict.fromkeys(labels))
    for i in range(0, len(unique), batch):
        chunk = unique[i: i + batch]
        try:
            got = classify(chunk)
        except ScreenUnavailable:
            raise
        except Exception as exc:
            raise ScreenUnavailable(f"classifier failed: {exc}") from exc
        for label in chunk:
            cat = got.get(label)
            if cat is None:
                blocked[label] = "unscreened"
            elif cat != "none":
                blocked[label] = cat
            elif filter_statement(label):
                blocked[label] = filter_statement(label)
    return blocked
