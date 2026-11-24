"""§9 Quest-like markdown tree. The leaves come from core.persona."""
from __future__ import annotations

from datetime import datetime, timezone
import io
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from temporal_memory.api.vault import AuthContext, get_store, require_owner_access
from temporal_memory.core.persona import projection, projection_from_store, slug, to_markdown
from temporal_memory.models import GraphStore

_DEFAULT_STORE: GraphStore | None = None


def set_default_store(store: GraphStore | None) -> None:
    global _DEFAULT_STORE
    _DEFAULT_STORE = store


def render(owner: str, *, store: GraphStore | None = None, db: object | None = None) -> dict[str, str]:
    """Render the §9 tree (`relative/path.md -> content`)."""
    st = store or _DEFAULT_STORE
    database = db if db is not None else getattr(st, "db", None)
    if database is not None:
        built = projection(database, owner)
    elif st is not None:
        built = projection_from_store(st, owner)
    else:
        raise RuntimeError("No GraphStore configured for api.export_md.render")
    return to_markdown(built)


router = APIRouter(prefix="/v1/owners/{owner}", tags=["export"])


@router.get("/export/md.zip")
def export_md_zip(
    owner: str,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> StreamingResponse:
    try:
        files = render(owner, store=store)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path, content in sorted(files.items()):
            zf.writestr(f"memory/{rel_path}", content.encode("utf-8"))
    buf.seek(0)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    headers = {"Content-Disposition": f'attachment; filename="{slug(owner)}-memory-{ts}.zip"'}
    return StreamingResponse(buf, media_type="application/zip", headers=headers)
