"""Run opt-in integration tests in an isolated Docker Compose project."""

from __future__ import annotations

import os
from pathlib import Path
import secrets
import subprocess
import time
from uuid import uuid4

from celery import Celery
import httpx
import pytest

from temporal_memory.db.db import Database
from temporal_memory.queue.jobs import PostgresJobs


MEMORY_DIR = Path(__file__).resolve().parents[2]
TERMINAL = {"applied", "rejected", "dead"}


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: real RabbitMQ, Celery and Postgres in isolated Docker Compose")
    config.addinivalue_line("markers", "live_llm: one billable synthetic day through a local Claude CLI")


def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_closest_marker("live_llm"):
            if os.environ.get("TM_RUN_LIVE_LLM") != "1":
                item.add_marker(pytest.mark.skip(reason="set TM_RUN_LIVE_LLM=1 to allow one live synthetic call"))
        elif item.get_closest_marker("e2e") and os.environ.get("TM_RUN_E2E") != "1":
            item.add_marker(pytest.mark.skip(reason="set TM_RUN_E2E=1 to run Docker integration tests"))


class Stack:
    def __init__(self, gold_dir: Path):
        self.project = f"tm-wpe-{uuid4().hex[:12]}"
        self.env = {
            **os.environ,
            "TM_E2E_GOLD_DIR": str(gold_dir),
            "TM_E2E_ADMIN_TOKEN": secrets.token_urlsafe(24),
        }
        self.timeout = float(os.environ.get("TM_E2E_TIMEOUT", "90"))

    def compose(self, *args, check=True, timeout=90) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["docker", "compose", "-p", self.project, "-f", "docker-compose.yml",
             "-f", "tests/e2e/compose.yml", *args],
            cwd=MEMORY_DIR,
            env=self.env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if check and result.returncode:
            raise RuntimeError(f"Docker Compose {args[0]} failed\n{result.stdout}\n{result.stderr}")
        return result

    def port(self, service: str, container_port: int) -> int:
        address = self.compose("port", service, str(container_port)).stdout.strip()
        return int(address.rsplit(":", 1)[1])

    def start(self):
        self.compose("up", "-d", "--build", "--wait", "--wait-timeout", "120",
                     "api", "worker-p0", "worker-p1", "beat", timeout=600)
        self.db = Database(f"postgresql://tm:tm@127.0.0.1:{self.port('postgres', 5432)}/tm")
        self.jobs = PostgresJobs(self.db)
        self.api = httpx.Client(
            base_url=f"http://127.0.0.1:{self.port('api', 8040)}",
            headers={"Authorization": f"Bearer {self.env['TM_E2E_ADMIN_TOKEN']}"},
            trust_env=False,
        )
        self.broker = Celery(broker=f"amqp://guest:guest@127.0.0.1:{self.port('rabbitmq', 5672)}//")
        health = self.api.get("/health")
        health.raise_for_status()
        hj = health.json()
        assert hj["ok"] is True and hj["db"] == "ok"

    def owner(self, display_name: str = "Synthetic Owner", *, self_aliases=()) -> str:
        owner_id = f"e2e_{uuid4().hex}"
        response = self.api.post("/v1/owners", json={
            "id": owner_id,
            "label": display_name,
            "kind": "simulated",
            "display_name": display_name,
            "self_aliases": list(self_aliases),
        })
        response.raise_for_status()
        assert response.json()["id"] == owner_id
        return owner_id

    def rows(self, sql, params=()):
        # Explicit scope keeps repeated test polling out of idle transactions.
        with self.db.transaction() as conn:
            return conn.execute(sql, params).fetchall()

    def wait(self, predicate, *, description="condition", timeout=None):
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        while time.monotonic() < deadline:
            result = predicate()
            if result:
                return result
            time.sleep(0.15)
        logs = self.compose("logs", "--tail", "24", "worker-p0", "worker-p1", "beat", check=False)
        pytest.fail(f"Timed out waiting for {description}\n{logs.stdout}")

    def wait_job(self, job_id, *states, timeout=None):
        def reached_state():
            rows = self.rows("SELECT * FROM jobs WHERE id = %s", (job_id,))
            if not rows:
                return None
            row = rows[0]
            if row["state"] in states:
                return row
            if row["state"] in TERMINAL:
                attempts = self.rows("SELECT model, verdict FROM job_attempts WHERE job_id = %s", (job_id,))
                pytest.fail(f"Job {job_id} ended as {row['state']}, expected {states}: {attempts}")
            return None

        return self.wait(reached_state, description=f"{job_id} to reach {states}", timeout=timeout)

    def close(self):
        for name in ("broker", "api", "db"):
            client = getattr(self, name, None)
            if client is not None:
                client.close()
        self.compose("down", "--volumes", check=True)


@pytest.fixture(scope="session")
def stack():
    gold_dir = os.environ.get("TM_E2E_GOLD_DIR")
    if not gold_dir or not (Path(gold_dir) / "ledger.json").is_file():
        pytest.fail("TM_E2E_GOLD_DIR must point to the synthetic gold directory containing ledger.json")

    harness = Stack(Path(gold_dir).resolve())
    try:
        harness.start()
        yield harness
    finally:
        harness.close()
