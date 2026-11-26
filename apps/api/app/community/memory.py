"""Community memory through the bridge. Consent stays off until the adult opts in."""

from fastapi import Request

from app.memory_bridge.models import ConsentDeniedError, MemoryRecordInput, MinorProtectionError


def bridge_of(request: Request):
    return getattr(request.app.state, "memory_bridge", None)


def remember(request: Request, *, record_id: str, source_id: str, text: str, author_id: str, subject_path: str | None = None):
    """Write one consented record. A missing bridge or a denied consent leaves the social row alone."""
    bridge = bridge_of(request)
    principal = getattr(request.state, "community_principal", None)
    if bridge is None or principal is None:
        return None
    if principal.is_minor_protected:
        return None
    # Demo cohort never becomes temporal_memory / verified facts about real users.
    try:
        from app.community.demo_10_users import is_demo_entity_id, is_demo_namespace_owner
        if (
            is_demo_namespace_owner(author_id)
            or is_demo_entity_id(source_id)
            or is_demo_entity_id(record_id)
            or is_demo_namespace_owner(getattr(principal, "user_id", None))
        ):
            return None
    except Exception:
        pass
    try:
        return bridge.write_consented(
            principal,
            MemoryRecordInput(
                record_id=record_id,
                source_kind="community",
                source_id=source_id,
                host_app="community",
                author_id=author_id,
                text=text,
                valid_time=_now_iso(),
                subject_path=subject_path,
                explicit_user_confirm=author_id == principal.user_id,
            ),
        )
    except (ConsentDeniedError, MinorProtectionError):
        return None


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
