"""WebSocket connection manager with room-based broadcasting and PostgreSQL NOTIFY/LISTEN."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Set
from urllib.parse import urlparse

import asyncpg
from fastapi import WebSocket

from app.core.config import settings

logger = logging.getLogger(__name__)

# PostgreSQL NOTIFY channel name for game events
PG_CHANNEL = "game_events"


def _parse_dsn(database_url: str) -> str:
    """Convert SQLAlchemy-style DATABASE_URL to asyncpg DSN.

    Replaces 'postgresql://' with 'postgresql://' (no-op) and strips
    query parameters that asyncpg doesn't understand.
    """
    # asyncpg accepts standard postgresql:// URIs
    url = database_url.replace("postgresql+psycopg2://", "postgresql://")
    return url


class ConnectionManager:
    """Manages WebSocket connections organized by game rooms.

    Each game_id maps to a set of active player WebSocket connections and
    a separate set of spectator connections.  Spectators receive all
    broadcasts but cannot send action messages.

    Optionally subscribes to a PostgreSQL NOTIFY channel so that events
    published from any backend process are fanned out to local WebSocket
    connections in the relevant game room.
    """

    def __init__(self) -> None:
        # game_id -> set of player WebSocket connections
        self._rooms: Dict[int, Set[WebSocket]] = {}
        # game_id -> set of spectator WebSocket connections
        self._spectators: Dict[int, Set[WebSocket]] = {}
        # websocket -> game_id (reverse lookup for cleanup)
        self._connection_rooms: Dict[WebSocket, int] = {}
        # websocket -> True if this connection is a spectator
        self._is_spectator: Dict[WebSocket, bool] = {}
        # asyncpg connection used for LISTEN
        self._listen_conn: Optional[asyncpg.Connection] = None
        # asyncpg pool used for NOTIFY
        self._notify_pool: Optional[asyncpg.Pool] = None
        # background task for the listener
        self._listener_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------ #
    #  Connection lifecycle                                                #
    # ------------------------------------------------------------------ #

    async def connect(self, websocket: WebSocket, game_id: int) -> None:
        """Accept a WebSocket connection and add it to the specified game room."""
        await websocket.accept()
        self.join_room(websocket, game_id)
        logger.info("WebSocket connected to game room %d", game_id)

    async def connect_spectator(self, websocket: WebSocket, game_id: int) -> None:
        """Accept a spectator WebSocket connection and add it to the game room."""
        await websocket.accept()
        self.join_room_as_spectator(websocket, game_id)
        logger.info("Spectator WebSocket connected to game room %d", game_id)

    def join_room(self, websocket: WebSocket, game_id: int) -> None:
        """Add a connection to a game room as a player."""
        if game_id not in self._rooms:
            self._rooms[game_id] = set()
        self._rooms[game_id].add(websocket)
        self._connection_rooms[websocket] = game_id
        self._is_spectator[websocket] = False

    def join_room_as_spectator(self, websocket: WebSocket, game_id: int) -> None:
        """Add a connection to a game room as a spectator."""
        if game_id not in self._spectators:
            self._spectators[game_id] = set()
        self._spectators[game_id].add(websocket)
        self._connection_rooms[websocket] = game_id
        self._is_spectator[websocket] = True

    def leave_room(self, websocket: WebSocket) -> None:
        """Remove a connection from its current room."""
        game_id = self._connection_rooms.pop(websocket, None)
        is_spectator = self._is_spectator.pop(websocket, False)
        if game_id is None:
            return
        if is_spectator:
            if game_id in self._spectators:
                self._spectators[game_id].discard(websocket)
                if not self._spectators[game_id]:
                    del self._spectators[game_id]
        else:
            if game_id in self._rooms:
                self._rooms[game_id].discard(websocket)
                if not self._rooms[game_id]:
                    del self._rooms[game_id]

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection from all tracking structures."""
        self.leave_room(websocket)
        logger.info("WebSocket disconnected")

    def disconnect_spectator(self, websocket: WebSocket) -> None:
        """Remove a spectator from all tracking structures."""
        self.leave_room(websocket)
        logger.info("Spectator disconnected")

    def is_spectator(self, websocket: WebSocket) -> bool:
        """Return True if the given connection is a spectator."""
        return self._is_spectator.get(websocket, False)

    def get_spectator_count(self, game_id: int) -> int:
        """Return the number of spectators in a game room."""
        return len(self._spectators.get(game_id, set()))

    # ------------------------------------------------------------------ #
    #  Messaging                                                           #
    # ------------------------------------------------------------------ #

    async def broadcast_to_room(self, game_id: int, message: Dict[str, Any]) -> None:
        """Send a JSON message to all connections (players and spectators) in a game room."""
        connections = self._rooms.get(game_id, set()).copy()
        spectators = self._spectators.get(game_id, set()).copy()
        all_connections = connections | spectators
        payload = json.dumps(message)
        for websocket in all_connections:
            try:
                await websocket.send_text(payload)
            except Exception:
                logger.warning("Failed to send to a WebSocket in room %d", game_id)
                self.disconnect(websocket)

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Send a JSON message to a single connection."""
        await websocket.send_text(json.dumps(message))

    def get_room_count(self, game_id: int) -> int:
        """Return the number of player connections in a game room."""
        return len(self._rooms.get(game_id, set()))

    def get_rooms(self) -> Dict[int, int]:
        """Return a dict of game_id -> player connection count."""
        return {gid: len(conns) for gid, conns in self._rooms.items()}

    def get_rooms_with_spectators(self) -> Dict[int, Dict[str, int]]:
        """Return a dict of game_id -> {players: count, spectators: count}."""
        all_ids = set(self._rooms.keys()) | set(self._spectators.keys())
        return {
            gid: {
                "players": len(self._rooms.get(gid, set())),
                "spectators": len(self._spectators.get(gid, set())),
            }
            for gid in all_ids
        }

    # ------------------------------------------------------------------ #
    #  PostgreSQL NOTIFY helper                                            #
    # ------------------------------------------------------------------ #

    async def notify(self, game_id: int, message: Dict[str, Any]) -> None:
        """Publish a game event via PostgreSQL NOTIFY.

        The payload is a JSON string containing ``game_id`` and the original
        ``message``.  All backend processes listening on the channel will
        receive the notification and broadcast it to their local WebSocket
        connections.

        If the NOTIFY pool is not available (e.g. in tests), falls back to
        a direct local broadcast.
        """
        payload = json.dumps({"game_id": game_id, "message": message})

        if self._notify_pool is not None:
            try:
                async with self._notify_pool.acquire() as conn:
                    await conn.execute(
                        f"SELECT pg_notify($1, $2)", PG_CHANNEL, payload
                    )
                return
            except Exception:
                logger.exception("Failed to send PG NOTIFY, falling back to local broadcast")

        # Fallback: broadcast locally when no PG connection is available
        await self.broadcast_to_room(game_id, message)

    # ------------------------------------------------------------------ #
    #  PostgreSQL LISTEN lifecycle                                         #
    # ------------------------------------------------------------------ #

    async def start_listening(self) -> None:
        """Connect to PostgreSQL and start listening for game events.

        Creates a dedicated connection for LISTEN (long-lived) and a
        connection pool for NOTIFY (short-lived queries).
        """
        dsn = _parse_dsn(settings.DATABASE_URL)

        try:
            self._notify_pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
            self._listen_conn = await asyncpg.connect(dsn)
            await self._listen_conn.add_listener(PG_CHANNEL, self._on_notification)
            logger.info("Listening on PostgreSQL channel '%s'", PG_CHANNEL)
        except Exception:
            logger.exception("Failed to start PostgreSQL listener")
            raise

    def _on_notification(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        """Handle a raw PostgreSQL notification.

        Parses the JSON payload and schedules a broadcast to the relevant
        game room on the running event loop.
        """
        try:
            data = json.loads(payload)
            game_id = data["game_id"]
            message = data["message"]
        except (json.JSONDecodeError, KeyError):
            logger.warning("Invalid NOTIFY payload: %s", payload)
            return

        loop = asyncio.get_event_loop()
        loop.create_task(self.broadcast_to_room(game_id, message))

    async def stop_listening(self) -> None:
        """Disconnect the LISTEN connection and close the NOTIFY pool."""
        if self._listen_conn is not None:
            try:
                await self._listen_conn.remove_listener(PG_CHANNEL, self._on_notification)
                await self._listen_conn.close()
            except Exception:
                logger.warning("Error closing LISTEN connection", exc_info=True)
            self._listen_conn = None

        if self._notify_pool is not None:
            try:
                await self._notify_pool.close()
            except Exception:
                logger.warning("Error closing NOTIFY pool", exc_info=True)
            self._notify_pool = None

        logger.info("Stopped PostgreSQL listener")


# Singleton instance shared across the application
manager = ConnectionManager()
