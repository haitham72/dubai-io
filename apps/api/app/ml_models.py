"""Local NLP backends for comment analysis and embeddings.

Models (from the Faz3 reference project; overridable in config):
- sentiment: cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual
- embeddings: sentence-transformers/all-MiniLM-L6-v2

All heavy imports are lazy. Without the ML dependencies the backend reports
unavailable and nothing is labelled: missing analysis is honest, never a fake
neutral score. `harsh` is NOT a dedicated toxicity verdict: it is derived from
the sentiment negative score (same as Faz3's neg-based toxic counts) and is
labelled as such. It never auto-hides content.
"""
import json
import logging
import math

from .config import settings

log = logging.getLogger(__name__)

# Semantic topic descriptors; a comment's topics are its nearest descriptors
# in embedding space. Short product taxonomy, documented here, not inferred.
TOPIC_DESCRIPTORS = {
    "rent_housing": "rent apartment housing lease deposit landlord bedroom flat accommodation",
    "jobs_hiring": "job hiring salary interview CV work employment boss career",
    "food_dining": "food restaurant cafe dinner lunch cuisine eat",
    "transport_commute": "metro bus taxi commute drive traffic road RTA nol parking",
    "neighborhoods_moving": "neighborhood area move marina JLT downtown community location",
    "shopping_items": "buy sell used item shop price market second hand",
    "schools_family": "school kids family children nursery wife mother",
    "health": "doctor clinic hospital health gym",
    "weekend_events": "weekend plans beach party event festival night",
    "money_bills": "money price bill DEWA salik fine cost expensive cheap",
}
TOPIC_THRESHOLD = 0.18
TOPIC_LIMIT = 2
HARSH_BASIS = "sentiment_negative"

DDL = (
    """CREATE TABLE IF NOT EXISTS comment_labels (
        comment_id TEXT PRIMARY KEY, post_id TEXT NOT NULL, sentiment TEXT NOT NULL,
        neg REAL NOT NULL, neu REAL NOT NULL, pos REAL NOT NULL, topics TEXT NOT NULL,
        harsh INTEGER NOT NULL, harsh_basis TEXT NOT NULL, model TEXT NOT NULL,
        analyzed_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS comment_embeddings (
        comment_id TEXT PRIMARY KEY, post_id TEXT NOT NULL, model TEXT NOT NULL,
        dim INTEGER NOT NULL, vec TEXT NOT NULL)""",
)


def setup(store):
    for statement in DDL:
        store.db.execute(statement)
    store.db.commit()


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


_backend = None


def set_backend(backend):
    """Inject a backend (tests); None resets to lazy loading."""
    global _backend
    _backend = backend


def probe():
    """Side-effect-free capability check; never downloads models."""
    import importlib.util
    deps = bool(importlib.util.find_spec("transformers") and importlib.util.find_spec("sentence_transformers"))
    loaded = _backend is not None and getattr(_backend, "available", False)
    return {"deps_installed": deps, "backend_loaded": loaded}


def backend():
    global _backend
    if _backend is None:
        _backend = _load() or _Unavailable()
    return _backend


def _load():
    try:
        from transformers import pipeline
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    try:
        clf = pipeline("sentiment-analysis", model=settings.sentiment_model, truncation=True)
        emb = SentenceTransformer(settings.embedding_model)
    except Exception as exc:  # missing weights, no network: stay honest
        log.warning("ml backend unavailable: %s", exc)
        return None
    return _RealBackend(clf, emb)


class _Unavailable:
    available = False

    def analyze(self, text):
        return {"available": False}

    def embed(self, texts):
        return None


class _RealBackend:
    available = True

    def __init__(self, clf, emb):
        self.clf = clf
        self.emb = emb
        self._descriptors = None

    def _scores(self, text):
        out = None
        for kwargs in ({"top_k": None}, {"return_all_scores": True}, {}):
            try:
                out = self.clf((text or "")[:2000], **kwargs)
                break
            except TypeError:
                continue
        rows = out if isinstance(out, list) else [out]
        scores = {"neg": 0.0, "neu": 0.0, "pos": 0.0}
        for row in rows or []:
            label = str(row.get("label", "")).lower()
            key = "neg" if label.startswith("neg") else "pos" if label.startswith("pos") else "neu"
            scores[key] = max(scores[key], float(row.get("score", 0.0)))
        return scores

    def _descriptor_vecs(self):
        if self._descriptors is None:
            keys = list(TOPIC_DESCRIPTORS)
            vecs = self.embed([TOPIC_DESCRIPTORS[k] for k in keys])
            self._descriptors = list(zip(keys, vecs))
        return self._descriptors

    def topics(self, vec):
        ranked = sorted(((t, cosine(vec, v)) for t, v in self._descriptor_vecs()),
                        key=lambda pair: -pair[1])
        return [{"topic": t, "score": round(s, 4)} for t, s in ranked
                if s >= TOPIC_THRESHOLD][:TOPIC_LIMIT]

    def analyze(self, text):
        scores = self._scores(text)
        word = {"neg": "negative", "neu": "neutral", "pos": "positive"}[max(scores, key=scores.get)]
        vec = (self.embed([text or ""]) or [None])[0]
        return {"available": True, "sentiment": word, "neg": round(scores["neg"], 4),
                "neu": round(scores["neu"], 4), "pos": round(scores["pos"], 4),
                "topics": self.topics(vec) if vec else [],
                "harsh": scores["neg"] >= settings.harsh_neg_threshold,
                "harsh_basis": HARSH_BASIS, "model": settings.sentiment_model}

    def embed(self, texts):
        try:
            return [vec.tolist() for vec in self.emb.encode(list(texts))]
        except Exception as exc:
            log.warning("embed failed: %s", exc)
            return None


def store_label(store, owner, comment_id, post_id, text, analyzed_at):
    """Analyze one comment and persist label + embedding. Returns a status dict."""
    result = backend().analyze(text or "")
    if not result.get("available"):
        return {"status": "unavailable"}
    vec = (backend().embed([text or ""]) or [None])[0]
    with store.lock:
        setup(store)
        store.db.execute(
            "INSERT OR REPLACE INTO comment_labels VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (comment_id, post_id, result["sentiment"], result["neg"], result["neu"], result["pos"],
             json.dumps(result["topics"]), int(bool(result["harsh"])), result["harsh_basis"],
             result["model"], analyzed_at))
        if vec:
            store.db.execute("INSERT OR REPLACE INTO comment_embeddings VALUES (?,?,?,?,?)",
                             (comment_id, post_id, settings.embedding_model, len(vec), json.dumps(vec)))
        store.db.commit()
    return {"status": "stored", "sentiment": result["sentiment"], "harsh": result["harsh"]}
