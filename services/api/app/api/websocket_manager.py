from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, assessment_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[assessment_id].add(websocket)

    def disconnect(self, assessment_id: str, websocket: WebSocket) -> None:
        self._connections[assessment_id].discard(websocket)
        if not self._connections[assessment_id]:
            del self._connections[assessment_id]

    async def broadcast(self, assessment_id: str, payload: dict[str, Any]) -> None:
        disconnected: list[WebSocket] = []
        for websocket in list(self._connections.get(assessment_id, set())):
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(assessment_id, websocket)


websocket_manager = WebSocketManager()
