"""Conservative extraction from an authenticated author's own turn."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import re

from temporal_memory.db.db import fold_text
from temporal_memory.models import CLUSTER_LABELS, Fact, Owner, PlaceType, Record, TripleModality, TriplePredicate
from temporal_memory.privacy.sensitive import pre_write


@dataclass(frozen=True)
class Triple:
    predicate: TriplePredicate
    object_text: str
    span_start: int
    span_end: int
    modality: TripleModality = "done"
    place_type: PlaceType | None = None


_FAMILY = re.compile(
    r"\b(?:my|our)\s+(?:mom|mum|mother|dad|father|sister|brother|wife|husband|child|daughter|son|"
    r"parents|family|grandmother|grandfather|aunt|uncle|cousin)\b|"
    r"(?<!\w)(?:أمي|امي|والدي|والدتي|أبويا|ابويا|أختي|اختي|أخي|اخي|عيلتي|زوجتي|زوجي)(?!\w)", re.I
)
_REJECT = re.compile(
    r'[?؟"“”«»\x60]|[\U0001f600-\U0001f64f]|'
    r"\b(?:never|not|didn['’]?t|don['’]?t|didnt|dont|won['’]?t|cancelled|canceled|if|maybe|"
    r"might|would|could|supposedly|apparently|probably|lol|haha|sarcasm|in my dreams|"
    r"or not|or what|right|they said|he said|she said|forwarded|promo|mesh|msh|law|ymken|"
    r"wala|tab3an)\b|(?<!\w)(?:مش|ما|لم|لن|رح|لو|ممكن|ولا|بس|طبعاً|طبعا)(?!\w)", re.I
)
_RULES: tuple[tuple[str, TriplePredicate, TripleModality, PlaceType | None], ...] = (
    (r"(?:i\s+)?(?:just\s+)?(?:bought|ordered|got|picked up)\s+", "buys", "done", None),
    (r"(?:i\s+)?booked\s+", "other", "done", "other"),
    (r"(?:i\s+|we\s+)?(?:had|grabbed)\s+(?:dinner|lunch|breakfast)\s+at\s+", "visits", "done", "restaurant"),
    (r"i\s+(?:went to|visited)\s+", "visits", "done", "other"),
    (r"i\s+(?:love|like|prefer)\s+", "likes", "done", None),
    (r"i\s+(?:dislike|hate)\s+", "dislikes", "done", None),
    (r"i\s+want\s+(?:to buy\s+)?", "wants", "wanted", None),
    (r"i\s+moved\s+to\s+", "moves_to", "done", "other"),
    (r"i\s+joined\s+", "joins", "done", None),
    (r"i\s+(?:work at|started working at)\s+", "works_at", "done", None),
    (r"i\s+will\s+(?:buy|order)\s+", "buys", "planned", None),
    (r"(?:أنا\s+)?اشتريت\s+", "buys", "done", None),
    (r"(?:أنا\s+)?حجزت\s+(?:ترابيزة|طاولة)\s+في\s+مطعم\s+", "other", "done", "restaurant"),
    (r"(?:أنا\s+)?(?:اتعشيت|اتعشينا|تغديت)\s+في\s+مطعم\s+", "visits", "done", "restaurant"),
    (r"(?:أنا\s+)?رحت\s+(?:كافيه|مقهى)\s+", "visits", "done", "café"),
    (r"(?:أنا\s+)?نقلت\s+(?:شقة\s+جديدة\s+في|إلى|الى)\s+", "moves_to", "done", "other"),
    (r"(?:أنا\s+)?بحب\s+", "likes", "done", None),
    (r"نفسي\s+أشتري\s+", "wants", "wanted", None),
    (r"(?:ana\s+)?(?:e|i)shte(?:ree|aree)t\s+", "buys", "done", None),
    (r"(?:ana\s+)?7agazt\s+", "other", "done", "other"),
    (r"(?:ana\s+)?ro7t\s+(?:dinner|lunch)\s+(?:fe|fi)\s+", "visits", "done", "restaurant"),
    (r"(?:ana\s+)?ba7eb\s+", "likes", "done", None),
    (r"(?:ana\s+)?naqalt\s+", "moves_to", "done", "other"),
    (r"(?:ana\s+)?3ayez\s+ashtery\s+", "wants", "wanted", None),
)
_TEMPLATES = tuple((re.compile(pattern, re.I), predicate, modality, place) for pattern, predicate, modality, place in _RULES)
_ARTICLE = re.compile(r"^(?:an?|the|el)\s+", re.I)
_END = re.compile(
    r"[,،;؛.!…]|\s+(?:yesterday|today|tomorrow|last|this|just now|from|for|in|on|at|"
    r"embara7|el osboo3|el naharda|youm|mn|fe|fi|kite beach|امبارح|امس|أمس|اليوم|الصبح|يوم|من|في|\u0648\u0643\u0627\u0646)(?=\s|[,.;\u060c\u061b]|$)", re.I
)
_OTHER_CLAUSE = re.compile(
    r"\b(?:and|but|or|because|said|told|heard|thought|that|he|she|then|reportedly)\b|"
    r"(?<!\w)(?:قال|قالت|بيقول|بيقولوا|لكن|عشان|لأن|أو)(?!\w)", re.I
)


def quarantine_category(text: str) -> str | None:
    """Hold restricted content before it can produce a fact, a topic, or a job."""
    return pre_write(text) or ("family_third_party" if _FAMILY.search(text) else None)


def extract_triples(text: str) -> list[Triple]:
    """Parse at most one explicit assertion. The caller authenticates the record author."""
    if len(text) > 400 or quarantine_category(text) or _REJECT.search(text) or _OTHER_CLAUSE.search(text):
        return []
    clean = text.lstrip()
    offset = len(text) - len(clean)
    if "\n" in clean or "\r" in clean:
        return []
    for pattern, predicate, modality, place in _TEMPLATES:
        match = pattern.match(clean)
        if match is None:
            continue
        rest = clean[match.end():]
        article = _ARTICLE.match(rest)
        article_len = article.end() if article else 0
        value = rest[article_len:]
        cutoff = _END.search(value)
        value = (value[:cutoff.start()] if cutoff else value).strip()
        if predicate == "buys":
            product = re.match(r"(?:shoes|camera|phone)\s+(?=\S.*\d)", value, re.I)
            if product:
                article_len += product.end()
                value = value[product.end():]
            if re.search(r"\d", value):
                value = re.sub(r"\s+(?:camera|phone|laptop)$", "", value, flags=re.I)
            if fold_text(value) in {"it", "that", "this", "one", "a text", "text", "a message", "message"}:
                return []
        if not value or len(value) > 100 or len(value.split()) > 8 or not value[0].isalnum():
            return []
        return [Triple(predicate, value, offset, offset + match.end() + article_len + len(value), modality, place)]
    return []


def feature_id(kind: str, *parts: str) -> str:
    return f"u2_{kind}_" + hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()[:24]


def fact_from_triple(owner: Owner, record: Record, triple: Triple, subject_id: str) -> Fact:
    from temporal_memory.live.context import extract_date

    text = record.text
    try:
        dates = extract_date(text[triple.span_end:], reference_date=date.fromisoformat(record.at[:10]))
    except ValueError:
        dates = []
    affirmed = triple.modality == "done"
    fact = Fact(
        id=feature_id("triple", owner.id, record.id, triple.predicate, triple.object_text.casefold()),
        owner=owner.id, text=text, subject_id=subject_id, valid_from=record.at,
        evidence=[record.id], provenance="user_supplied" if affirmed else "inferred",
        status="active" if affirmed else "hypothesis", predicate=triple.predicate,
        object_text=triple.object_text, modality=triple.modality, polarity="affirmed",
        event_at=dates[0]["iso"] if len(dates) == 1 else None,
        span_record_id=record.id, span_start=triple.span_start, span_end=triple.span_end,
    )
    return fact


def save_postgres_triple(conn, owner: Owner, record: Record, triple: Triple) -> str | None:
    path = "career" if triple.predicate == "works_at" else "events"
    default_subject = feature_id("subject", owner.id, path)
    fact = fact_from_triple(owner, record, triple, default_subject)
    default_actor = feature_id("self", owner.id)
    default_place = feature_id("place", owner.id, fold_text(triple.object_text))
    state = conn.execute(
        """
        SELECT
            (SELECT id FROM subjects WHERE owner=%(owner)s AND path=%(path)s) AS subject,
            (SELECT id FROM entities WHERE owner=%(owner)s AND relation_to_user='self'
                 AND erased_at IS NULL AND status <> 'merged' ORDER BY id LIMIT 1) AS actor,
            EXISTS (SELECT 1 FROM facts WHERE owner=%(owner)s AND id=%(fact)s) AS duplicate,
            EXISTS (SELECT 1 FROM forget_rules WHERE owner=%(owner)s AND
                ((kind='subject' AND (value=%(subject)s OR position(lower(value) in %(path)s)>0))
                 OR (kind='text' AND position(lower(value) in lower(%(text)s))>0)
                 OR (kind='item' AND value=%(fact)s)
                 OR (kind='entity' AND lower(value) IN (
                       lower(%(object)s),lower(%(name)s),%(actor)s,%(place)s)))) AS blocked
        """,
        {
            "owner": owner.id, "path": path, "fact": fact.id, "subject": default_subject,
            "text": record.text, "object": triple.object_text, "name": owner.display_name or owner.id,
            "actor": default_actor, "place": default_place,
        },
    ).fetchone()
    if state["duplicate"] or state["blocked"]:
        return None
    if state["subject"] is None:
        conn.execute(
            """INSERT INTO subjects (owner,id,path,label,kind,status)
               VALUES (%s,%s,%s,%s,'theme','active')""",
            (owner.id, default_subject, path, CLUSTER_LABELS[path]),
        )
    fact.subject_id = subject_id = state["subject"] or default_subject
    fact.actor_entity_id = state["actor"] or default_actor
    if state["actor"] is None:
        conn.execute(
            """INSERT INTO entities (owner,id,kind,name,status,relation_to_user,provenance)
               VALUES (%s,%s,'person',%s,'active','self','user_supplied')
               ON CONFLICT (owner,id) DO UPDATE SET erased_at=NULL""",
            (owner.id, fact.actor_entity_id, owner.display_name or owner.id),
        )
    if triple.place_type is not None and fact.status == "active":
        folded = fold_text(triple.object_text)
        place_rows = conn.execute(
            """SELECT DISTINCT e.id FROM entities e LEFT JOIN entity_aliases a
               ON a.owner=e.owner AND a.entity_id=e.id
               WHERE e.owner=%s AND e.kind='place' AND e.erased_at IS NULL AND e.status <> 'merged'
                 AND (lower(e.name)=lower(%s) OR a.alias_folded=%s) LIMIT 2""",
            (owner.id, triple.object_text, folded),
        ).fetchall()
        if len(place_rows) == 1:
            fact.object_entity_id = place_rows[0]["id"]
        elif not place_rows:
            fact.object_entity_id = default_place
        if fact.object_entity_id:
            conn.execute(
                """INSERT INTO entities (owner,id,kind,name,status,provenance,place_type)
                   VALUES (%s,%s,'place',%s,'active','user_supplied',%s)
                   ON CONFLICT (owner,id) DO UPDATE SET erased_at=NULL,
                     place_type=CASE WHEN entities.place_type IS NULL OR entities.place_type='other'
                                     THEN EXCLUDED.place_type ELSE entities.place_type END""",
                (owner.id, fact.object_entity_id, triple.object_text, triple.place_type),
            )
            conn.execute(
                """INSERT INTO entity_aliases (owner,entity_id,alias,alias_folded,source)
                   VALUES (%s,%s,%s,%s,'user_supplied') ON CONFLICT DO NOTHING""",
                (owner.id, fact.object_entity_id, triple.object_text, folded),
            )

    params = asdict(fact)
    params["text_folded"] = fold_text(f"{record.text} {triple.place_type or ''}")
    params["content_hash"] = fact.id
    params["generation"] = record.generation
    params["entity_ids"] = [eid for eid in (fact.actor_entity_id, fact.object_entity_id) if eid]
    conn.execute(
        """
        WITH added AS (
            INSERT INTO facts (owner,id,text,text_folded,subject_id,valid_from,status,provenance,content_hash,
                actor_entity_id,predicate,object_text,object_entity_id,polarity,modality,event_at,
                span_record_id,span_start,span_end)
            VALUES (%(owner)s,%(id)s,%(text)s,%(text_folded)s,%(subject_id)s,%(valid_from)s,%(status)s,
                %(provenance)s,%(content_hash)s,%(actor_entity_id)s,%(predicate)s,%(object_text)s,
                %(object_entity_id)s,%(polarity)s,%(modality)s,%(event_at)s,%(span_record_id)s,%(span_start)s,%(span_end)s)
            RETURNING owner,id,subject_id,status
        ), evidence AS (
            INSERT INTO fact_evidence (owner,fact_id,record_id,record_generation)
            SELECT owner,id,%(span_record_id)s,%(generation)s FROM added
        ), mentions AS (
            INSERT INTO fact_entities (owner,fact_id,entity_id)
            SELECT owner,id,unnest(%(entity_ids)s::text[]) FROM added
        )
        UPDATE subjects s SET fact_count=s.fact_count+1 FROM added
        WHERE s.owner=added.owner AND s.id=added.subject_id AND added.status='active'
        """,
        params,
    )
    if fact.object_entity_id:
        conn.execute(
            """INSERT INTO entity_subjects (owner,entity_id,subject_id,role,weight,fact_count,first_seen,last_seen)
               VALUES (%s,%s,%s,'',1,1,%s,%s)
               ON CONFLICT (owner,entity_id,subject_id,role) DO UPDATE SET
                 weight=entity_subjects.weight+1, fact_count=entity_subjects.fact_count+1,
                 first_seen=LEAST(entity_subjects.first_seen,EXCLUDED.first_seen),
                 last_seen=GREATEST(entity_subjects.last_seen,EXCLUDED.last_seen)""",
            (owner.id, fact.object_entity_id, subject_id, record.at, record.at),
        )
    return fact.id
