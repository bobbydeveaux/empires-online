"""Unit tests for the WebSocket ConnectionManager."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.ws_manager import ConnectionManager


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
