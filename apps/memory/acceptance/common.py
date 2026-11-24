"""Shared helpers for the temporal_note external acceptance harness (U0b)."""
from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from typing import Any, Iterator
import uuid

import httpx
import psycopg
import uvicorn

from temporal_memory.api.app import create_app
from temporal_memory.db import db as db_mod
from temporal_memory.db.db import Database, fold_text, migrate
from temporal_memory.privacy.sensitive import pre_write

DSN = os.environ.get("TM_TEST_DATABASE_URL", "postgresql://tm:tm@localhost:5442/tm")
ACCEPTANCE_DIR = Path(__file__).resolve().parent
GOLD_DIR = ACCEPTANCE_DIR / "gold"
EMPTY_MCP = ACCEPTANCE_DIR / "empty_mcp.json"
CLAUDE_EXE = os.environ.get("CLAUDE_EXE") or shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude.exe")

_AR_RE = re.compile(r"[\u0600-\u06FF]")
_ARZ_HINT_RE = re.compile(r"\b(el|emta|bekam|delwa2ty|hayebda2|3omar|7aga|mish|keda)\b", re.I)


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, math.ceil(p * len(sorted_vals)) - 1))
    return float(sorted_vals[idx])


def summarize_latencies(vals: list[float]) -> dict[str, Any]:
    s = sorted(float(v) for v in vals)
    if not s:
        return {"n": 0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "max_ms": 0.0, "mean_ms": 0.0}
    return {
        "n": len(s),
        "p50_ms": round(percentile(s, 0.50), 2),
        "p95_ms": round(percentile(s, 0.95), 2),
        "p99_ms": round(percentile(s, 0.99), 2),
        "max_ms": round(s[-1], 2),
        "mean_ms": round(sum(s) / len(s), 2),
    }


def hardware_info() -> dict[str, Any]:
    info: dict[str, Any] = {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu_logical": os.cpu_count(),
        "machine": platform.machine(),
    }
    try:
        ps = (
            "$c=Get-CimInstance Win32_Processor | Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors;"
            "$m=Get-CimInstance Win32_ComputerSystem | Select-Object -First 1 TotalPhysicalMemory;"
            "$g=Get-CimInstance Win32_VideoController | Select-Object -First 1 Name;"
            "@{cpu=$c.Name;cores=$c.NumberOfCores;threads=$c.NumberOfLogicalProcessors;"
            "ram_gb=[math]::Round($m.TotalPhysicalMemory/1GB,1);gpu=$g.Name} | ConvertTo-Json -Compress"
        )
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps], text=True, timeout=10).strip()
        info.update(json.loads(out))
    except Exception:
        pass
    try:
        with psycopg.connect(DSN) as conn:
            info["postgres"] = conn.execute("SELECT version()").fetchone()[0]
    except Exception as exc:
        info["postgres_error"] = str(exc)
    return info


