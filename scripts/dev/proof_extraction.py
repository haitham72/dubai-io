"""E1b proof: synthetic owner -> memory engine ingest -> HOST worker (claude -p) -> facts -> cost -> Forget.
Synthetic data only. Reads TM_ADMIN_TOKEN from apps/memory/.env, never prints it. Needs start-all running."""
import json, os, subprocess, sys, time, urllib.request, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = os.environ.get("TM_BASE_URL", "http://localhost:8040")


def env_value(name):
    for line in (ROOT / "apps/memory/.env").read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"{name} missing in apps/memory/.env")


def call(method, path, token, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"{}")


def sql(q):
    out = subprocess.run(["docker", "compose", "-f", str(ROOT / "apps/memory/docker-compose.yml"), "exec", "-T", "postgres",
                          "psql", "-U", "tm", "-d", "tm", "-t", "-A", "-F", "|", "-c", q], capture_output=True, text=True)
    return out.stdout.strip()


admin = env_value("TM_ADMIN_TOKEN")
owner = "synthetic-e1b-" + uuid.uuid4().hex[:6]
call("POST", "/v1/owners", admin, {"id": owner, "label": "E1b synthetic", "kind": "simulated", "display_name": "Karim (synthetic)",
                                    "self_aliases": [], "timezone": "Asia/Dubai"})
tok = call("POST", "/v1/tokens", admin, {"role": "owner-device", "owner": owner, "label": "e1b-proof"})
otoken, tid = tok["token"], tok.get("id")
rid = "rec-" + uuid.uuid4().hex[:6]
text = ("Karim (synthetic) wrote on 2026-11-20: I started a weekend padel league at Dubai Sports City with my colleague "
        "Lina. I moved to a new flat in Dubai Marina last month. I want to learn Arabic calligraphy and signed up for "
        "a class at Alserkal Avenue starting 5 December.")
res = call("POST", f"/v1/owners/{owner}/records", otoken, {"records": [{"id": rid, "source": "note", "at": "2026-11-20T09:00:00+04:00",
          "author": "Karim", "text": text}], "enqueue": "extract.day"})
print("ingest:", {k: res.get(k) for k in ("ok", "job_id", "record_ids")})
t0 = time.time(); seen = []
while time.time() - t0 < 300:
    rows = sql(f"SELECT id,kind,state FROM jobs WHERE owner='{owner}' ORDER BY created_at")
    if rows not in seen:
        seen.append(rows); print(f"t+{int(time.time()-t0)}s jobs:", rows.replace("\n", " ; "))
    if rows and all(r.split("|")[2] in ("applied", "done", "failed", "dead") for r in rows.splitlines()):
        break
    time.sleep(3)
print("attempts (job|worker_kind|model|model_observed|tokens_in|tokens_out|cost_usd|verdict):")
print(sql(f"SELECT job_id,worker_kind,model,model_observed,tokens_in,tokens_out,cost_usd,verdict FROM job_attempts WHERE owner='{owner}'"))
print("facts:", sql(f"SELECT count(*) FROM facts WHERE owner='{owner}'"), "| sample provenance:",
      sql(f"SELECT provenance,count(*) FROM facts WHERE owner='{owner}' GROUP BY 1").replace("\n", ";"))
fr = call("POST", f"/v1/owners/{owner}/forget", otoken, {"record_ids": [rid]})
print("forget:", fr)
print("after forget (unerased): records", sql(f"SELECT count(*) FROM records WHERE owner='{owner}' AND erased_at IS NULL"),
      "unerased facts", sql(f"SELECT count(*) FROM facts WHERE owner='{owner}' AND erased_at IS NULL"))
if tid:
    try: call("DELETE", f"/v1/tokens/{tid}", admin)
    except Exception as e: print("token revoke:", e)
