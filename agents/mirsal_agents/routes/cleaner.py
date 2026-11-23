"""Routes: AI Image Cleaner jobs (wraps ai_cleaner_engine)."""
from __future__ import annotations

from fastapi import FastAPI

from fastapi import File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from ..ai_cleaner import MODES
def register(app: FastAPI, S, user, verify_key) -> None:
    @app.post("/agents/ai-cleaner/jobs")
    async def cleaner_submit(req: Request, image: UploadFile = File(...), mode: str = Form("resize_then_sdxl")):
        try:
            data = await image.read()
            job = S(req).cleaner.submit(user(req), image.filename or "upload.jpg", data, (mode or "").strip())
        except ValueError as err:
            raise HTTPException(400, str(err)) from err
        return {"job_id": job.id}

    @app.get("/agents/ai-cleaner/jobs/{job_id}")
    async def cleaner_status(req: Request, job_id: str):
        job = S(req).cleaner.get_for(user(req), job_id)
        if job is None:
            raise HTTPException(404, "job not found")
        return S(req).cleaner.wire(job)

    @app.get("/agents/ai-cleaner/jobs/{job_id}/file")
    async def cleaner_file(req: Request, job_id: str):
        job = S(req).cleaner.get_for(user(req), job_id)
        if job is None:
            raise HTTPException(404, "job not found")
        if not job.done or job.error or job.cleaned is None:
            raise HTTPException(409, "result not ready")
        return FileResponse(str(job.cleaned), media_type="image/jpeg", filename=f"{job.id}_cleaned.jpg")

    @app.get("/agents/ai-cleaner/capabilities")
    async def cleaner_capabilities(req: Request):
        s = S(req)
        return {"modes": list(MODES), "engine": "ai_cleaner_engine",
                "verify_openai": bool(s.cfg.openai_key)}

    # The verify endpoint exists only when a key is configured: no key, no
    # endpoint, no button. Each call needs explicit user consent (private images
    # leave the device only on tap) and counts against the spend budget.
    _verify_key = verify_key
    if _verify_key:
        @app.post("/agents/ai-cleaner/verify")
        async def cleaner_verify(req: Request, image: UploadFile = File(...)):
            from .ai_cleaner import verify_with_openai
            data = await image.read()
            if len(data) > 50 * 1024 * 1024:
                raise HTTPException(400, "Image is over the 50 MB limit.")
            try:
                return await verify_with_openai(_verify_key, data, image.filename or "image.jpg")
            except PermissionError as err:
                raise HTTPException(401, str(err)) from err
            except RuntimeError as err:
                raise HTTPException(502, str(err)) from err