@contextmanager
def temp_schema(prefix: str = "acc") -> Iterator[tuple[Database, str]]:
    schema = f"acc_{prefix}_{uuid.uuid4().hex[:8]}"
    db = Database(DSN, schema=schema)
    prev_default = db_mod._DEFAULT_DB
    try:
        migrate(db)
        db_mod._DEFAULT_DB = db
        yield db, schema
    finally:
        db_mod._DEFAULT_DB = prev_default
        try:
            db.close()
        except Exception:
            pass
        with psycopg.connect(DSN, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            left = conn.execute("SELECT to_regnamespace(%s)", (schema,)).fetchone()[0]
            if left is not None:
                raise RuntimeError(f"Failed to drop temporary schema {schema}")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class LiveApiServer:
    """In-process real FastAPI + uvicorn HTTP server backed by Postgres temp schema."""

    def __init__(self, db: Database, admin_token: str = "acc-admin-tok") -> None:
        self.db = db
        self.admin_token = admin_token
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> LiveApiServer:
        app = create_app(db=self.db, admin_token=self.admin_token)
        cfg = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning", access_log=False)
        self._server = uvicorn.Server(cfg)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        deadline = time.monotonic() + 15.0
        with httpx.Client(base_url=self.base_url, timeout=2.0) as client:
            while time.monotonic() < deadline:
                try:
                    r = client.get("/health")
                    if r.status_code == 200:
                        return self
                except Exception:
                    pass
                time.sleep(0.05)
        raise RuntimeError(f"LiveApiServer failed to become healthy on {self.base_url}")

    def __exit__(self, *args: Any) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    def create_owner(
        self,
        owner_id: str,
        *,
        label: str = "",
        kind: str = "demo",
        display_name: str = "",
        self_aliases: list[str] | None = None,
        timezone: str = "Asia/Dubai",
    ) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=10.0) as c:
            r = c.post(
                "/v1/owners",
                headers=self.admin_headers,
                json={
                    "id": owner_id,
                    "label": label or owner_id,
                    "kind": kind,
                    "display_name": display_name or label or owner_id,
                    "self_aliases": self_aliases or [],
                    "timezone": timezone,
                },
            )
            r.raise_for_status()
            return dict(r.json())

    def mint_token(self, role: str, owner: str | None = None, label: str = "acc") -> str:
        with httpx.Client(base_url=self.base_url, timeout=10.0) as c:
            r = c.post(
                "/v1/tokens",
                headers=self.admin_headers,
                json={"role": role, "owner": owner, "label": label},
            )
            r.raise_for_status()
            return str(r.json()["token"])


