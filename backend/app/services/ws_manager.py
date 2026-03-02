"""WebSocket connection manager with room-based broadcasting."""

import json
import logging
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections organized by game rooms.

    Each game_id maps to a set of active WebSocket connections.
    Supports connect, disconnect, join_room, leave_room, and broadcast_to_room.
    """

    def __init__(self) -> None:
        # game_id -> set of WebSocket connections
        self._rooms: Dict[int, Set[WebSocket]] = {}
        # websocket -> game_id (reverse lookup for cleanup)
        self._connection_rooms: Dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, game_id: int) -> None:
        """Accept a WebSocket connection and add it to the specified game room."""
        await websocket.accept()
        self.join_room(websocket, game_id)
        logger.info("WebSocket connected to game room %d", game_id)

    def join_room(self, websocket: WebSocket, game_id: int) -> None:
        """Add a connection to a game room."""
        if game_id not in self._rooms:
            self._rooms[game_id] = set()
        self._rooms[game_id].add(websocket)
        self._connection_rooms[websocket] = game_id

    def leave_room(self, websocket: WebSocket) -> None:
        """Remove a connection from its current room."""
        game_id = self._connection_rooms.pop(websocket, None)
        if game_id is not None and game_id in self._rooms:
            self._rooms[game_id].discard(websocket)
            if not self._rooms[game_id]:
                del self._rooms[game_id]

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection from all tracking structures."""
        self.leave_room(websocket)
        logger.info("WebSocket disconnected")

    async def broadcast_to_room(self, game_id: int, message: Dict[str, Any]) -> None:
        """Send a JSON message to all connections in a game room."""
        connections = self._rooms.get(game_id, set()).copy()
        payload = json.dumps(message)
        for websocket in connections:
            try:
                await websocket.send_text(payload)
            except Exception:
                logger.warning("Failed to send to a WebSocket in room %d", game_id)
                self.disconnect(websocket)

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Send a JSON message to a single connection."""
        await websocket.send_text(json.dumps(message))

    def get_room_count(self, game_id: int) -> int:
        """Return the number of connections in a game room."""
        return len(self._rooms.get(game_id, set()))

    def get_rooms(self) -> Dict[int, int]:
        """Return a dict of game_id -> connection count."""
        return {gid: len(conns) for gid, conns in self._rooms.items()}


# Singleton instance shared across the application
manager = ConnectionManager()
