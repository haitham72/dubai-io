"""Routes: Diwan UAE events + picture versions."""
from __future__ import annotations

from fastapi import FastAPI

from fastapi import HTTPException, Request
def register(app: FastAPI, S, user) -> None:
    @app.get("/agents/diwan/events")
    async def diwan_events(req: Request):
        try:
            return await S(req).diwan.upcoming()
        except Exception as err:  # noqa: BLE001
            raise HTTPException(502, f"Diwan unavailable ({type(err).__name__})") from err

    @app.get("/agents/diwan/more")
    async def diwan_more(req: Request, event: str, image: str, count: int = 3):
        """"More from this picture": variations Diwan already holds (MCP tool more_from_image); Mirsal never makes them."""
        try:
            out = await S(req).diwan.more_from_image(event[:120], image[:300], count)
        except ValueError as err:
            raise HTTPException(400, str(err)) from err
        except LookupError as err:
            raise HTTPException(404, str(err)) from err
        except Exception as err:  # noqa: BLE001
            await S(req).tracer.record("diwan", tool="more_from_image", event=event[:120], error=type(err).__name__)
            raise HTTPException(502, f"Diwan unavailable ({type(err).__name__})") from err
        await S(req).tracer.record("diwan", tool="more_from_image", event=out["event"], image=out["image"],
                                   returned=len(out["images"]), mode=out["mode"])
        return out
