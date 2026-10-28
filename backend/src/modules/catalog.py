import asyncio
import re
import time
from html import unescape
from typing import Any

import httpx

from src.core.errors import AppError, ErrorCode

MET_SEARCH = "https://collectionapi.metmuseum.org/public/collection/v1.1/search"
MET_OBJECT = "https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}"
# Met returns 403 for httpx's default python-httpx User-Agent.
MET_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Hammerz/1.0)"}
SEARCH_TIMEOUT = 5.0
DETAIL_CONCURRENCY = 4
CACHE_TTL = 60.0

_TAG_RE = re.compile(r"<[^>]*>")


def _plain_met_text(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = unescape(_TAG_RE.sub("", raw))
    text = " ".join(text.split())
    return text or None


_cache: dict[tuple[str, int, int], tuple[float, dict[str, Any]]] = {}


def _cache_get(key: tuple[str, int, int]) -> dict[str, Any] | None:
    entry = _cache.get(key)
    if not entry:
        return None
    expires, value = entry
    if time.monotonic() > expires:
        del _cache[key]
        return None
    return value


def _cache_set(key: tuple[str, int, int], value: dict[str, Any]) -> None:
    _cache[key] = (time.monotonic() + CACHE_TTL, value)


async def _get_json(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = await client.get(url, timeout=SEARCH_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < 2:
                await asyncio.sleep(0.2 * (attempt + 1))
    raise AppError(503, ErrorCode.CATALOG_UNAVAILABLE, "Catalog service unavailable") from last_exc


async def search_catalog(q: str, offset: int, limit: int) -> dict[str, Any]:
    if limit < 1 or limit > 20:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "limit must be 1–20")
    if offset < 0:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "offset must be >= 0")
    cache_key = (q, offset, limit)
    cached = _cache_get(cache_key)
    if cached:
        return cached

    async with httpx.AsyncClient(headers=MET_HTTP_HEADERS) as client:
        search_url = MET_SEARCH + "?" + str(httpx.QueryParams({"hasImages": "true", "q": q}))
        try:
            search_data = await _get_json(client, search_url)
        except AppError:
            raise
        object_ids = search_data.get("objectIDs") or []
        total = int(search_data.get("total") or 0)
        slice_ids = object_ids[offset : offset + limit]

        sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

        async def fetch_one(oid: int) -> dict[str, Any] | None:
            if oid <= 0:
                return None
            async with sem:
                try:
                    data = await _get_json(client, MET_OBJECT.format(object_id=oid))
                except AppError:
                    return None
                if not data.get("title") or not data.get("primaryImage"):
                    return None
                return _map_object(data)

        details = await asyncio.gather(*(fetch_one(int(i)) for i in slice_ids))
        items = [d for d in details if d is not None]
        items.sort(key=lambda x: (not x.get("is_public_domain", False), x.get("external_id", "")))

    result = {"has_more": offset + limit < total, "items": items, "limit": limit, "offset": offset, "total": total}
    _cache_set(cache_key, result)
    return result


# Used when the live Met API is unreachable (e.g. demo seed in Docker).
_DEMO_OBJECT_SNAPSHOTS: dict[int, dict[str, Any]] = {
    436535: {
        "artist": "Vincent van Gogh",
        "attribution": "Vincent van Gogh (1853–1890)",
        "description": "https://www.metmuseum.org/art/collection/search/436535",
        "external_id": "436535",
        "object_begin_date": 1889,
        "image_url": "https://images.metmuseum.org/CRDImages/ep/original/DT1567.jpg",
        "is_public_domain": True,
        "object_url": "https://www.metmuseum.org/art/collection/search/436535",
        "provider": "met",
        "title": "Self-Portrait with a Straw Hat (obverse: The Potato Peeler)",
    },
    436532: {
        "artist": "Vincent van Gogh",
        "attribution": "Vincent van Gogh (1853–1890)",
        "description": "https://www.metmuseum.org/art/collection/search/436532",
        "external_id": "436532",
        "object_begin_date": 1887,
        "image_url": "https://images.metmuseum.org/CRDImages/ep/original/DT1502_cropped2.jpg",
        "is_public_domain": True,
        "object_url": "https://www.metmuseum.org/art/collection/search/436532",
        "provider": "met",
        "title": "Wheat Field with Cypresses",
    },
}


def _map_object(data: dict[str, Any]) -> dict[str, Any]:
    artist = _plain_met_text(data.get("artistDisplayName"))
    begin = data.get("objectBeginDate")
    title = _plain_met_text(data.get("title"))
    return {
        "artist": artist,
        "attribution": data.get("creditLine"),
        "description": data.get("objectURL"),
        "external_id": str(data.get("objectID")),
        "object_begin_date": begin,
        "image_url": data.get("primaryImage"),
        "is_public_domain": bool(data.get("isPublicDomain")),
        "object_url": data.get("objectURL"),
        "provider": "met",
        "title": title,
    }


async def fetch_object(object_id: int, *, allow_demo_snapshot: bool = False) -> dict[str, Any]:
    if object_id <= 0:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "Invalid object id")
    async with httpx.AsyncClient(headers=MET_HTTP_HEADERS) as client:
        try:
            data = await _get_json(client, MET_OBJECT.format(object_id=object_id))
        except AppError:
            fallback = _DEMO_OBJECT_SNAPSHOTS.get(object_id) if allow_demo_snapshot else None
            if fallback is not None:
                return fallback
            raise
    if not data.get("title") or not data.get("primaryImage"):
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "Catalog object missing title or image")
    return _map_object(data)
