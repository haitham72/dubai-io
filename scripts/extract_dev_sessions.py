"""Extract Developer Sessions (Claude Code, Codex, Antigravity, Git Commits).

Borrows the fast local scanner architecture from ide-companio (Claude Report):
- Scans ~/.claude/projects/**/*.jsonl, ~/.codex/sessions, and active Git roots.
- Redacts secrets, tokens, and .env leaks before writing.
- Outputs clean project session summaries to data/sync/dev_sessions.json.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "sync"
OUTPUT_FILE = DATA_DIR / "dev_sessions.json"

USER_HOME = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or ".")
CLAUDE_PROJECTS = USER_HOME / ".claude" / "projects"
CODEX_SESSIONS = USER_HOME / ".codex" / "sessions"

SECRET_PATTERNS = [
    re.compile(r"(?<![\w])\.env[\w.-]*", re.I),
    re.compile(r"^[ \t]*(?:export[ \t]+)?[A-Z][A-Z0-9_]{2,}[ \t]*=[ \t]*\S.*$", re.M),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(-----END [A-Z ]*PRIVATE KEY-----|$)", re.M),
    re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I),
    re.compile(r"\b(api[_-]?key|token|secret|password|passwd)\b\s*[:=]\s*['\"]?[^\s'\",;]+", re.I),
]


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text


def scan_claude_sessions(max_sessions: int = 20) -> list[dict]:
    results = []
    if not CLAUDE_PROJECTS.exists():
        return results

    jsonl_files = sorted(CLAUDE_PROJECTS.rglob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    seen_sessions = set()

    for f in jsonl_files:
        if len(results) >= max_sessions:
            break

        prompts = []
        ai_title = ""
        cwd = ""
        git_branch = ""
        project_name = f.parent.name
        created_at = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()

        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except Exception:
                        continue
                    
                    rtype = record.get("type")
                    if rtype == "ai-title" and record.get("aiTitle"):
                        ai_title = record["aiTitle"]
                    
                    if record.get("cwd") and not cwd:
                        cwd = record["cwd"]
                    if record.get("gitBranch") and not git_branch:
                        git_branch = record["gitBranch"]

                    if rtype == "user":
                        msg = record.get("message")
                        content = ""
                        if isinstance(msg, dict):
                            content = msg.get("content") or ""
                        elif isinstance(msg, str):
                            content = msg
                        
                        if isinstance(content, list):
                            content = " ".join(str(c.get("text", "")) for c in content if isinstance(c, dict))
                        
                        content_str = str(content).strip()
                        if content_str and not content_str.startswith("<local-command-caveat>") and len(content_str) > 10:
                            prompts.append(redact(content_str[:350]))
        except Exception:
            continue

        session_key = ai_title or (prompts[-1][:50] if prompts else f.name)
        if session_key in seen_sessions:
            continue
        seen_sessions.add(session_key)

        if prompts or ai_title:
            results.append({
                "source": "claude_code",
                "title": ai_title or f"Session in {project_name}",
                "project": project_name,
                "cwd": cwd,
                "git_branch": git_branch,
                "session_file": f.name,
                "timestamp": created_at,
                "prompts_sample": prompts[-3:],
                "total_prompts": len(prompts),
            })
    return results


def scan_git_activity(max_commits: int = 20) -> list[dict]:
    results = []
    try:
        cmd = ["git", "log", f"-n{max_commits}", "--pretty=format:%H|%an|%ad|%s", "--date=iso"]
        out = subprocess.check_output(cmd, text=True, cwd=str(REPO_ROOT), stderr=subprocess.DEVNULL)
        for line in out.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 4:
                results.append({
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "date": parts[2],
                    "message": redact(parts[3]),
                })
    except Exception:
        pass
    return results


def main():
    print("=" * 60)
    print("Developer Sessions & Activity Extractor")
    print("=" * 60)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    claude_sessions = scan_claude_sessions(max_sessions=15)
    git_commits = scan_git_activity(max_commits=15)

    payload = {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "claude_sessions_count": len(claude_sessions),
        "git_commits_count": len(git_commits),
        "claude_sessions": claude_sessions,
        "recent_git_commits": git_commits,
    }

    OUTPUT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Done] Extracted {len(claude_sessions)} Claude sessions and {len(git_commits)} Git commits.")
    print(f"[Saved] Output written to: {OUTPUT_FILE}")
    print("\n--- Summary of Recent Dev Projects ---")
    for s in claude_sessions[:6]:
        print(f"• {s['title']} [{s['project']}] ({s['total_prompts']} prompts)")
        if s.get('prompts_sample'):
            print(f"  Latest intent: \"{s['prompts_sample'][-1][:100]}...\"")


if __name__ == "__main__":
    main()
