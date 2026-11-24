"""JSON cards for the same leaves the markdown tree renders."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from temporal_memory.api.vault import AuthContext, get_store, require_owner_access
from temporal_memory.core.persona import cards_for, person_card, projection, projection_from_store
from temporal_memory.models import CLUSTERS, GraphStore

router = APIRouter(prefix="/v1/owners/{owner}", tags=["cards"])


def _projection(owner: str, store: GraphStore):
    database = getattr(store, "db", None)
    if database is not None:
        return projection(database, owner)
    return projection_from_store(store, owner)


@router.get("/cards")
def list_cards(
    owner: str,
    cluster: str | None = Query(default=None),
    person: str | None = Query(default=None),
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict:
    if cluster is not None and cluster not in CLUSTERS:
        raise HTTPException(status_code=400, detail="unknown cluster")
    built = _projection(owner, store)
    cards = cards_for(built, cluster=cluster, person=person)
    if person and not cards:
        raise HTTPException(status_code=404, detail="person card not found")
    return {"owner": owner, "cards": cards}


@router.get("/people/{entity_id}/card")
def get_person_card(
    owner: str,
    entity_id: str,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict:
    database = getattr(store, "db", None)
    if database is not None:
        card = person_card(database, owner, entity_id)
    else:
        matches = cards_for(_projection(owner, store), person=entity_id)
        card = matches[0] if matches else None
    if card is None:
        raise HTTPException(status_code=404, detail="person card not found")
    return card