def mcp_call(client: httpx.Client, token: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": f"acc-{uuid.uuid4().hex[:8]}",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    resp = client.post("/mcp/", headers=headers, json=payload, follow_redirects=True)
    resp.raise_for_status()
    ctype = (resp.headers.get("content-type") or "").lower()
    if "text/event-stream" in ctype:
        last = {}
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                raw = line[5:].strip()
                if raw:
                    last = json.loads(raw)
        data = last
    else:
        data = resp.json()
    res = data.get("result") or {}
    if isinstance(res.get("structuredContent"), dict):
        sc = dict(res["structuredContent"])
        if set(sc.keys()) == {"result"} and isinstance(sc["result"], dict):
            return dict(sc["result"])
        return sc
    content = res.get("content") or []
    if content and isinstance(content[0], dict) and isinstance(content[0].get("text"), str):
        return dict(json.loads(content[0]["text"]))
    return dict(res)


def load_gold() -> dict[str, Any]:
    return json.loads((GOLD_DIR / "ledger.json").read_text(encoding="utf-8"))


def load_probes() -> list[dict[str, Any]]:
    return json.loads((GOLD_DIR / "probes.json").read_text(encoding="utf-8"))["probes"]


def load_ingest_order() -> dict[str, Any]:
    return json.loads((GOLD_DIR / "ingest_order.json").read_text(encoding="utf-8"))


def load_gold_source_texts() -> dict[str, dict[str, str]]:
    """Return record_id -> {source, at, author, text} across all 5 synthetic gold source files."""
    out: dict[str, dict[str, str]] = {}
    wa_re = re.compile(r"^\[([^\]]+)\]\s*([^:]+):\s*(.*)$")
    for fname, prefix, src_name in [
        ("whatsapp_best.txt", "wab", "whatsapp:best"),
        ("whatsapp_work.txt", "wag", "whatsapp:work"),
        ("whatsapp_family.txt", "waf", "whatsapp:family"),
    ]:
        for idx, line in enumerate((GOLD_DIR / "sources" / fname).read_text(encoding="utf-8").splitlines(), 1):
            rid = f"{prefix}-{idx:04d}"
            m = wa_re.match(line)
            if m:
                out[rid] = {"source": src_name, "at": m.group(1), "author": m.group(2), "text": m.group(3)}
            else:
                out[rid] = {"source": src_name, "at": "", "author": "", "text": line}
    for line in (GOLD_DIR / "sources" / "gmail.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        subj = row.get("subject", "")
        body = row.get("body", "")
        out[row["id"]] = {
            "source": "gmail",
            "at": row.get("ts", ""),
            "author": row.get("from", ""),
            "text": f"{subj}: {body}" if subj else body,
        }
    note_re = re.compile(r"^\[(n\d+)\]\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.*)$")
    for line in (GOLD_DIR / "sources" / "notes.md").read_text(encoding="utf-8").splitlines():
        m = note_re.match(line.strip())
        if m:
            out[m.group(1)] = {"source": "notes", "at": m.group(2), "author": "Karim Haddad", "text": m.group(3)}
    return out


def extract_text_orig(fact: dict[str, Any], rec_texts: dict[str, dict[str, str]]) -> str | None:
    spans: list[str] = []
    for r in fact.get("renders") or []:
        t = str(r.get("text") or "").strip()
        if t and (_AR_RE.search(t) or _ARZ_HINT_RE.search(t)):
            spans.append(t[:300])
    if not spans:
        for rid in fact.get("evidence") or []:
            t = (rec_texts.get(rid) or {}).get("text", "")
            if t and (_AR_RE.search(t) or _ARZ_HINT_RE.search(t)):
                spans.append(t[:300])
    return " | ".join(dict.fromkeys(spans)) if spans else None


def subject_path_for(subj: dict[str, Any] | None) -> str:
    if not subj:
        return "general/notes"
    slug = re.sub(r"[^a-z0-9]+", "-", str(subj.get("name", "")).casefold()).strip("-")
    return f"{subj.get('kind', 'topic')}/{slug or subj['id']}"


def load_gold_graph(db: Database, owner: str = "karim_gold") -> dict[str, Any]:
    """Load gold ledger as a real graph: entities, aliases, subjects, links, text_orig, pre_write gate, and statuses."""
    ledger = load_gold()
    rec_texts = load_gold_source_texts()
    persona = next(p for p in ledger["people"] if p.get("relation") == "self")

    stats = {
        "owner": owner,
        "facts_total_gold": len(ledger["facts"]),
        "facts_inserted": 0,
        "facts_active": 0,
        "facts_history": 0,
        "facts_ended": 0,
        "facts_quarantined_by_gate": 0,
        "clean_gold_facts_gated_fp": [],
        "gold_sensitive_leaked_past_gate": [],
        "entities_inserted": 0,
        "aliases_inserted": 0,
        "links_inserted": 0,
    }

    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO owners (id, label, kind, display_name, self_aliases, timezone) "
            "VALUES (%s, %s, 'demo', %s, %s::jsonb, 'Asia/Dubai')",
            (owner, owner, persona["canonical"], json.dumps(persona.get("aliases") or [])),
        )
        # Subjects: themes by kind + leaf topics
        themes_seen: dict[str, str] = {}
        for s in ledger["subjects"]:
            path = subject_path_for(s)
            theme_key = path.split("/")[0]
            if theme_key not in themes_seen:
                tid = f"th_{theme_key}"
                themes_seen[theme_key] = tid
                conn.execute(
                    "INSERT INTO subjects (id, owner, parent_id, path, label, kind, status) "
                    "VALUES (%s, %s, NULL, %s, %s, 'theme', 'active') ON CONFLICT DO NOTHING",
                    (tid, owner, theme_key, theme_key.replace("-", " ").title()),
                )
            conn.execute(
                "INSERT INTO subjects (id, owner, parent_id, path, label, kind, status) "
                "VALUES (%s, %s, %s, %s, %s, 'topic', 'active') ON CONFLICT DO NOTHING",
                (s["id"], owner, themes_seen[theme_key], path, s["name"]),
            )
        conn.execute(
            "INSERT INTO subjects (id, owner, parent_id, path, label, kind, status) "
            "VALUES ('s_default', %s, NULL, 'general/notes', 'Notes', 'topic', 'active') ON CONFLICT DO NOTHING",
            (owner,),
        )

        # Entities + Aliases
        for kind, key in [("person", "people"), ("org", "orgs"), ("place", "places")]:
            for e in ledger[key]:
                nm = e.get("canonical") or e.get("name")
                rel = e.get("relation")
                if rel == "best_friend":
                    rel = "friend"
                elif rel in ("manager", "ex-colleague", "ex_colleague"):
                    rel = "colleague"
                conn.execute(
                    "INSERT INTO entities (id, owner, kind, name, status, relation_to_user) "
                    "VALUES (%s, %s, %s, %s, 'active', %s)",
                    (e["id"], owner, kind, nm, rel),
                )
                stats["entities_inserted"] += 1
                for al in [nm, *(e.get("aliases") or [])]:
                    af = fold_text(al)
                    if af:
                        conn.execute(
                            "INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded, source) "
                            "VALUES (%s, %s, %s, %s, 'user_supplied') ON CONFLICT DO NOTHING",
                            (owner, e["id"], al, af),
                        )
                        stats["aliases_inserted"] += 1

        # Seed records referenced by gold facts
        all_rids = sorted({rid for f in ledger["facts"] for rid in (f.get("evidence") or [])})
        for rid in all_rids:
            info = rec_texts.get(rid, {"source": "unknown", "at": "2026-10-20", "author": "", "text": rid})
            h = hashlib.sha256(f"{rid}|{info['text']}".encode("utf-8")).hexdigest()
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (rid, owner, info["source"], info["at"], info["author"], info["text"], h),
            )

        # Facts (filtered through engine's own pre_write gate; changed -> history, ended -> ended)
        kept_fact_ids: set[str] = set()
        for f in ledger["facts"]:
            fid = f["id"]
            txt = f["text"]
            orig = extract_text_orig(f, rec_texts)
            gate = pre_write(txt) or (pre_write(orig) if orig else None)
            if gate:
                stats["facts_quarantined_by_gate"] += 1
                if not f.get("sensitive"):
                    stats["clean_gold_facts_gated_fp"].append({"id": fid, "category": gate, "text": txt})
                if gate != "credential":
                    conn.execute(
                        "INSERT INTO quarantine (owner, category, record_ids, status) VALUES (%s, %s, %s::jsonb, 'held')",
                        (owner, gate, json.dumps(list(f.get("evidence") or []))),
                    )
                continue
            if f.get("sensitive"):
                stats["gold_sensitive_leaked_past_gate"].append({"id": fid, "text": txt})

            raw_status = f.get("status", "active")
            db_status = "history" if raw_status == "changed" else ("ended" if raw_status == "ended" else "active")
            sid = (f.get("subject_ids") or ["s_default"])[0]
            vf = f.get("valid_from") or "2026-10-20"
            vt = f.get("valid_to")
            h = hashlib.sha256(f"{sid}|{fold_text(txt)}".encode("utf-8")).hexdigest()
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_orig, text_folded, subject_id, valid_from, valid_to, "
                "status, superseded_by, provenance, content_hash) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'inferred', %s)",
                (fid, owner, txt, orig, fold_text(f"{txt} {orig or ''}"), sid, vf, vt, db_status, f.get("superseded_by"), h),
            )
            kept_fact_ids.add(fid)
            stats["facts_inserted"] += 1
            if db_status == "active":
                stats["facts_active"] += 1
            elif db_status == "history":
                stats["facts_history"] += 1
            elif db_status == "ended":
                stats["facts_ended"] += 1

            for eid in [*(f.get("person_ids") or []), *(f.get("org_ids") or []), *(f.get("place_ids") or [])]:
                conn.execute(
                    "INSERT INTO fact_entities (owner, fact_id, entity_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (owner, fid, eid),
                )
            for rid in dict.fromkeys(f.get("evidence") or []):
                conn.execute(
                    "INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) "
                    "VALUES (%s, %s, %s, 0) ON CONFLICT DO NOTHING",
                    (owner, fid, rid),
                )

        # Links (only when src/dst exist in entities table)
        ent_ids_in_db = {
            r["id"] for r in conn.execute("SELECT id FROM entities WHERE owner = %s", (owner,)).fetchall()
        }
        for ed in ledger.get("edges") or []:
            if ed["src"] in ent_ids_in_db and ed["dst"] in ent_ids_in_db:
                conn.execute(
                    "INSERT INTO links (id, owner, src, rel, dst, valid_from, valid_to) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (ed["id"], owner, ed["src"], ed["rel"], ed["dst"], ed.get("valid_from"), ed.get("valid_to")),
                )
                stats["links_inserted"] += 1

        # Recompute derived entity_subjects & subject fact_count
        conn.execute(
            """
            INSERT INTO entity_subjects (owner, entity_id, subject_id, role, weight, fact_count, first_seen, last_seen)
            SELECT vf.owner, fe.entity_id, vf.subject_id, COALESCE(fe.role, ''),
                   SUM(CASE WHEN vf.status = 'active' THEN 1.0 ELSE 0.3 END),
                   COUNT(*)::int, MIN(vf.valid_from), MAX(vf.valid_from)
            FROM visible_facts vf
            JOIN fact_entities fe ON fe.owner = vf.owner AND fe.fact_id = vf.id
            WHERE vf.owner = %s
            GROUP BY vf.owner, fe.entity_id, vf.subject_id, COALESCE(fe.role, '')
            """,
            (owner,),
        )
        conn.execute(
            """
            UPDATE subjects s SET fact_count = COALESCE((
                SELECT COUNT(*)::int FROM visible_facts vf WHERE vf.owner = s.owner AND vf.subject_id = s.id
            ), 0) WHERE s.owner = %s
            """,
            (owner,),
        )
        conn.execute("UPDATE owners SET facts_version = 1, alias_version = 1 WHERE id = %s", (owner,))
    return stats


