"""Small deterministic temporal recommender. No LLM calls or imported ad profiles.

Only reviewed app topics can be learned. Client observations are organic-only;
neither Google listing attributes nor transcripts are retained. Observations can
rank options, never prefill a form, schedule a message or execute an action.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .actions import COOKIE, engine

router = APIRouter(tags=["recommendations"])
TOPICS = {
    "food.restaurants": "restaurants", "food.seafood": "seafood", "food.cafes": "cafés",
    "pets.care": "pet care", "pets.grooming": "pet grooming", "pets.boarding": "pet boarding",
    "services.laundry": "laundry", "services.cleaning": "home cleaning", "services.repairs": "repairs",
    "shopping.clothing": "clothing", "shopping.books": "books", "shopping.gifts": "gifts",
    "events.festivals": "festivals", "events.live_music": "live music", "events.exhibitions": "exhibitions",
    "outings.attractions": "attractions", "occasions.celebrations": "celebrations",
}
WEIGHTS = {"category": .25, "detail": .5, "choose": 1., "save": 1.5, "less_like_this": -1.5, "dismiss": 0.}
DAY = 86400
RANKER = "temporal-v1"


def clock():
    return datetime.now(timezone.utc).timestamp()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Event(Strict):
    event_key: str = Field(min_length=8, max_length=100)
    session_id: str = Field(min_length=8, max_length=64)
    thread_id: str | None = Field(default=None, max_length=64)
    kind: Literal["category", "detail", "choose", "save", "less_like_this", "dismiss"]
    topic: str
    entity_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9:_-]+$")

    @field_validator("topic")
    @classmethod
    def topic_known(cls, value):
        if value not in TOPICS:
            raise ValueError("Unknown app topic")
        return value


class Batch(Strict):
    events: list[Event] = Field(min_length=1, max_length=30)


class Candidate(Strict):
    id: str = Field(min_length=1, max_length=160)
    topics: list[str] = Field(min_length=1, max_length=5)

    @field_validator("topics")
    @classmethod
    def topics_known(cls, values):
        if any(t not in TOPICS for t in values):
            raise ValueError("Unknown app topic")
        return list(dict.fromkeys(values))


class Rank(Strict):
    session_id: str = Field(min_length=8, max_length=64)
    intent: str | None = None
    surface: Literal["maps", "services", "events", "home"]
    sort: Literal["recommended", "closest", "price"] = "recommended"
    candidates: list[Candidate] = Field(max_length=60)

    @field_validator("intent")
    @classmethod
    def intent_known(cls, value):
        if value is not None and value not in TOPICS:
            raise ValueError("Unknown app topic")
        return value


class Control(Strict):
    action: Literal["confirm", "reject", "forget", "resume"]


def setup(store):
    db = store.db
    db.execute("""CREATE TABLE IF NOT EXISTS recommendation_events (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, event_key TEXT NOT NULL, session_id TEXT NOT NULL, thread_id TEXT,
        kind TEXT NOT NULL, topic TEXT NOT NULL, entity_id TEXT NOT NULL, weight REAL NOT NULL,
        received_at DOUBLE PRECISION NOT NULL, expires_at DOUBLE PRECISION NOT NULL, usage_class TEXT NOT NULL,
        UNIQUE(owner,event_key))""")
    db.execute("CREATE INDEX IF NOT EXISTS recommendation_events_owner ON recommendation_events(owner,session_id,topic,entity_id)")
    db.execute("""CREATE TABLE IF NOT EXISTS profile_interests (
        owner TEXT NOT NULL, topic TEXT NOT NULL, scope TEXT NOT NULL, context_key TEXT NOT NULL,
        usage_class TEXT NOT NULL, positive REAL NOT NULL, negative REAL NOT NULL, evidence_count INTEGER NOT NULL,
        last_decay DOUBLE PRECISION NOT NULL, expires_at DOUBLE PRECISION NOT NULL, evidence JSON NOT NULL,
        status TEXT NOT NULL DEFAULT 'active', PRIMARY KEY(owner,topic,scope,context_key,usage_class))""")
    db.execute("""CREATE TABLE IF NOT EXISTS recommendation_runs (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, session_id TEXT NOT NULL, surface TEXT NOT NULL,
        intent TEXT, profile_version TEXT NOT NULL, ranker_version TEXT NOT NULL, results JSON NOT NULL,
        created_at DOUBLE PRECISION NOT NULL, expires_at DOUBLE PRECISION NOT NULL)""")
    db.commit()


class Recommender:
    def __init__(self, store):
        self.store = store

    def _lock_owner(self, owner):
        # Cross-process serialization supplements the shared Python connection lock.
        if self.store.db.dialect == "postgres":
            self.store.db.execute("SELECT pg_advisory_xact_lock(hashtext(?))", ("recommendations:" + owner,))

    def _prune(self, at):
        for table in ("recommendation_events", "recommendation_runs"):
            self.store.db.execute(f"DELETE FROM {table} WHERE expires_at<=?", (at,))
        self.store.db.execute("DELETE FROM profile_interests WHERE expires_at<=? AND status='active'", (at,))

    def _project(self, owner, event, delta, at):
        db = self.store.db
        for scope, key, half_life, lifetime in (("session", event.session_id, 1800, DAY), ("long_term", "all", 30 * DAY, 90 * DAY)):
            row = db.execute("""SELECT positive,negative,evidence_count,last_decay,evidence,status FROM profile_interests
                WHERE owner=? AND topic=? AND scope=? AND context_key=? AND usage_class='organic_only'""", (owner,event.topic,scope,key)).fetchone()
            if row and row[5] in {"rejected", "forgotten"}:
                continue
            decay = .5 ** (max(0, at - row[3]) / half_life) if row else 1
            positive, negative = (row[0] * decay, row[1] * decay) if row else (0.,0.)
            evidence = json.loads(row[4]) if row else []
            entity_key = sha256(event.entity_id.encode()).hexdigest()[:20]
            count = (row[2] if row else 0) + int(entity_key not in evidence)
            evidence = list(dict.fromkeys([*evidence,entity_key]))[-32:]
            db.execute("""INSERT INTO profile_interests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(owner,topic,scope,context_key,usage_class) DO UPDATE SET
                positive=excluded.positive,negative=excluded.negative,evidence_count=excluded.evidence_count,
                last_decay=excluded.last_decay,expires_at=excluded.expires_at,evidence=excluded.evidence""",
                (owner,event.topic,scope,key,"organic_only",positive + max(delta,0),negative + max(-delta,0),count,at,at+lifetime,json.dumps(evidence),row[5] if row else "active"))

    def record(self, owner, events):
        at, recorded = clock(), 0
        with self.store.lock:
            db = self.store.db
            self._lock_owner(owner)
            self._prune(at)
            for event in events:
                override = db.execute("""SELECT status FROM profile_interests WHERE owner=? AND topic=?
                    AND scope='long_term' AND context_key='all' AND usage_class='organic_only'""", (owner,event.topic)).fetchone()
                if override and override[0] in {"rejected", "forgotten"}:
                    continue
                weight = WEIGHTS[event.kind]
                # A replay with a new key still cannot inflate one item indefinitely.
                previous = db.execute("""SELECT COALESCE(SUM(weight),0) FROM recommendation_events
                    WHERE owner=? AND session_id=? AND entity_id=? AND topic=? AND kind=?""",
                    (owner,event.session_id,event.entity_id,event.topic,event.kind)).fetchone()[0]
                delta = math.copysign(max(0,abs(weight)-abs(previous)), weight)
                cur = db.execute("INSERT OR IGNORE INTO recommendation_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (uuid4().hex,owner,event.event_key,event.session_id,event.thread_id,event.kind,event.topic,event.entity_id,delta,at,at+90*DAY,"organic_only"))
                if cur.rowcount:
                    recorded += 1
                    if delta:
                        self._project(owner,event,delta,at)
            db.commit()
        return recorded

    def interests(self, owner, session_id=None):
        at, result = clock(), []
        with self.store.lock:
            rows = self.store.db.execute("""SELECT topic,scope,context_key,positive,negative,evidence_count,last_decay,expires_at,status
                FROM profile_interests WHERE owner=? AND usage_class='organic_only' ORDER BY topic,scope""", (owner,)).fetchall()
            self.store.db.commit()
        for topic,scope,key,positive,negative,count,last,expiry,status in rows:
            if scope == "session" and key != session_id or expiry <= at and status == "active":
                continue
            decay = .5 ** (max(0,at-last)/(1800 if scope == "session" else 30*DAY))
            p,n = positive*decay,negative*decay
            result.append({"topic":topic,"label":TOPICS[topic],"scope":scope,"status":status,
                "provenance":"user_supplied" if status == "confirmed" else "inferred",
                "confidence":round((p+1)/(p+n+2),4),"evidence_count":count,
                "signal":round(p/(p+n+2),4),"as_of":datetime.fromtimestamp(last,timezone.utc).isoformat(),
                "usage_class":"organic_only"})
        return result

    def control(self, owner, topic, action):
        from .luna.graph import clear_conversation, memory_lock
        with memory_lock:
            if action != "confirm":
                clear_conversation(owner)
            return self._control(owner,topic,action)

    def _control(self, owner, topic, action):
        if topic not in TOPICS:
            raise HTTPException(404,"Unknown interest")
        at = clock()
        status = {"confirm":"confirmed","reject":"rejected","forget":"forgotten","resume":"active"}[action]
        with self.store.lock:
            db = self.store.db
            self._lock_owner(owner)
            db.execute("DELETE FROM recommendation_events WHERE owner=? AND topic=?", (owner,topic))
            db.execute("DELETE FROM profile_interests WHERE owner=? AND topic=?", (owner,topic))
            db.execute("DELETE FROM recommendation_runs WHERE owner=?", (owner,))
            if action != "resume":
                db.execute("INSERT INTO profile_interests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (owner,topic,"long_term","all","organic_only",0.,0.,0,at,at+90*DAY,"[]",status))
            db.commit()
        # Confirmation is an explicit user decision, not promotion by an LLM.
        from .user_profile import ProfileStore
        facts = ProfileStore(lambda:self.store)
        key = "interest:" + topic
        if action == "confirm":
            facts.add(owner,key,TOPICS[topic],"You confirmed this interest",facet="preference",status="confirmed")
        else:
            facts.forget(owner,key)
        return {"topic":topic,"status":status}

    def rank(self, owner, body):
        interests = self.interests(owner,body.session_id)
        visible = [i for i in interests if i["status"] in {"active","confirmed"}]
        indexed = {(i["topic"],i["scope"]):i for i in visible}
        version = sha256(json.dumps(interests,sort_keys=True).encode()).hexdigest()[:16]
        ranked = []
        for position,candidate in enumerate(body.candidates):
            current = float(body.intent in candidate.topics) if body.intent else .5
            confirmed = any(indexed.get((t,"long_term"),{}).get("status") == "confirmed" for t in candidate.topics)
            session = max((indexed.get((t,"session"),{}).get("signal",0) for t in candidate.topics),default=0)
            long = max((indexed.get((t,"long_term"),{}).get("signal",0) for t in candidate.topics),default=0)
            evidence = [i for i in visible if i["topic"] in candidate.topics and i["evidence_count"] >= 2 and i["confidence"] >= .6]
            # Inferred contributions are used only when the reason can be displayed.
            if not evidence:
                session = long = 0
            score = .45*current + .2*float(confirmed) + .15*session + .1*long + .1*.5
            reason = ("Because you confirmed an interest in " + next(TOPICS[t] for t in candidate.topics if indexed.get((t,"long_term"),{}).get("status") == "confirmed")) if confirmed else (
                "Because you explored " + evidence[0]["label"] if evidence else None)
            ranked.append({"id":candidate.id,"score":round(score,6),"reason":reason,"provenance":"inferred" if reason and not confirmed else "user_supplied" if confirmed else "estimate","position":position})
        if body.sort == "recommended":
            ranked.sort(key=lambda r:(-r["score"],r["position"]))
        for row in ranked:
            row.pop("position")
        run_id,at = uuid4().hex,clock()
        with self.store.lock:
            self._prune(at)
            self.store.db.execute("INSERT INTO recommendation_runs VALUES (?,?,?,?,?,?,?,?,?,?)",
                (run_id,owner,body.session_id,body.surface,body.intent,version,RANKER,json.dumps(ranked),at,at+DAY))
            self.store.db.commit()
        return {"run_id":run_id,"profile_version":version,"ranker_version":RANKER,"results":ranked,"as_of":datetime.fromtimestamp(at,timezone.utc).isoformat()}


def owned(request):
    store = engine().store
    owner = store.owner(request.cookies.get(COOKIE))
    with store.lock:
        setup(store)
    return Recommender(store),owner


@router.post("/api/recommendation-events")
def record_events(body: Batch, request: Request):
    rec,owner = owned(request)
    return {"recorded":rec.record(owner,body.events)}


@router.post("/api/recommendations")
def recommend(body: Rank, request: Request):
    if len({c.id for c in body.candidates}) != len(body.candidates):
        raise HTTPException(422,"Candidate IDs must be unique")
    rec,owner = owned(request)
    return rec.rank(owner,body)


@router.get("/api/profile/interests")
def list_interests(request: Request, session_id: str | None = None):
    rec,owner = owned(request)
    return {"interests":rec.interests(owner,session_id),"topics":TOPICS}


@router.put("/api/profile/interests/{topic}")
def control_interest(topic: str, body: Control, request: Request):
    rec,owner = owned(request)
    return rec.control(owner,topic,body.action)
