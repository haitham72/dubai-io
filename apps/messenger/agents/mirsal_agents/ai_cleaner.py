"""AI Image Cleaner jobs: thin wrapper around ai_cleaner_engine (the battle-tested script).

The engine is never modified here. This module imports it lazily (inside the
worker) so the agents service and its offline tests import cleanly on machines
without torch / remove-ai-watermarks / PIL.

Stage strings originate purely server-side. The frontend holds no stage logic:
it renders whatever GET /agents/ai-cleaner/jobs/{id} returns, verbatim.
Canonical stages: "Checking image" -> "Resizing image" -> "Cleaning AI traces"
-> faces wording -> "Presenting result".
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MODES = ("resize", "sdxl", "resize_then_sdxl")

STAGE_CHECKING = "Checking image"
STAGE_RESIZING = "Resizing image"
STAGE_CLEANING = "Cleaning AI traces"
STAGE_FACES_NONE = "No faces found"
STAGE_PRESENTING = "Presenting result"


# The faces wording is dynamic (count or fallback) and travels live in `stage`;
# the ordered list below carries the static stages only.


MODE_STAGES: dict[str, list[str]] = {
    "resize": [STAGE_CHECKING, STAGE_RESIZING, STAGE_PRESENTING],
    "sdxl": [STAGE_CHECKING, STAGE_CLEANING, STAGE_PRESENTING],
    "resize_then_sdxl": [STAGE_CHECKING, STAGE_RESIZING, STAGE_CLEANING, STAGE_PRESENTING],
}


def faces_stage(count: int | None) -> str:
    if count is None:
        return "Preserving faces"
    if count <= 0:
        return STAGE_FACES_NONE
    return f"Faces found ({count})"


_PERCENT = re.compile(r"(\d{1,3})\s*%")
_FACE_HINT = re.compile(r"face", re.IGNORECASE)
_NOISE = re.compile(r"^\s*$")


def classify_child_line(line: str) -> tuple[str | None, str | None, int | None]:
    """Map one SDXL child output line to (stage, note, percent).

    Returns (None, None, None) for lines that stay in the server-side tail only.
    Patterns are conservative on purpose; they get refined after the first real
    GPU run. Raw lines never leave the server.
    """
    text = line.strip()
    if not text or _NOISE.match(line):
        return None, None, None
    if _FACE_HINT.search(text):
        return faces_stage(None), "Preserving faces", None
    m = _PERCENT.search(text)
    if m:
        try:
            pct = max(0, min(100, int(m.group(1))))
        except ValueError:
            pct = None
        return STAGE_CLEANING, "Cleaning AI traces", pct
    lowered = text.lower()
    if "download" in lowered or "fetching" in lowered or "loading" in lowered:
        return STAGE_CLEANING, "Loading models…", None
    if len(text) > 140:
        return None, None, None
    return STAGE_CLEANING, text[:140], None


@dataclass
class CleanJob:
    id: str
    user: str
    mode: str
    stage: str = STAGE_CHECKING
    note: str = "Checking image"
    percent: int | None = None
    done: bool = False
    error: str | None = None
    workdir: Path | None = None
    cleaned: Path | None = None
    quality: dict = field(default_factory=dict)
    tail: list[str] = field(default_factory=list)


class CleanerJobs:
    """One GPU job at a time (single-worker FIFO); extras queue behind it."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, CleanJob] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ai-cleaner")

    def submit(self, user: str, filename: str, data: bytes, mode: str) -> CleanJob:
        ext = Path(filename or "").suffix.lower()
        if ext not in ALLOWED_EXTS:
            raise ValueError(f"Unsupported image type {ext or '?'}; use JPEG, PNG or WebP.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("Image is over the 50 MB limit.")
        if mode not in MODES:
            raise ValueError(f"Unknown mode {mode!r}.")
        job_id = uuid.uuid4().hex
        workdir = self.root / job_id
        workdir.mkdir(parents=True, exist_ok=True)
        original = workdir / f"original{ext}"
        original.write_bytes(data)
        job = CleanJob(id=job_id, user=user, mode=mode, workdir=workdir)
        with self._lock:
            self._jobs[job_id] = job
        self._pool.submit(self._run, job_id)
        return job

    def get(self, job_id: str) -> CleanJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def get_for(self, user: str, job_id: str) -> CleanJob | None:
        job = self.get((job_id or "")[:64])
        return job if job is not None and job.user == user else None

    def wire(self, job: CleanJob) -> dict:
        out: dict = {"id": job.id, "mode": job.mode, "stage": job.stage,
                     "note": job.note, "done": job.done,
                     "stages": MODE_STAGES.get(job.mode, MODE_STAGES["resize_then_sdxl"])}
        if job.percent is not None:
            out["percent"] = job.percent
        if job.error:
            out["error"] = job.error
        if job.done and not job.error and job.cleaned is not None:
            out["result"] = True
            out["quality"] = job.quality
        return out

    # -- worker ---------------------------------------------------------
    def _set(self, job: CleanJob, stage: str, note: str, percent: int | None = None) -> None:
        with self._lock:
            job.stage = stage
            job.note = note
            if percent is not None:
                job.percent = percent

    def _run(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None or job.workdir is None:
            return
        try:
            self._process(job)
        except Exception as err:  # noqa: BLE001 — a failed job reports, never crashes the service
            with self._lock:
                job.done = True
                job.error = f"{type(err).__name__}: {err}"[:500]

    def _process(self, job: CleanJob) -> None:
        from . import ai_cleaner_engine as eng  # lazy: keeps service importable without torch/PIL/raiw
        assert job.workdir is not None
        workdir = job.workdir
        originals = sorted(workdir.glob("original.*"))
        if not originals:
            raise RuntimeError("Upload went missing before processing started.")
        source = originals[0]
        cleaned = workdir / f"cleaned.jpg"

        self._set(job, STAGE_CHECKING, "Checking image")
        env = eng.command_env()
        try:
            cli = eng.find_cli()
        except RuntimeError as err:
            raise RuntimeError(str(err)) from err
        before = eng.inspect(cli, source, env)

        prepared = source
        if job.mode in ("resize", "resize_then_sdxl"):
            self._set(job, STAGE_RESIZING, "Resizing image")
            if job.mode == "resize":
                eng.real_resize_roundtrip(source, cleaned)
            else:
                tmpdir = Path(tempfile.mkdtemp(prefix="raiw-pre-sdxl-", dir=str(workdir)))
                prepared = tmpdir / f"prepared{source.suffix}"
                eng.real_resize_roundtrip(source, prepared)

        if job.mode in ("sdxl", "resize_then_sdxl"):
            self._set(job, STAGE_CLEANING, "Cleaning AI traces")
            try:
                eng.verify_gpu()
            except Exception as err:
                raise RuntimeError(f"GPU unavailable: {err}") from err
            with tempfile.TemporaryDirectory(prefix="raiw-sdxl-output-", dir=str(workdir)) as tmp:
                raw_output = Path(tmp) / "sdxl_output.png"
                self._run_sdxl_captured(eng, job, prepared, raw_output, env)
                self._set(job, faces_stage(None), "Preserving faces")
                with _open_image(raw_output) as result:
                    eng.write_image(result, cleaned, jpeg_quality=eng.JPEG_QUALITY)

        self._set(job, STAGE_PRESENTING, "Presenting result")
        after = eng.inspect(cli, cleaned, env)
        try:
            job.quality = eng.image_quality(source, cleaned)
        except Exception:  # noqa: BLE001 — quality is informational only
            job.quality = {}
        job.quality["signals_before"] = len((before.get("identify") or {}).get("signals") or [])
        job.quality["signals_after"] = len((after.get("identify") or {}).get("signals") or [])
        with self._lock:
            job.cleaned = cleaned
            job.done = True

    def _run_sdxl_captured(self, eng, job: CleanJob, src: Path, dest: Path, env: dict) -> None:
        """Mirror of engine.run_sdxl, but with piped stdout classified into stages.

        Reads denoise strength / pipeline / offload / resolution from the engine
        module constants so battle-tested settings stay single-sourced.
        """
        cmd = [
            sys.executable, str(Path(eng.__file__).resolve()), "--internal-sdxl",
            "invisible", str(src), "-o", str(dest),
            "--pipeline", str(eng.PIPELINE),
            "--strength", str(eng.SDXL_STRENGTH),
            "--controlnet-scale", "1.0",
            "--no-adaptive-polish", "--unsharp", "0", "--humanize", "0",
            "--max-resolution", str(eng.MAX_RESOLUTION),
            "--seed", "0", "--force",
        ]
        if eng.CPU_OFFLOAD:
            cmd.append("--cpu-offload")
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace", bufsize=1)
        assert proc.stdout is not None
        for line in proc.stdout:
            with self._lock:
                job.tail.append(line.rstrip("\n"))
                del job.tail[:-200]
            stage, note, pct = classify_child_line(line)
            if stage is not None:
                if stage == faces_stage(None):
                    self._set(job, stage, note or stage)
                else:
                    with self._lock:
                        job.stage, job.note = stage, note or stage
                        if pct is not None:
                            job.percent = pct
        code = proc.wait()
        if code:
            raise RuntimeError(f"SDXL failed with exit code {code}; see server logs.")
        if not dest.is_file() or dest.stat().st_size == 0:
            raise RuntimeError(f"SDXL finished but output was not found: {dest}")


def _open_image(path: Path):
    from PIL import Image  # lazy: PIL lives in the GPU env, not the test env
    return Image.open(path)


OPENAI_PROVENANCE_URL = "https://api.openai.com/v1/content_provenance_checks"


def _signal(value: object) -> str:
    text = str(value or "").strip().lower()
    if text in ("detected", "true", "positive", "found"):
        return "detected"
    if text in ("not_detected", "not detected", "false", "negative", "not_found", "not found", "none"):
        return "not_detected"
    return "unknown"


def _find_signal(payload: object, *names: str) -> object:
    """Look for a signal value under likely keys, one nesting level deep. Never invents."""
    if isinstance(payload, dict):
        lowered = {str(k).lower(): v for k, v in payload.items()}
        for name in names:
            if name in lowered:
                v = lowered[name]
                return v.get("status", v) if isinstance(v, dict) else v
        for v in payload.values():
            found = _find_signal(v, *names)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for v in payload:
            found = _find_signal(v, *names)
            if found is not None:
                return found
    return None


async def verify_with_openai(api_key: str, data: bytes, filename: str) -> dict:
    """Official Content Provenance check. Maps the real response; unknown fields stay unknown."""
    import httpx2 as httpx  # ships with the openai SDK (no extra dependency)
    ext = Path(filename or "").suffix.lower()
    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                OPENAI_PROVENANCE_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename or "image.jpg", data, media)},
            )
    except Exception as err:  # noqa: BLE001 — network failure is a 502, not a crash
        raise RuntimeError(f"OpenAI verification unreachable ({type(err).__name__})") from err
    if resp.status_code in (401, 403):
        raise PermissionError("OpenAI rejected the API key.")
    if resp.status_code == 429:
        raise RuntimeError("OpenAI rate limit reached; try again later.")
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenAI verification failed (HTTP {resp.status_code}).")
    try:
        payload = resp.json()
    except Exception as err:  # noqa: BLE001
        raise RuntimeError("OpenAI returned an unreadable response.") from err
    return map_provenance(payload)


def map_provenance(payload: object) -> dict:
    """Pure mapping of a real provenance response. Unknown fields stay unknown."""
    c2pa = _signal(_find_signal(payload, "c2pa", "content_credentials", "contentcredentials"))
    synthid = _signal(_find_signal(payload, "synthid", "synth_id", "synth-id", "watermark"))
    overall = ("no_supported_openai_signal_detected" if c2pa == "not_detected" and synthid == "not_detected"
               else "checked")
    return {"provider": "openai", "status": "completed",
            "results": {"c2pa": c2pa, "synthid": synthid}, "overall": overall}