def dump_graph_snapshot(db: Database, owner: str, out_path: Path) -> dict[str, Any]:
    """Serialize an owner's full Postgres graph tables so other suites can reload them."""
    with db.connection() as conn:
        owner_row = conn.execute("SELECT * FROM owners WHERE id = %s", (owner,)).fetchone()
        snap = {
            "owner": dict(owner_row) if owner_row else {},
            "records": conn.execute("SELECT * FROM records WHERE owner = %s ORDER BY id", (owner,)).fetchall(),
            "entities": conn.execute("SELECT * FROM entities WHERE owner = %s ORDER BY id", (owner,)).fetchall(),
            "entity_aliases": conn.execute("SELECT * FROM entity_aliases WHERE owner = %s", (owner,)).fetchall(),
            "subjects": conn.execute("SELECT * FROM subjects WHERE owner = %s ORDER BY id", (owner,)).fetchall(),
            "facts": conn.execute("SELECT * FROM facts WHERE owner = %s ORDER BY id", (owner,)).fetchall(),
            "fact_entities": conn.execute("SELECT * FROM fact_entities WHERE owner = %s", (owner,)).fetchall(),
            "fact_evidence": conn.execute("SELECT * FROM fact_evidence WHERE owner = %s", (owner,)).fetchall(),
            "links": conn.execute("SELECT * FROM links WHERE owner = %s ORDER BY id", (owner,)).fetchall(),
            "entity_subjects": conn.execute("SELECT * FROM entity_subjects WHERE owner = %s", (owner,)).fetchall(),
            "quarantine": conn.execute("SELECT * FROM quarantine WHERE owner = %s ORDER BY id", (owner,)).fetchall(),
        }
    out_path.write_text(json.dumps(snap, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    return snap


def load_graph_snapshot(db: Database, snap_path: Path) -> str:
    """Restore an owner graph snapshot into a fresh temp schema."""
    snap = json.loads(snap_path.read_text(encoding="utf-8"))
    ow = snap["owner"]
    owner = ow["id"]
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO owners (id, label, kind, display_name, self_aliases, timezone, alias_version, facts_version) "
            "VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s)",
            (
                owner, ow["label"], ow["kind"], ow.get("display_name", ""),
                json.dumps(ow.get("self_aliases") or []), ow.get("timezone", "Asia/Dubai"),
                int(ow.get("alias_version", 1)), int(ow.get("facts_version", 1)),
            ),
        )
        for r in snap["records"]:
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash, generation, erased_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (r["id"], owner, r["source"], r["at"], r.get("author", ""), r["text"], r["content_hash"],
                 int(r.get("generation", 0)), r.get("erased_at")),
            )
        for e in snap["entities"]:
            conn.execute(
                "INSERT INTO entities (id, owner, kind, name, status, relation_to_user, closeness_tier, merged_into, "
                "salience, distinct_days, first_seen, last_seen, erased_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (e["id"], owner, e["kind"], e["name"], e["status"], e.get("relation_to_user"), e.get("closeness_tier"),
                 e.get("merged_into"), float(e.get("salience", 0.0)), int(e.get("distinct_days", 1)),
                 e.get("first_seen"), e.get("last_seen"), e.get("erased_at")),
            )
        for ea in snap["entity_aliases"]:
            conn.execute(
                "INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded, lang, source) "
                "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (owner, ea["entity_id"], ea["alias"], ea["alias_folded"], ea.get("lang"), ea.get("source", "extractor")),
            )
        for s in snap["subjects"]:
            conn.execute(
                "INSERT INTO subjects (id, owner, parent_id, path, label, kind, status, salience, fact_count, distinct_days, sensitive_cat) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (s["id"], owner, s.get("parent_id"), s["path"], s["label"], s["kind"], s["status"],
                 float(s.get("salience", 0.0)), int(s.get("fact_count", 0)), int(s.get("distinct_days", 1)), s.get("sensitive_cat")),
            )
        for f in snap["facts"]:
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_orig, text_folded, lang, subject_id, valid_from, valid_to, "
                "status, superseded_by, provenance, confidence, job_id, attempt_id, worker_id, model, prompt_version, "
                "content_hash, erased_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (f["id"], owner, f["text"], f.get("text_orig"), f.get("text_folded", ""), f.get("lang"),
                 f["subject_id"], f.get("valid_from", ""), f.get("valid_to"), f["status"], f.get("superseded_by"),
                 f.get("provenance", "inferred"), f.get("confidence"), f.get("job_id"), f.get("attempt_id"),
                 f.get("worker_id"), f.get("model"), f.get("prompt_version"), f["content_hash"], f.get("erased_at")),
            )
        for fe in snap["fact_entities"]:
            conn.execute(
                "INSERT INTO fact_entities (owner, fact_id, entity_id, role) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (owner, fe["fact_id"], fe["entity_id"], fe.get("role")),
            )
        for fev in snap["fact_evidence"]:
            conn.execute(
                "INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (owner, fev["fact_id"], fev["record_id"], int(fev.get("record_generation", 0))),
            )
        for ln in snap["links"]:
            conn.execute(
                "INSERT INTO links (id, owner, src, rel, dst, valid_from, valid_to, evidence_fact_id, erased_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (ln["id"], owner, ln["src"], ln["rel"], ln["dst"], ln.get("valid_from"), ln.get("valid_to"),
                 ln.get("evidence_fact_id"), ln.get("erased_at")),
            )
        for es in snap["entity_subjects"]:
            conn.execute(
                "INSERT INTO entity_subjects (owner, entity_id, subject_id, role, weight, fact_count, first_seen, last_seen) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (owner, es["entity_id"], es["subject_id"], es.get("role", ""), float(es["weight"]),
                 int(es["fact_count"]), es["first_seen"], es["last_seen"]),
            )
        for q in snap["quarantine"]:
            conn.execute(
                "INSERT INTO quarantine (owner, category, record_ids, status) VALUES (%s,%s,%s::jsonb,%s)",
                (owner, q["category"], json.dumps(q["record_ids"]), q["status"]),
            )
    return owner


