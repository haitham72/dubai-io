"""Register Messenger capabilities into the shared action registry at import time."""

from app.actions import CAPABILITIES, Capability

TASK = "workspace.task.create"

if TASK not in CAPABILITIES:
    CAPABILITIES[TASK] = Capability(
        TASK,
        "Create a workspace task",
        ("title", "assignee", "due", "evidence_message_ids"),
        ("title", "assignee", "due", "evidence_message_ids"),
        "This group's task list",
        "No workspace adapter is connected. The draft is saved; nothing has been created.",
        adapter=None,
    )
