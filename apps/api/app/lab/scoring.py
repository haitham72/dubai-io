"""The two local scoring models, behind one small interface.

  sentiment  cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual   polarity -> -1..1 (p_positive - p_negative)
  emotion    AnasAlokla/multilingual_go_emotions                          multi-label, keep scores >= 0.45

They are classifiers, not the extraction LLM: the LLM is never asked for a feeling. Scores are stored with
the model ids that produced them. When the scorers cannot run (no torch, models missing, LAB_SCORERS=off)
every score stays null and the row says why - a number is never invented to fill the gap (rule 1/2).
The API venv has no torch, so a worker subprocess (scorer_worker.py) runs under LAB_SCORER_PYTHON
(default: the base interpreter) and is kept alive for the whole run.
"""
from __future__ import annotations

import atexit
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from app.config import settings

STARTUP_TIMEOUT = 300  # first run loads two transformer models
REQUEST_TIMEOUT = 300
WORKER = Path(__file__).with_name("scorer_worker.py")


class NullScorer:
    available = False

    def __init__(self, reason: str):
        self.reason = reason

    def score(self, texts: list[str]) -> list[dict | None]:
        return [None] * len(texts)

    def info(self) -> dict:
        return {"status": "unavailable", "reason": self.reason}


class SubprocessScorer:
    def __init__(self, python: str | None = None):
        base = Path(sys.base_prefix) / ("python.exe" if os.name == "nt" else "bin/python3")
        self.python = python or settings.lab_scorer_python or str(base)
        self.proc: subprocess.Popen | None = None
        self.lines: queue.Queue = queue.Queue()
        self.reason = ""
        self.available = True

    def _read(self, timeout: float) -> dict:
        """Wait for one JSON line; fail fast (with the worker's last stderr) if the process has died."""
        waited = 0.0
        while waited < timeout:
            try:
                return json.loads(self.lines.get(timeout=1))
            except queue.Empty:
                waited += 1
                if self.proc is not None and self.proc.poll() is not None and self.lines.empty():
                    raise RuntimeError(f"scorer worker exited with code {self.proc.returncode}: {self._stderr_tail()}")
        raise TimeoutError("scorer worker did not answer in time")

    def _stderr_tail(self) -> str:
        try:
            self.err.flush()
            self.err.seek(0)
            return " ".join(self.err.read().decode("utf-8", "replace").strip().splitlines()[-3:])[-300:]
        except Exception:
            return ""

    def _start(self) -> None:
        env = {**os.environ, "LAB_SENTIMENT_MODEL": settings.sentiment_model, "LAB_EMOTION_MODEL": settings.lab_emotion_model,
               "LAB_EMOTION_THRESHOLD": str(settings.lab_emotion_threshold), "PYTHONIOENCODING": "utf-8",
               "PYTHONSAFEPATH": "1"}  # keep the script folder off sys.path; NOT -I, which would hide user site-packages (torch)
        self.err = tempfile.TemporaryFile()
        self.proc = subprocess.Popen([self.python, str(WORKER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.err, text=True, encoding="utf-8", env=env)
        threading.Thread(target=lambda: [self.lines.put(x) for x in self.proc.stdout], daemon=True).start()
        if not self._read(STARTUP_TIMEOUT).get("ready"):
            raise RuntimeError("scorer worker did not report ready")
        atexit.register(self.close)

    def score(self, texts: list[str]) -> list[dict | None]:
        if not texts or not self.available:
            return [None] * len(texts)
        try:
            if self.proc is None:
                self._start()
            self.proc.stdin.write(json.dumps({"texts": texts}) + "\n")
            self.proc.stdin.flush()
            res = self._read(REQUEST_TIMEOUT)
            if "error" in res:
                raise RuntimeError(res["error"])
            return res["results"]
        except Exception as exc:  # no torch, model missing, crash: scores stay null, honestly
            self.available = False
            self.reason = f"{type(exc).__name__}: {exc}"[:300]
            self.close()
            return [None] * len(texts)

    def info(self) -> dict:
        if not self.available:
            return {"status": "unavailable", "reason": self.reason}
        return {"status": "ok", "sentiment_model": settings.sentiment_model, "emotion_model": settings.lab_emotion_model,
                "emotion_threshold": settings.lab_emotion_threshold}

    def close(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        self.proc = None


_scorer = None


def get_scorer():
    global _scorer
    if _scorer is None:
        _scorer = NullScorer("disabled (LAB_SCORERS=off)") if settings.lab_scorers == "off" else SubprocessScorer()
    return _scorer


def set_scorer(scorer) -> None:
    """Tests and callers inject their own (or None to reset)."""
    global _scorer
    _scorer = scorer


def aggregate(per_text: list[dict | None]) -> dict | None:
    """Mean sentiment over the texts; for each emotion, the strongest score seen. None if nothing was scored."""
    got = [x for x in per_text if x]
    if not got:
        return None
    emotions: dict[str, float] = {}
    for x in got:
        for label, v in x["emotions"].items():
            emotions[label] = max(v, emotions.get(label, 0.0))
    return {"sentiment": round(sum(x["sentiment"] for x in got) / len(got), 2), "emotions": dict(sorted(emotions.items())),
            "n": len(got)}


def score_groups(groups: dict[str, list[str]]) -> tuple[dict[str, dict | None], dict]:
    """groups: {"owner": [texts], "other": [texts]} -> ({group: aggregate|None}, scorer info)."""
    scorer = get_scorer()
    out: dict[str, dict | None] = {}
    for name, texts in groups.items():
        out[name] = aggregate(scorer.score(texts)) if texts else None
    return out, scorer.info()
