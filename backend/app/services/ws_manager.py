"""WebSocket connection manager with room-based broadcasting.

Provides the ConnectionManager class that tracks active WebSocket connections
per game room and supports PostgreSQL NOTIFY/LISTEN for cross-process fanout.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections organized into game rooms.

    Tracks active connections per room and provides broadcast capabilities.
    Integrates with PostgreSQL NOTIFY/LISTEN for cross-process event fanout
    so multiple worker processes can relay messages to their local connections.
    """

    def __init__(self) -> None:
        # Map of room_id -> set of WebSocket connections
        self._rooms: Dict[str, Set[WebSocket]] = {}
        # Map of WebSocket -> set of room_ids (for cleanup on disconnect)
        self._connection_rooms: Dict[WebSocket, Set[str]] = {}
        # Background task for the PG listener
        self._listener_task: Optional[asyncio.Task] = None
        self._listening: bool = False

    @property
    def rooms(self) -> Dict[str, Set[WebSocket]]:
        """Read-only access to rooms for testing/inspection."""
        return self._rooms

    @property
    def connection_rooms(self) -> Dict[WebSocket, Set[str]]:
        """Read-only access to connection-room mapping."""
        return self._connection_rooms

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to accept.
        """
        await websocket.accept()
        self._connection_rooms[websocket] = set()
        logger.info("WebSocket connection accepted")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from all rooms and clean up.

        Args:
            websocket: The WebSocket connection to remove.
        """
        rooms = self._connection_rooms.pop(websocket, set())
        for room_id in rooms:
            self._rooms.get(room_id, set()).discard(websocket)
            # Remove empty rooms
            if room_id in self._rooms and not self._rooms[room_id]:
                del self._rooms[room_id]
        logger.info("WebSocket connection removed from %d rooms", len(rooms))

    def join_room(self, websocket: WebSocket, room_id: str) -> None:
        """Add a WebSocket connection to a room.

        Args:
            websocket: The WebSocket connection.
            room_id: The room identifier (typically a game_id).
        """
        if websocket not in self._connection_rooms:
            raise ValueError("WebSocket must be connected before joining a room")

        if room_id not in self._rooms:
            self._rooms[room_id] = set()
        self._rooms[room_id].add(websocket)
        self._connection_rooms[websocket].add(room_id)
        logger.info("WebSocket joined room %s", room_id)

    def leave_room(self, websocket: WebSocket, room_id: str) -> None:
        """Remove a WebSocket connection from a room.

        Args:
            websocket: The WebSocket connection.
            room_id: The room identifier.
        """
        if room_id in self._rooms:
            self._rooms[room_id].discard(websocket)
            if not self._rooms[room_id]:
                del self._rooms[room_id]

        if websocket in self._connection_rooms:
            self._connection_rooms[websocket].discard(room_id)
        logger.info("WebSocket left room %s", room_id)

    async def broadcast_to_room(self, room_id: str, message: dict) -> None:
        """Send a JSON message to all connections in a room.

        Disconnected or errored connections are automatically cleaned up.

        Args:
            room_id: The room identifier.
            message: The message dict to send as JSON.
        """
        connections = self._rooms.get(room_id, set()).copy()
        if not connections:
            return

        stale: list[WebSocket] = []
        for ws in connections:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(message)
                else:
                    stale.append(ws)
            except Exception:
                logger.warning("Failed to send message to WebSocket in room %s", room_id)
                stale.append(ws)

        # Clean up stale connections
        for ws in stale:
            await self.disconnect(ws)

    def get_room_connections(self, room_id: str) -> Set[WebSocket]:
        """Get the set of connections in a room.

        Args:
            room_id: The room identifier.

        Returns:
            Set of WebSocket connections in the room (empty set if room doesn't exist).
        """
        return self._rooms.get(room_id, set()).copy()

    def get_connection_count(self, room_id: str) -> int:
        """Get the number of connections in a room.

        Args:
            room_id: The room identifier.

        Returns:
            Number of active connections in the room.
        """
        return len(self._rooms.get(room_id, set()))

    # ── PostgreSQL NOTIFY/LISTEN ──────────────────────────────────────

    async def start_pg_listener(self) -> None:
        """Start the PostgreSQL NOTIFY/LISTEN background listener.

        Listens on the 'game_events' channel and fans out received
        notifications to the appropriate local WebSocket room.

        The notification payload is expected to be a JSON string with
        at minimum a "room" key indicating which room to broadcast to.
        """
        if self._listening:
            return

        self._listening = True
        self._listener_task = asyncio.create_task(self._pg_listen_loop())
        logger.info("PostgreSQL NOTIFY/LISTEN listener started")

    async def stop_pg_listener(self) -> None:
        """Stop the PostgreSQL NOTIFY/LISTEN background listener."""
        self._listening = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        self._listener_task = None
        logger.info("PostgreSQL NOTIFY/LISTEN listener stopped")

    async def _pg_listen_loop(self) -> None:
        """Internal loop that listens for PostgreSQL notifications.

        Uses psycopg2 in a thread executor since it is a synchronous driver.
        Reconnects automatically on connection failure.
        """
        while self._listening:
            conn = None
            try:
                conn = await self._create_pg_connection()
                if conn is None:
                    await asyncio.sleep(5)
                    continue

                # Use a thread to run the blocking select/poll on the connection
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._pg_execute_listen, conn)

                while self._listening:
                    # Poll for notifications in a thread (blocking with timeout)
                    notifications = await loop.run_in_executor(
                        None, self._pg_poll_notifications, conn
                    )
                    for payload in notifications:
                        await self._handle_pg_notification(payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("PG listener error, reconnecting in 5s")
                await asyncio.sleep(5)
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass

    async def _create_pg_connection(self):
        """Create a raw psycopg2 connection for LISTEN.

        Returns None if psycopg2 is not available or connection fails.
        """
        try:
            import psycopg2
        except ImportError:
            logger.warning("psycopg2 not available, PG listener disabled")
            self._listening = False
            return None

        loop = asyncio.get_event_loop()
        try:
            conn = await loop.run_in_executor(
                None,
                lambda: psycopg2.connect(settings.DATABASE_URL),
            )
            conn.set_isolation_level(
                psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
            )
            return conn
        except Exception:
            logger.exception("Failed to connect to PostgreSQL for LISTEN")
            return None

    @staticmethod
    def _pg_execute_listen(conn) -> None:
        """Execute the LISTEN command on a psycopg2 connection."""
        with conn.cursor() as cur:
            cur.execute("LISTEN game_events;")

    @staticmethod
    def _pg_poll_notifications(conn, timeout: float = 1.0) -> list:
        """Poll for pending notifications with a timeout.

        Returns a list of notification payloads (strings).
        """
        import select

        payloads: list[str] = []
        if select.select([conn], [], [], timeout) != ([], [], []):
            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop(0)
                payloads.append(notify.payload)
        return payloads

    async def _handle_pg_notification(self, payload: str) -> None:
        """Handle a single PostgreSQL notification payload.

        Expected payload format (JSON):
            {"room": "<room_id>", "type": "<event_type>", ...data}
        """
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Invalid JSON in PG notification: %s", payload)
            return

        room_id = data.get("room")
        if not room_id:
            logger.warning("PG notification missing 'room' key: %s", payload)
            return

        await self.broadcast_to_room(str(room_id), data)

    # ── Utility for publishing (used by other services) ───────────────

    @staticmethod
    async def pg_notify(room_id: str, event_type: str, data: dict) -> None:
        """Publish a notification via PostgreSQL NOTIFY.

        This is a convenience method for other services to publish events
        that will be picked up by all worker processes' listeners.

        Args:
            room_id: The game room to target.
            event_type: The event type string.
            data: Additional event data.
        """
        try:
            import psycopg2
        except ImportError:
            logger.warning("psycopg2 not available, cannot NOTIFY")
            return

        payload = json.dumps({"room": room_id, "type": event_type, **data})

        loop = asyncio.get_event_loop()
        try:
            def _do_notify():
                conn = psycopg2.connect(settings.DATABASE_URL)
                conn.set_isolation_level(
                    psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
                )
                try:
                    with conn.cursor() as cur:
                        cur.execute("NOTIFY game_events, %s;", (payload,))
                finally:
                    conn.close()

            await loop.run_in_executor(None, _do_notify)
        except Exception:
            logger.exception("Failed to send PG NOTIFY")


# Singleton instance used across the application
manager = ConnectionManager()