def score_probe_runs(
    probes: list[dict[str, Any]],
    hits_by_turn: dict[str, dict[str, Any]],
    *,
    extracted_to_gold: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Score per-bucket coverage, leaks (counted as failures!), and noise clean rate."""
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_probe: list[dict[str, Any]] = []

    for p in probes:
        tid = p["turn_id"]
        bucket = p.get("bucket", "unknown")
        gold_ids = set(p.get("gold_context_fact_ids") or [])
        must_not = p.get("must_not_contain") or []
        raw = hits_by_turn.get(tid) or {"ids": [], "texts": []}
        raw_ids: list[str] = list(raw.get("ids") or [])
        raw_texts: list[str] = list(raw.get("texts") or [])

        def _eval_k(k: int) -> dict[str, Any]:
            top_ids = raw_ids[:k]
            top_texts = raw_texts[:k]
            if extracted_to_gold is not None:
                matched_gold: set[str] = set()
                for eid in top_ids:
                    matched_gold.update(extracted_to_gold.get(eid, []))
                covered = len(gold_ids & matched_gold) if gold_ids else 0
            else:
                covered = len(gold_ids & set(top_ids)) if gold_ids else 0
            leaks = [m for m in must_not if any(m.lower() in t.lower() for t in top_texts)]
            if bucket == "noise":
                # Noise probes should return nothing relevant (0 items)
                cov = 1.0 if len(top_ids) == 0 else 0.0
                leak_free = len(top_ids) == 0 and not leaks
            else:
                cov = (covered / len(gold_ids)) if gold_ids else None
                leak_free = len(leaks) == 0
            return {
                "items": len(top_ids),
                "covered": covered,
                "gold_total": len(gold_ids),
                "coverage": cov,
                "leaks": leaks,
                "leak_free": leak_free,
            }

        s8 = _eval_k(8)
        s16 = _eval_k(16)
        row = {
            "turn_id": tid,
            "bucket": bucket,
            "top8": s8,
            "top16": s16,
            "latency_ms": raw.get("latency_ms", 0.0),
        }
        by_bucket[bucket].append(row)
        per_probe.append(row)

    bucket_summary: dict[str, Any] = {}
    for b, rows in sorted(by_bucket.items()):
        c8 = [r["top8"]["coverage"] for r in rows if r["top8"]["coverage"] is not None]
        c16 = [r["top16"]["coverage"] for r in rows if r["top16"]["coverage"] is not None]
        leaks8 = sum(1 for r in rows if not r["top8"]["leak_free"])
        leaks16 = sum(1 for r in rows if not r["top16"]["leak_free"])
        # Leak-adjusted effective score: 0 coverage on any leaking probe (leaks count as failures)
        eff8 = [0.0 if not r["top8"]["leak_free"] else (r["top8"]["coverage"] or 0.0) for r in rows]
        eff16 = [0.0 if not r["top16"]["leak_free"] else (r["top16"]["coverage"] or 0.0) for r in rows]
        bucket_summary[b] = {
            "n": len(rows),
            "top8_raw": round(sum(c8) / len(c8), 4) if c8 else None,
            "top16_raw": round(sum(c16) / len(c16), 4) if c16 else None,
            "top8_leak_penalized": round(sum(eff8) / len(eff8), 4) if eff8 else None,
            "top16_leak_penalized": round(sum(eff16) / len(eff16), 4) if eff16 else None,
            "leaks8": leaks8,
            "leaks16": leaks16,
        }

    non_noise = [r for r in per_probe if r["bucket"] != "noise"]
    nn8 = [r["top8"]["coverage"] for r in non_noise if r["top8"]["coverage"] is not None]
    nn16 = [r["top16"]["coverage"] for r in non_noise if r["top16"]["coverage"] is not None]
    all40_eff8 = [0.0 if not r["top8"]["leak_free"] else (r["top8"]["coverage"] or 0.0) for r in per_probe]
    all40_eff16 = [0.0 if not r["top16"]["leak_free"] else (r["top16"]["coverage"] or 0.0) for r in per_probe]
    total_leaks8 = sum(1 for r in per_probe if not r["top8"]["leak_free"])
    total_leaks16 = sum(1 for r in per_probe if not r["top16"]["leak_free"])
    sens_leaks16 = sum(1 for r in by_bucket.get("sensitive", []) if r["top16"]["leaks"])

    return {
        "overall": {
            "probes_total": len(per_probe),
            "top8_macro_38": round(sum(nn8) / len(nn8), 4) if nn8 else 0.0,
            "top16_macro_38": round(sum(nn16) / len(nn16), 4) if nn16 else 0.0,
            "top8_effective_40_with_noise_and_leak_fail": round(sum(all40_eff8) / len(all40_eff8), 4),
            "top16_effective_40_with_noise_and_leak_fail": round(sum(all40_eff16) / len(all40_eff16), 4),
            "leaks_or_noise_fail_top8": total_leaks8,
            "leaks_or_noise_fail_top16": total_leaks16,
            "sensitive_leaks_top16": sens_leaks16,
        },
        "by_bucket": bucket_summary,
        "per_probe": per_probe,
    }
