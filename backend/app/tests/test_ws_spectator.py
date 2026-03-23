"""Tests for spectator WebSocket support."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.auth import create_access_token
from app.services.ws_manager import ConnectionManager


def _make_ws():
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


def _create_token(username: str = "testuser") -> str:
    return create_access_token(
        data={"sub": username}, expires_delta=timedelta(minutes=30)
    )


def _mock_player(player_id: int = 1, username: str = "testuser"):
    player = MagicMock()
    player.id = player_id
    player.username = username
    return player


# ---------------------------------------------------------------------------
# Unit tests for ConnectionManager spectator support
# ---------------------------------------------------------------------------


class TestConnectionManagerSpectators:

    @pytest.fixture
    def manager(self):
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_connect_spectator_adds_to_spectators(self, manager):
        ws = _make_ws()
        await manager.connect_spectator(ws, game_id=1)

        ws.accept.assert_awaited_once()
        assert manager.get_spectator_count(1) == 1
        assert manager.get_room_count(1) == 0

    @pytest.mark.asyncio
    async def test_spectator_disconnect_removes_from_spectators(self, manager):
        ws = _make_ws()
        await manager.connect_spectator(ws, game_id=1)
        manager.disconnect(ws)

        assert manager.get_spectator_count(1) == 0

    @pytest.mark.asyncio
    async def test_is_spectator_flag(self, manager):
        ws_player = _make_ws()
        ws_spectator = _make_ws()

        await manager.connect(ws_player, game_id=1)
        await manager.connect_spectator(ws_spectator, game_id=1)

        assert manager.is_spectator(ws_player) is False
        assert manager.is_spectator(ws_spectator) is True

    @pytest.mark.asyncio
    async def test_broadcast_reaches_spectators(self, manager):
        ws_player = _make_ws()
        ws_spectator = _make_ws()

        await manager.connect(ws_player, game_id=1)
        await manager.connect_spectator(ws_spectator, game_id=1)

        message = {"type": "game_state_update", "data": "test"}
        await manager.broadcast_to_room(1, message)

        payload = json.dumps(message)
        ws_player.send_text.assert_awaited_once_with(payload)
        ws_spectator.send_text.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_spectator_count_accurate(self, manager):
        ws1 = _make_ws()
        ws2 = _make_ws()
        ws3 = _make_ws()

        await manager.connect_spectator(ws1, game_id=1)
        await manager.connect_spectator(ws2, game_id=1)
        await manager.connect(ws3, game_id=1)

        assert manager.get_spectator_count(1) == 2
        assert manager.get_room_count(1) == 1

        manager.disconnect(ws1)
        assert manager.get_spectator_count(1) == 1

    @pytest.mark.asyncio
    async def test_spectator_different_room_isolated(self, manager):
        ws_spec_room1 = _make_ws()
        ws_spec_room2 = _make_ws()

        await manager.connect_spectator(ws_spec_room1, game_id=1)
        await manager.connect_spectator(ws_spec_room2, game_id=2)

        await manager.broadcast_to_room(1, {"type": "test"})

        ws_spec_room1.send_text.assert_awaited_once()
        ws_spec_room2.send_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_spectator_room_removed(self, manager):
        ws = _make_ws()
        await manager.connect_spectator(ws, game_id=5)
        manager.disconnect(ws)

        assert 5 not in manager._spectators

    @pytest.mark.asyncio
    async def test_broadcast_handles_failed_spectator_send(self, manager):
        ws_good = _make_ws()
        ws_bad = _make_ws()
        ws_bad.send_text.side_effect = Exception("connection lost")

        await manager.connect(ws_good, game_id=1)
        await manager.connect_spectator(ws_bad, game_id=1)

        await manager.broadcast_to_room(1, {"type": "test"})

        ws_good.send_text.assert_awaited_once()
        assert manager.get_spectator_count(1) == 0

    @pytest.mark.asyncio
    async def test_is_spectator_unknown_websocket(self, manager):
        ws = _make_ws()
        assert manager.is_spectator(ws) is False


# ---------------------------------------------------------------------------
# Integration tests for spectator WebSocket endpoint
# ---------------------------------------------------------------------------


class TestSpectatorWebSocketEndpoint:

    def test_spectator_connect_with_valid_token(self):
        token = _create_token("spectator1")
        mock_player = _mock_player(player_id=10, username="spectator1")

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1/spectate?token={token}") as ws:
                data = ws.receive_json()
                assert data["type"] == "spectator_joined"
                assert data["game_id"] == 1
                assert data["spectator_count"] == 1

    def test_spectator_reject_without_token(self):
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/1/spectate"):
                pass

    def test_spectator_reject_invalid_token(self):
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/1/spectate?token=bad.token"):
                pass

    def test_spectator_ping_pong(self):
        token = _create_token("spectator1")
        mock_player = _mock_player(player_id=10, username="spectator1")

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1/spectate?token={token}") as ws:
                ws.receive_json()  # spectator_joined
                ws.send_json({"type": "ping"})
                data = ws.receive_json()
                assert data["type"] == "pong"

    def test_spectator_chat_rejected_with_403(self):
        token = _create_token("spectator1")
        mock_player = _mock_player(player_id=10, username="spectator1")

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1/spectate?token={token}") as ws:
                ws.receive_json()  # spectator_joined
                ws.send_json({"type": "chat", "message": "Hello!"})
                data = ws.receive_json()
                assert data["type"] == "error"
                assert data["code"] == 403
                assert "Spectators cannot perform actions" in data["message"]

    def test_spectator_action_rejected_with_403(self):
        token = _create_token("spectator1")
        mock_player = _mock_player(player_id=10, username="spectator1")

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1/spectate?token={token}") as ws:
                ws.receive_json()  # spectator_joined
                ws.send_json({"type": "action", "action": "buy_bond"})
                data = ws.receive_json()
                assert data["type"] == "error"
                assert data["code"] == 403

    def test_spectator_unknown_type_rejected_with_403(self):
        token = _create_token("spectator1")
        mock_player = _mock_player(player_id=10, username="spectator1")

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1/spectate?token={token}") as ws:
                ws.receive_json()  # spectator_joined
                ws.send_json({"type": "unknown_thing"})
                data = ws.receive_json()
                assert data["type"] == "error"
                assert data["code"] == 403

    def test_spectator_receives_player_broadcasts(self):
        """Spectator receives broadcasts from player actions in the same room."""
        token_player = _create_token("player1")
        token_spectator = _create_token("spectator1")
        mock_player1 = _mock_player(player_id=1, username="player1")
        mock_spectator = _mock_player(player_id=10, username="spectator1")

        def get_player_side_effect(db, username):
            if username == "player1":
                return mock_player1
            if username == "spectator1":
                return mock_spectator
            return None

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", side_effect=get_player_side_effect):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1/spectate?token={token_spectator}") as ws_spec:
                ws_spec.receive_json()  # spectator_joined

                with client.websocket_connect(f"/ws/1?token={token_player}") as ws_player:
                    ws_player.receive_json()  # player_joined (player sees own join)
                    spec_msg = ws_spec.receive_json()  # spectator also gets player_joined
                    assert spec_msg["type"] == "player_joined"
                    assert spec_msg["player"]["username"] == "player1"

    def test_spectator_disconnect_broadcasts_left(self):
        token = _create_token("spectator1")
        mock_player = _mock_player(player_id=10, username="spectator1")
        token_player = _create_token("player1")
        mock_player1 = _mock_player(player_id=1, username="player1")

        def get_player_side_effect(db, username):
            if username == "player1":
                return mock_player1
            if username == "spectator1":
                return mock_player
            return None

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", side_effect=get_player_side_effect):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            from app.services.ws_manager import manager
            client = TestClient(app)

            with client.websocket_connect(f"/ws/1?token={token_player}") as ws_player:
                ws_player.receive_json()  # player_joined

                with client.websocket_connect(f"/ws/1/spectate?token={token}") as ws_spec:
                    ws_spec.receive_json()  # spectator_joined
                    # Player also gets spectator_joined
                    player_msg = ws_player.receive_json()
                    assert player_msg["type"] == "spectator_joined"

                # Spectator disconnected - player should get spectator_left
                left_msg = ws_player.receive_json()
                assert left_msg["type"] == "spectator_left"
                assert left_msg["spectator_count"] == 0
