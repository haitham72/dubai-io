"""AI Image Cleaner: validation, stage flow, isolation, and the conditional verify endpoint.

Offline and socket-free: the engine (torch / remove-ai-watermarks / PIL) is never
imported here, and no event loop is needed. The worker's _process is faked;
route wiring is asserted through the registered paths (the handlers themselves
are thin: get_for + wire + FileResponse).
"""
import time
from dataclasses import replace
from pathlib import Path

import pytest

from mirsal_agents import ai_cleaner as ac
from mirsal_agents.app import Services, build_app
from mirsal_agents.config import Settings
from mirsal_agents.store import MemoryStore

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200


@pytest.fixture
def jobs(tmp_path):
    return ac.CleanerJobs(tmp_path / "ai-cleaner")


def fake_process_done(self, job):
    out = Path(job.workdir) / "cleaned.jpg"
    out.write_bytes(JPEG)
    with self._lock:
        job.stage, job.note = ac.STAGE_PRESENTING, "Presenting result"
        job.quality = {"psnr_db": 42.5, "signals_before": 3, "signals_after": 0}
        job.cleaned, job.done = out, True


def wait_done(job, timeout_s=10.0):
    end = time.time() + timeout_s
    while time.time() < end:
        if job.done:
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish in time")


def test_rejects_non_image_bad_mode_and_oversize(jobs, monkeypatch):
    monkeypatch.setattr(ac.CleanerJobs, "_process", lambda self, job: None)
    with pytest.raises(ValueError):
        jobs.submit("me", "t.txt", b"hello", "resize")
    with pytest.raises(ValueError):
        jobs.submit("me", "t.jpg", JPEG, "nope")
    monkeypatch.setattr(ac, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(ValueError):
        jobs.submit("me", "t.jpg", JPEG, "resize")


def test_full_job_flow_with_faked_worker(jobs, monkeypatch):
    seen = []

    def fake(self, job):
        seen.append(job.mode)
        fake_process_done(self, job)

    monkeypatch.setattr(ac.CleanerJobs, "_process", fake)
    job = jobs.submit("me", "t.jpg", JPEG, "resize")
    wait_done(job)
    wired = jobs.wire(job)
    assert wired["done"] and wired["result"] is True
    assert wired["quality"]["signals_before"] == 3 and wired["quality"]["signals_after"] == 0
    assert seen == ["resize"]
    assert job.cleaned is not None and job.cleaned.read_bytes().startswith(b"\xff\xd8\xff")


def test_wire_includes_ordered_stages_per_mode(jobs, monkeypatch):
    monkeypatch.setattr(ac.CleanerJobs, "_process", lambda self, job: None)
    for mode, expected in {
        "resize": ["Checking image", "Resizing image", "Presenting result"],
        "sdxl": ["Checking image", "Cleaning AI traces", "Presenting result"],
        "resize_then_sdxl": ["Checking image", "Resizing image", "Cleaning AI traces", "Presenting result"],
    }.items():
        job = jobs.submit("me", "t.jpg", JPEG, mode)
        assert jobs.wire(job)["stages"] == expected


def test_failed_worker_reports_instead_of_crashing(jobs, monkeypatch):
    monkeypatch.setattr(ac.CleanerJobs, "_process",
                        lambda self, job: (_ for _ in ()).throw(RuntimeError("mocked GPU blew up")))
    job = jobs.submit("me", "t.jpg", JPEG, "sdxl")
    wait_done(job)
    assert job.done and "mocked GPU blew up" in (job.error or "")
    assert "result" not in jobs.wire(job)


def test_jobs_are_isolated_per_user(jobs, monkeypatch):
    monkeypatch.setattr(ac.CleanerJobs, "_process", lambda self, job: None)
    job = jobs.submit("me", "t.jpg", JPEG, "resize")
    assert jobs.get_for("me", job.id) is job
    assert jobs.get_for("someone-else", job.id) is None
    assert jobs.get_for("me", "nope") is None
    assert jobs.get_for("me", "x" * 200) is None


def test_concurrent_submits_get_distinct_ids(jobs, monkeypatch):
    import threading
    monkeypatch.setattr(ac.CleanerJobs, "_process", lambda self, job: None)
    ids, lock = set(), threading.Lock()

    def submit():
        with lock:
            ids.add(jobs.submit("me", "t.jpg", JPEG, "resize").id)

    threads = [threading.Thread(target=submit) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(ids) == 2


def app_paths(**overrides):
    cfg = replace(Settings(), live=False, watch_enabled=False, budget_usd=1.0, **overrides)
    return [r.path for r in build_app(Services(cfg, MemoryStore())).routes]


def test_routes_registered_without_verify_without_key(tmp_path):
    # Explicit empty key: the repo .env may carry a real one, which must not leak into this assertion.
    paths = app_paths(data_dir=tmp_path, openai_key="",
                      gmail_client_file=tmp_path / "none.json", gmail_token_file=tmp_path / "token.json")
    assert "/agents/ai-cleaner/jobs" in paths
    assert "/agents/ai-cleaner/jobs/{job_id}" in paths
    assert "/agents/ai-cleaner/jobs/{job_id}/file" in paths
    assert "/agents/ai-cleaner/capabilities" in paths
    assert "/agents/ai-cleaner/verify" not in paths


def test_verify_route_exists_only_with_key(tmp_path):
    paths = app_paths(data_dir=tmp_path, openai_key="test-key",
                      gmail_client_file=tmp_path / "none.json", gmail_token_file=tmp_path / "token.json")
    assert "/agents/ai-cleaner/verify" in paths


def test_provenance_mapping_never_invents():
    assert ac.map_provenance({"results": {"c2pa": "not_detected", "synthid": "not_detected"}}) == {
        "provider": "openai", "status": "completed",
        "results": {"c2pa": "not_detected", "synthid": "not_detected"},
        "overall": "no_supported_openai_signal_detected"}
    mixed = ac.map_provenance({"c2pa": {"status": "detected"}, "other": [{"synthID": "bogus"}]})
    assert mixed["results"] == {"c2pa": "detected", "synthid": "unknown"}
    assert mixed["overall"] == "checked"
    assert ac.map_provenance({"unrelated": True})["results"] == {"c2pa": "unknown", "synthid": "unknown"}


def test_classifier_groups_child_flood_into_stages():
    assert ac.classify_child_line(" 50%|████ | 5/10 [00:03]") == ("Cleaning AI traces", "Cleaning AI traces", 50)
    stage, note, _ = ac.classify_child_line("Downloading weights (4.2 GB)…")
    assert (stage, note) == ("Cleaning AI traces", "Loading models…")
    stage, note, _ = ac.classify_child_line("Face 2/3 restored in 0.4s")
    assert stage == "Preserving faces"
    assert ac.classify_child_line("") == (None, None, None)
    assert ac.classify_child_line("x" * 500) == (None, None, None)
    assert ac.faces_stage(2) == "Faces found (2)"
    assert ac.faces_stage(0) == "No faces found"
    assert ac.faces_stage(None) == "Preserving faces"


def test_signal_mapping_never_invents():
    assert ac._signal("detected") == "detected"
    assert ac._signal("not detected") == "not_detected"
    assert ac._signal("weird-new-value") == "unknown"
    assert ac._signal(None) == "unknown"
    payload = {"results": {"c2pa": {"status": "not_detected"}, "nested": [{"synthID": "detected"}]}}
    assert ac._find_signal(payload, "c2pa") == "not_detected"
    assert ac._find_signal(payload, "synthid") == "detected"
    assert ac._find_signal(payload, "nope") is None
    assert ac._find_signal({"a": 1}, "c2pa") is None


def test_cleaner_config_defaults_match_old_engine_constants():
    from mirsal_agents.config import Cleaner
    assert Cleaner() == Cleaner()  # frozen value object
    assert Settings().cleaner.mode == "resize_then_sdxl"
    c = Cleaner()
    assert (c.mode, c.resize_multiplier, c.jpeg_quality, c.output_format) == ("resize_then_sdxl", 2, 95, "jpg")
    assert (c.sdxl_strength, c.sdxl_effective_steps, c.cpu_offload, c.max_resolution) == (0.01, 2, True, 2024)
    assert (c.allow_model_downloads, c.pipeline) == (True, "sdxl-zimage")


def test_cleaner_config_env_overrides(monkeypatch):
    from mirsal_agents.config import Cleaner
    monkeypatch.setenv("CLEANER_MODE", "sdxl")
    monkeypatch.setenv("CLEANER_SDXL_STRENGTH", "0.2")
    monkeypatch.setenv("CLEANER_CPU_OFFLOAD", "0")
    c = Cleaner()
    assert (c.mode, c.sdxl_strength, c.cpu_offload) == ("sdxl", 0.2, False)
