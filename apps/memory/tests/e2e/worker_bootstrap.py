"""Container entry point for the Docker tests only."""

from oracle_runner import install
from race_runner import install as install_races

from temporal_memory.queue.celery_app import celery_app as app


install()
install_races()
for entry in app.conf.beat_schedule.values():
    if entry["task"] == "memory.reconcile":
        entry["schedule"] = 1.0
