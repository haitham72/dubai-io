"""Worker instrumentation for synthetic queue races, installed by tests only."""

from datetime import datetime, timezone
import time

from celery.signals import task_postrun
import psycopg

from temporal_memory.config import get_settings
from temporal_memory.models import Attempt, ExtractionOutput, OutFact


RACE_SOURCE = "notes:e2e-race"
DUPLICATE_TASK_PREFIX = "tm-e2e-duplicate-"
MODEL = "gold-oracle"


def install():
    from temporal_memory.core import extract

    gold_run = extract.run
    observed_jobs = set()

    def run(bundle, runner, model):
        records = [record for record in bundle.records if record.source == RACE_SOURCE]
        if not records:
            return gold_run(bundle, runner, model)
        if runner != "oracle" or model != MODEL or len(records) != 1:
            raise ValueError("The queue race runner expects one synthetic record and the oracle")

        job = bundle.job
        record = records[0]
        observed_jobs.add(job.id)
        started = datetime.now(timezone.utc)
        with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO tm_e2e_race_calls (job_id, attempt_no, fence_token, worker_id) "
                "VALUES (%s, %s, %s, %s)",
                (job.id, job.attempt_no, job.fence_token, job.worker_id),
            )
            deadline = time.monotonic() + 35
            while conn.execute(
                "SELECT 1 FROM tm_e2e_race_gates WHERE record_id = %s AND attempt_no = %s",
                (record.id, job.attempt_no),
            ).fetchone():
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Queue race gate still closed for {job.id}")
                time.sleep(0.05)

        output = ExtractionOutput(entities=[], links=[], facts=[OutFact(
            text=record.text,
            text_orig=None,
            subject_path="Culture/Ceramics",
            entities=[],
            op="new",
            target=None,
            valid_from=record.at,
            evidence=[record.id],
            sensitive=None,
        )])
        return Attempt(
            job_id=job.id,
            attempt_no=job.attempt_no,
            fence_token=job.fence_token,
            worker_id=job.worker_id,
            worker_kind="agent-cli",
            model=model,
            prompt_version=job.prompt_version,
            output=output,
            started_at=started.isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    def record_outcome(sender, task_id, args, retval, state, **_):
        if sender.name != "memory.run_job" or not args:
            return
        job_id = args[0]
        if job_id not in observed_jobs and not task_id.startswith(DUPLICATE_TASK_PREFIX):
            return
        observed_jobs.discard(job_id)
        status = retval.get("status", state) if isinstance(retval, dict) else state
        with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO tm_e2e_race_outcomes (task_id, job_id, status) VALUES (%s, %s, %s)",
                (task_id, job_id, status),
            )

    extract.run = run
    task_postrun.connect(record_outcome, weak=False)
