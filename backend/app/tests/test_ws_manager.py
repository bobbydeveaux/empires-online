"""Unit tests for the WebSocket ConnectionManager."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ws_manager import ConnectionManager, PG_CHANNEL, _parse_dsn


@pytest.fixture
def manager():
    return ConnectionManager()


def _make_ws():
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


class TestConnectionManager:

    @pytest.mark.asyncio
    async def test_connect_adds_to_room(self, manager):
        ws = _make_ws()
        await manager.connect(ws, game_id=1)

        ws.accept.assert_awaited_once()
        assert manager.get_room_count(1) == 1

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_room(self, manager):
        ws = _make_ws()
        await manager.connect(ws, game_id=1)
        manager.disconnect(ws)

        assert manager.get_room_count(1) == 0

    @pytest.mark.asyncio
    async def test_multiple_connections_same_room(self, manager):
        ws1 = _make_ws()
        ws2 = _make_ws()

        await manager.connect(ws1, game_id=1)
        await manager.connect(ws2, game_id=1)

        assert manager.get_room_count(1) == 2

    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, manager):
        ws1 = _make_ws()
        ws2 = _make_ws()
        ws3 = _make_ws()

        await manager.connect(ws1, game_id=1)
        await manager.connect(ws2, game_id=1)
        await manager.connect(ws3, game_id=2)  # different room

        message = {"type": "test", "data": "hello"}
        await manager.broadcast_to_room(1, message)

        payload = json.dumps(message)
        ws1.send_text.assert_awaited_once_with(payload)
        ws2.send_text.assert_awaited_once_with(payload)
        ws3.send_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_personal(self, manager):
        ws = _make_ws()
        await manager.connect(ws, game_id=1)

        message = {"type": "pong"}
        await manager.send_personal(ws, message)

        ws.send_text.assert_awaited_with(json.dumps(message))

    @pytest.mark.asyncio
    async def test_leave_room(self, manager):
        ws = _make_ws()
        await manager.connect(ws, game_id=1)
        assert manager.get_room_count(1) == 1

        manager.leave_room(ws)
        assert manager.get_room_count(1) == 0

    @pytest.mark.asyncio
    async def test_get_rooms(self, manager):
        ws1 = _make_ws()
        ws2 = _make_ws()
        ws3 = _make_ws()

        await manager.connect(ws1, game_id=1)
        await manager.connect(ws2, game_id=1)
        await manager.connect(ws3, game_id=2)

        rooms = manager.get_rooms()
        assert rooms == {1: 2, 2: 1}

    @pytest.mark.asyncio
    async def test_broadcast_handles_failed_send(self, manager):
        """If one connection fails to send, it is disconnected but others still receive."""
        ws_good = _make_ws()
        ws_bad = _make_ws()
        ws_bad.send_text.side_effect = Exception("connection lost")

        await manager.connect(ws_good, game_id=1)
        await manager.connect(ws_bad, game_id=1)

        await manager.broadcast_to_room(1, {"type": "test"})

        # The good connection received the message
        ws_good.send_text.assert_awaited_once()
        # The bad connection was cleaned up
        assert manager.get_room_count(1) == 1

    @pytest.mark.asyncio
    async def test_disconnect_idempotent(self, manager):
        """Disconnecting an unknown WebSocket should not raise."""
        ws = _make_ws()
        manager.disconnect(ws)  # should not raise
        assert manager.get_rooms() == {}

    @pytest.mark.asyncio
    async def test_empty_room_removed(self, manager):
        ws = _make_ws()
        await manager.connect(ws, game_id=5)
        manager.disconnect(ws)

        # Room dict should not contain the empty room
        assert 5 not in manager._rooms


class TestNotifyFallback:
    """Tests for the notify() method when no PG pool is available."""

    @pytest.mark.asyncio
    async def test_notify_falls_back_to_local_broadcast(self, manager):
        """When _notify_pool is None, notify() broadcasts locally."""
        ws = _make_ws()
        await manager.connect(ws, game_id=42)

        message = {"type": "game_state_update", "data": {"phase": "development"}}
        await manager.notify(42, message)

        ws.send_text.assert_awaited_once_with(json.dumps(message))

    @pytest.mark.asyncio
    async def test_notify_with_pool_calls_pg_notify(self, manager):
        """When _notify_pool is set, notify() sends PG NOTIFY."""
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        manager._notify_pool = mock_pool

        message = {"type": "test", "data": "hello"}
        await manager.notify(7, message)

        expected_payload = json.dumps({"game_id": 7, "message": message})
        mock_conn.execute.assert_awaited_once_with(
            "SELECT pg_notify($1, $2)", PG_CHANNEL, expected_payload
        )

    @pytest.mark.asyncio
    async def test_notify_pg_error_falls_back_to_local(self, manager):
        """When PG NOTIFY fails, notify() falls back to local broadcast."""
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("connection lost")
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        manager._notify_pool = mock_pool

        ws = _make_ws()
        await manager.connect(ws, game_id=3)

        message = {"type": "state_update"}
        await manager.notify(3, message)

        ws.send_text.assert_awaited_once_with(json.dumps(message))


class TestOnNotification:
    """Tests for the _on_notification callback."""

    @pytest.mark.asyncio
    async def test_on_notification_broadcasts_to_room(self, manager):
        """A valid NOTIFY payload triggers broadcast to the correct room."""
        ws = _make_ws()
        await manager.connect(ws, game_id=10)

        payload = json.dumps({
            "game_id": 10,
            "message": {"type": "game_state_update", "data": {"round": 3}},
        })

        mock_conn = MagicMock()
        manager._on_notification(mock_conn, 123, PG_CHANNEL, payload)

        # Allow the created task to run
        await asyncio.sleep(0)

        ws.send_text.assert_awaited_once_with(
            json.dumps({"type": "game_state_update", "data": {"round": 3}})
        )

    @pytest.mark.asyncio
    async def test_on_notification_ignores_invalid_json(self, manager):
        """Invalid JSON payloads are logged and ignored."""
        mock_conn = MagicMock()
        # Should not raise
        manager._on_notification(mock_conn, 123, PG_CHANNEL, "not-json")

    @pytest.mark.asyncio
    async def test_on_notification_ignores_missing_keys(self, manager):
        """Payloads missing required keys are logged and ignored."""
        mock_conn = MagicMock()
        # Missing 'message' key
        manager._on_notification(mock_conn, 123, PG_CHANNEL, json.dumps({"game_id": 1}))

    @pytest.mark.asyncio
    async def test_on_notification_different_room(self, manager):
        """Notification for a room with no local connections is a no-op."""
        ws = _make_ws()
        await manager.connect(ws, game_id=1)

        payload = json.dumps({
            "game_id": 999,
            "message": {"type": "test"},
        })
        mock_conn = MagicMock()
        manager._on_notification(mock_conn, 123, PG_CHANNEL, payload)

        await asyncio.sleep(0)

        ws.send_text.assert_not_awaited()


class TestParseDsn:
    """Tests for DSN parsing utility."""

    def test_standard_postgresql_url(self):
        url = "postgresql://user:pass@host:5432/db"
        assert _parse_dsn(url) == "postgresql://user:pass@host:5432/db"

    def test_psycopg2_dialect_stripped(self):
        url = "postgresql+psycopg2://user:pass@host:5432/db"
        assert _parse_dsn(url) == "postgresql://user:pass@host:5432/db"


class TestStopListening:
    """Tests for the stop_listening cleanup."""

    @pytest.mark.asyncio
    async def test_stop_listening_when_not_started(self, manager):
        """stop_listening is safe to call when never started."""
        await manager.stop_listening()  # should not raise
        assert manager._listen_conn is None
        assert manager._notify_pool is None

    @pytest.mark.asyncio
    async def test_stop_listening_closes_connections(self, manager):
        """stop_listening properly closes conn and pool."""
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        manager._listen_conn = mock_conn
        manager._notify_pool = mock_pool

        await manager.stop_listening()

        mock_conn.remove_listener.assert_awaited_once()
        mock_conn.close.assert_awaited_once()
        mock_pool.close.assert_awaited_once()
        assert manager._listen_conn is None
        assert manager._notify_pool is None
