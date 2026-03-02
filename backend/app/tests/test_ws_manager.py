"""Unit tests for the WebSocket connection manager."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch

from starlette.websockets import WebSocketState

from app.services.ws_manager import ConnectionManager


@pytest.fixture
def manager():
    """Create a fresh ConnectionManager for each test."""
    return ConnectionManager()


def make_mock_ws(client_state=WebSocketState.CONNECTED):
    """Create a mock WebSocket with the required interface."""
    ws = AsyncMock()
    ws.client_state = client_state
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    # Make it hashable for use in sets
    ws.__hash__ = Mock(return_value=id(ws))
    ws.__eq__ = lambda self, other: self is other
    return ws


class TestConnectionLifecycle:
    """Test connection connect and disconnect operations."""

    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self, manager):
        """connect() should call accept() on the WebSocket."""
        ws = make_mock_ws()
        await manager.connect(ws)

        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_registers_connection(self, manager):
        """connect() should register the WebSocket in connection_rooms."""
        ws = make_mock_ws()
        await manager.connect(ws)

        assert ws in manager.connection_rooms
        assert manager.connection_rooms[ws] == set()

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager):
        """disconnect() should remove the WebSocket from tracking."""
        ws = make_mock_ws()
        await manager.connect(ws)
        await manager.disconnect(ws)

        assert ws not in manager.connection_rooms

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_all_rooms(self, manager):
        """disconnect() should remove the WebSocket from all rooms."""
        ws = make_mock_ws()
        await manager.connect(ws)
        manager.join_room(ws, "room1")
        manager.join_room(ws, "room2")

        await manager.disconnect(ws)

        assert "room1" not in manager.rooms or ws not in manager.rooms.get("room1", set())
        assert "room2" not in manager.rooms or ws not in manager.rooms.get("room2", set())

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_empty_rooms(self, manager):
        """disconnect() should remove rooms that become empty."""
        ws = make_mock_ws()
        await manager.connect(ws)
        manager.join_room(ws, "room1")

        await manager.disconnect(ws)

        assert "room1" not in manager.rooms

    @pytest.mark.asyncio
    async def test_disconnect_unregistered_is_noop(self, manager):
        """disconnect() on an unregistered WebSocket should not raise."""
        ws = make_mock_ws()
        await manager.disconnect(ws)  # Should not raise

    @pytest.mark.asyncio
    async def test_multiple_connects(self, manager):
        """Multiple WebSocket connections should be tracked independently."""
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()

        await manager.connect(ws1)
        await manager.connect(ws2)

        assert ws1 in manager.connection_rooms
        assert ws2 in manager.connection_rooms


class TestRoomManagement:
    """Test room join and leave operations."""

    @pytest.mark.asyncio
    async def test_join_room(self, manager):
        """join_room() should add the WebSocket to the specified room."""
        ws = make_mock_ws()
        await manager.connect(ws)
        manager.join_room(ws, "game_42")

        assert ws in manager.rooms["game_42"]
        assert "game_42" in manager.connection_rooms[ws]

    @pytest.mark.asyncio
    async def test_join_room_creates_room(self, manager):
        """join_room() should create the room if it doesn't exist."""
        ws = make_mock_ws()
        await manager.connect(ws)

        assert "new_room" not in manager.rooms
        manager.join_room(ws, "new_room")
        assert "new_room" in manager.rooms

    @pytest.mark.asyncio
    async def test_join_room_without_connect_raises(self, manager):
        """join_room() should raise ValueError if WebSocket is not connected."""
        ws = make_mock_ws()

        with pytest.raises(ValueError, match="must be connected"):
            manager.join_room(ws, "room1")

    @pytest.mark.asyncio
    async def test_join_multiple_rooms(self, manager):
        """A WebSocket can join multiple rooms."""
        ws = make_mock_ws()
        await manager.connect(ws)
        manager.join_room(ws, "room1")
        manager.join_room(ws, "room2")

        assert "room1" in manager.connection_rooms[ws]
        assert "room2" in manager.connection_rooms[ws]

    @pytest.mark.asyncio
    async def test_multiple_connections_same_room(self, manager):
        """Multiple WebSockets can join the same room."""
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()
        await manager.connect(ws1)
        await manager.connect(ws2)
        manager.join_room(ws1, "room1")
        manager.join_room(ws2, "room1")

        assert ws1 in manager.rooms["room1"]
        assert ws2 in manager.rooms["room1"]
        assert manager.get_connection_count("room1") == 2

    @pytest.mark.asyncio
    async def test_leave_room(self, manager):
        """leave_room() should remove the WebSocket from the room."""
        ws = make_mock_ws()
        await manager.connect(ws)
        manager.join_room(ws, "room1")
        manager.leave_room(ws, "room1")

        assert ws not in manager.rooms.get("room1", set())
        assert "room1" not in manager.connection_rooms[ws]

    @pytest.mark.asyncio
    async def test_leave_room_cleans_up_empty(self, manager):
        """leave_room() should remove the room if it becomes empty."""
        ws = make_mock_ws()
        await manager.connect(ws)
        manager.join_room(ws, "room1")
        manager.leave_room(ws, "room1")

        assert "room1" not in manager.rooms

    @pytest.mark.asyncio
    async def test_leave_room_keeps_other_connections(self, manager):
        """leave_room() should not affect other connections in the room."""
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()
        await manager.connect(ws1)
        await manager.connect(ws2)
        manager.join_room(ws1, "room1")
        manager.join_room(ws2, "room1")

        manager.leave_room(ws1, "room1")

        assert ws2 in manager.rooms["room1"]
        assert manager.get_connection_count("room1") == 1

    @pytest.mark.asyncio
    async def test_leave_nonexistent_room_is_noop(self, manager):
        """leave_room() for a room the WebSocket isn't in should not raise."""
        ws = make_mock_ws()
        await manager.connect(ws)
        manager.leave_room(ws, "nonexistent")  # Should not raise


