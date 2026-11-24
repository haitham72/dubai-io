"""Record owner-scoped topic evidence by distinct conversation sessions."""
from __future__ import annotations

from collections import defaultdict

from temporal_memory.db.db import fold_text
from temporal_memory.live.triples import feature_id, quarantine_category
from temporal_memory.models import HELD_BACK_ROOTS, Fact


_BLOCKED_ROOTS = {*HELD_BACK_ROOTS, "family", "people family", "people and family",
                  "people", "relationships", "religion", "wellbeing", "well being"}


def eligible_subject(path: str, label: str, sensitive_cat: str | None = None) -> bool:
    return (
        not sensitive_cat
        and not any(fold_text(segment) in _BLOCKED_ROOTS for segment in path.split("/"))
        and not quarantine_category(f"{path} {label}")
    )


def _contains(folded: str, name: str) -> bool:
    return bool(name and f" {name} " in f" {folded} ")


def match_topics(text, subjects, entity_aliases, affiliations) -> set[str]:
    """Use whole folded phrases; aliases shared across entities are ambiguous."""
    folded = fold_text(text)
    matched = {
        subject["id"] for subject in subjects
        if eligible_subject(subject["path"], subject["label"], subject["sensitive_cat"])
        and any(_contains(folded, fold_text(term))
                for term in (subject["label"], subject["path"].rsplit("/", 1)[-1]))
    }
    owners = defaultdict(set)
    for entity_id, alias in entity_aliases:
        owners[fold_text(alias)].add(entity_id)
    unique_hits = {
        next(iter(ids)) for alias, ids in owners.items() if len(ids) == 1 and _contains(folded, alias)
    }
    eligible = {
        subject["id"] for subject in subjects
        if eligible_subject(subject["path"], subject["label"], subject["sensitive_cat"])
    }
    return matched | {sid for eid, sid in affiliations if eid in unique_hits and sid in eligible}


class PostgresTopicMentions:
    """The topic counter shares the caller's record and hypothesis transaction."""

    def __init__(self, conn):
        self.conn = conn

    def record_topic_mention(self, owner: str, subject_id: str, session_id: str) -> int:
        self.conn.execute(
            """INSERT INTO topic_mentions (owner,subject_id,session_id)
               VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
            (owner, subject_id, session_id),
        )
        return self.topic_session_count(owner, subject_id)

    def _evidence(self, owner: str, subject_id: str):
        return self.conn.execute(
            """SELECT DISTINCT ON (tm.session_id) r.id,r.generation,r.at
               FROM topic_mentions tm JOIN records r
                 ON r.owner=tm.owner AND r.meta->>'u2_session'=tm.session_id
               WHERE tm.owner=%s AND tm.subject_id=%s AND r.erased_at IS NULL
                 AND r.meta->'u2_topics' ? tm.subject_id
               ORDER BY tm.session_id,r.at,r.id""",
            (owner, subject_id),
        ).fetchall()

    def topic_session_count(self, owner: str, subject_id: str) -> int:
        return len(self._evidence(owner, subject_id))

    def observe(self, owner, record_id, session_id, text):
        subjects = self.conn.execute(
            """SELECT s.id,s.path,s.label,s.sensitive_cat FROM subjects s WHERE s.owner=%s
               AND NOT EXISTS (SELECT 1 FROM forget_rules fr WHERE fr.owner=s.owner
                 AND fr.kind='subject' AND (fr.value=s.id OR position(lower(fr.value) in lower(s.path))>0))""",
            (owner,),
        ).fetchall()
        tokens = fold_text(text).split()
        phrases = list({" ".join(tokens[i:i+n]) for i in range(len(tokens)) for n in range(1, min(6, len(tokens)-i)+1)})
        aliases = self.conn.execute(
            """SELECT DISTINCT e.id,a.alias_folded AS alias FROM entity_aliases a
               JOIN entities e ON e.owner=a.owner AND e.id=a.entity_id
               WHERE a.owner=%s AND a.alias_folded=ANY(%s) AND e.erased_at IS NULL
                 AND e.status='active' AND e.kind <> 'person'""",
            (owner, phrases),
        ).fetchall() if phrases else []
        affiliations = self.conn.execute(
            """SELECT DISTINCT es.entity_id,es.subject_id FROM entity_subjects es
               JOIN fact_entities fe ON fe.owner=es.owner AND fe.entity_id=es.entity_id
               JOIN visible_facts f ON f.owner=fe.owner AND f.id=fe.fact_id AND f.subject_id=es.subject_id
               WHERE es.owner=%s AND es.entity_id=ANY(%s) AND f.status='active' AND f.provenance='user_supplied'""",
            (owner, [row["id"] for row in aliases]),
        ).fetchall() if aliases else []
        matches = match_topics(text, subjects, [(a["id"], a["alias"]) for a in aliases],
                               [(a["entity_id"], a["subject_id"]) for a in affiliations])
        if not matches:
            return []
        import json

        self.conn.execute(
            """UPDATE records SET meta=jsonb_set(meta,'{u2_topics}',%s::jsonb)
               WHERE owner=%s AND id=%s""",
            (json.dumps(sorted(matches)), owner, record_id),
        )
        created = []
        for subject in subjects:
            if subject["id"] in matches and self.record_topic_mention(owner, subject["id"], session_id) >= 2:
                fact_id = self._notice(owner, subject)
                if fact_id:
                    created.append(fact_id)
        return created

    def _notice(self, owner, subject):
        evidence = self._evidence(owner, subject["id"])
        if len(evidence) < 2:
            return None
        # Earliest two eligible sessions as of insertion; retries retain the receipt.
        evidence = sorted(evidence, key=lambda row: (row["at"], row["id"]))[:2]
        fact = topic_fact(owner, subject["id"], subject["label"], [row["id"] for row in evidence], evidence[-1]["at"])
        inserted = self.conn.execute(
            """INSERT INTO facts (owner,id,text,text_folded,subject_id,valid_from,status,provenance,content_hash)
               SELECT %s,%s,%s,%s,%s,%s,'hypothesis','inferred',%s
               WHERE NOT EXISTS (SELECT 1 FROM forget_rules WHERE owner=%s AND
                 ((kind='item' AND value=%s) OR (kind='text' AND position(lower(value) in lower(%s))>0)))
               ON CONFLICT (owner,id) DO NOTHING RETURNING id""",
            (owner, fact.id, fact.text, fold_text(fact.text), fact.subject_id, fact.valid_from, fact.id,
             owner, fact.id, fact.text),
        ).fetchone()
        if not inserted:
            return None
        for row in evidence:
            self.conn.execute(
                "INSERT INTO fact_evidence (owner,fact_id,record_id,record_generation) VALUES (%s,%s,%s,%s)",
                (owner, fact.id, row["id"], row["generation"]),
            )
        return fact.id


def topic_fact(owner: str, subject_id: str, label: str, evidence: list[str], at: str) -> Fact:
    return Fact(feature_id("topic", owner, subject_id), owner, f"I noticed you're into {label}",
                subject_id, at, evidence, status="hypothesis", provenance="inferred")
