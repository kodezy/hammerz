from fastapi import APIRouter, Depends, Query

from app.api.deps import require_seller
from app.db.tables import User
from app.modules.catalog import search_catalog

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get("/search")
async def catalog_search(
    q: str = Query(min_length=1),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=20),
    _seller: User = Depends(require_seller),
) -> dict:
    return await search_catalog(q, offset, limit)
