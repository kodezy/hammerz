import asyncio
from collections import defaultdict
from typing import Any
from uuid import uuid4

from fastapi import WebSocket


class Hub:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def join(self, auction_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms[auction_id].add(ws)

    async def leave(self, auction_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[auction_id].discard(ws)

    async def publish(self, auction_id: str, message: dict[str, Any]) -> None:
        payload = {**message, "id": str(uuid4())}
        async with self._lock:
            sockets = list(self._rooms.get(auction_id, set()))
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._rooms[auction_id].discard(ws)