class TestBroadcast:
    """Test room-based message broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_in_room(self, manager):
        """broadcast_to_room() should send the message to every connection in the room."""
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()
        await manager.connect(ws1)
        await manager.connect(ws2)
        manager.join_room(ws1, "room1")
        manager.join_room(ws2, "room1")

        msg = {"type": "game_update", "data": {"gold": 10}}
        await manager.broadcast_to_room("room1", msg)

        ws1.send_json.assert_awaited_once_with(msg)
        ws2.send_json.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_broadcast_only_targets_correct_room(self, manager):
        """broadcast_to_room() should not send to connections in other rooms."""
        ws_room1 = make_mock_ws()
        ws_room2 = make_mock_ws()
        await manager.connect(ws_room1)
        await manager.connect(ws_room2)
        manager.join_room(ws_room1, "room1")
        manager.join_room(ws_room2, "room2")

        msg = {"type": "event"}
        await manager.broadcast_to_room("room1", msg)

        ws_room1.send_json.assert_awaited_once_with(msg)
        ws_room2.send_json.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_room(self, manager):
        """broadcast_to_room() to a room with no connections should not raise."""
        await manager.broadcast_to_room("empty_room", {"type": "test"})
        # Should not raise

    @pytest.mark.asyncio
    async def test_broadcast_cleans_up_stale_connections(self, manager):
        """broadcast_to_room() should remove connections that fail to receive."""
        ws_ok = make_mock_ws()
        ws_stale = make_mock_ws()
        ws_stale.send_json = AsyncMock(side_effect=RuntimeError("connection closed"))

        await manager.connect(ws_ok)
        await manager.connect(ws_stale)
        manager.join_room(ws_ok, "room1")
        manager.join_room(ws_stale, "room1")

        await manager.broadcast_to_room("room1", {"type": "test"})

        # Stale connection should be removed
        assert ws_stale not in manager.connection_rooms
        # Good connection should remain
        assert ws_ok in manager.rooms.get("room1", set())

    @pytest.mark.asyncio
    async def test_broadcast_skips_disconnected_state(self, manager):
        """broadcast_to_room() should skip WebSockets not in CONNECTED state."""
        ws_connected = make_mock_ws(client_state=WebSocketState.CONNECTED)
        ws_disconnected = make_mock_ws(client_state=WebSocketState.DISCONNECTED)

        await manager.connect(ws_connected)
        await manager.connect(ws_disconnected)
        manager.join_room(ws_connected, "room1")
        manager.join_room(ws_disconnected, "room1")

        await manager.broadcast_to_room("room1", {"type": "test"})

        ws_connected.send_json.assert_awaited_once()
        ws_disconnected.send_json.assert_not_awaited()


class TestRoomQueries:
    """Test room query/utility methods."""

    @pytest.mark.asyncio
    async def test_get_room_connections(self, manager):
        """get_room_connections() should return connections in the room."""
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()
        await manager.connect(ws1)
        await manager.connect(ws2)
        manager.join_room(ws1, "room1")
        manager.join_room(ws2, "room1")

        conns = manager.get_room_connections("room1")
        assert ws1 in conns
        assert ws2 in conns

    @pytest.mark.asyncio
    async def test_get_room_connections_returns_copy(self, manager):
        """get_room_connections() should return a copy, not the internal set."""
        ws = make_mock_ws()
        await manager.connect(ws)
        manager.join_room(ws, "room1")

        conns = manager.get_room_connections("room1")
        conns.clear()  # Modifying the copy

        # Internal set should be unaffected
        assert manager.get_connection_count("room1") == 1

    @pytest.mark.asyncio
    async def test_get_room_connections_empty_room(self, manager):
        """get_room_connections() for nonexistent room returns empty set."""
        conns = manager.get_room_connections("nonexistent")
        assert conns == set()

    @pytest.mark.asyncio
    async def test_get_connection_count(self, manager):
        """get_connection_count() returns correct count."""
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()
        await manager.connect(ws1)
        await manager.connect(ws2)
        manager.join_room(ws1, "room1")
        manager.join_room(ws2, "room1")

        assert manager.get_connection_count("room1") == 2
        assert manager.get_connection_count("nonexistent") == 0


class TestPgNotifyListener:
    """Test PostgreSQL NOTIFY/LISTEN integration."""

    @pytest.mark.asyncio
    async def test_handle_pg_notification_broadcasts_to_room(self, manager):
        """_handle_pg_notification() should broadcast to the specified room."""
        ws = make_mock_ws()
        await manager.connect(ws)
        manager.join_room(ws, "game_42")

        payload = json.dumps({
            "room": "game_42",
            "type": "game_update",
            "data": {"phase": "development"},
        })

        await manager._handle_pg_notification(payload)

        ws.send_json.assert_awaited_once()
        sent_msg = ws.send_json.call_args[0][0]
        assert sent_msg["room"] == "game_42"
        assert sent_msg["type"] == "game_update"

    @pytest.mark.asyncio
    async def test_handle_pg_notification_invalid_json(self, manager):
        """_handle_pg_notification() should handle invalid JSON gracefully."""
        await manager._handle_pg_notification("not valid json")
        # Should not raise

    @pytest.mark.asyncio
    async def test_handle_pg_notification_missing_room(self, manager):
        """_handle_pg_notification() should skip notifications without a room key."""
        payload = json.dumps({"type": "event", "data": {}})
        await manager._handle_pg_notification(payload)
        # Should not raise

    @pytest.mark.asyncio
    async def test_start_stop_pg_listener(self, manager):
        """start/stop_pg_listener should manage the listener state."""
        with patch.object(manager, '_pg_listen_loop', new_callable=AsyncMock) as mock_loop:
            mock_loop.return_value = None

            await manager.start_pg_listener()
            assert manager._listening is True
            assert manager._listener_task is not None

            await manager.stop_pg_listener()
            assert manager._listening is False
            assert manager._listener_task is None

    @pytest.mark.asyncio
    async def test_start_pg_listener_idempotent(self, manager):
        """Starting the listener twice should not create duplicate tasks."""
        with patch.object(manager, '_pg_listen_loop', new_callable=AsyncMock) as mock_loop:
            mock_loop.return_value = None

            await manager.start_pg_listener()
            task1 = manager._listener_task

            await manager.start_pg_listener()
            task2 = manager._listener_task

            # Should be the same task (second call is a no-op)
            assert task1 is task2

            await manager.stop_pg_listener()

    @pytest.mark.asyncio
    async def test_pg_notify_static_method(self):
        """pg_notify() should execute NOTIFY via psycopg2."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        with patch("app.services.ws_manager.psycopg2") as mock_psycopg2:
            mock_psycopg2.connect.return_value = mock_conn
            mock_psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT = 0

            await ConnectionManager.pg_notify(
                "game_42", "game_update", {"phase": "development"}
            )

            mock_psycopg2.connect.assert_called_once()
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "NOTIFY game_events" in call_args[0][0]
            payload = json.loads(call_args[0][1][0])
            assert payload["room"] == "game_42"
            assert payload["type"] == "game_update"
            mock_conn.close.assert_called_once()
