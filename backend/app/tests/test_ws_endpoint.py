"""Integration tests for the WebSocket endpoint with JWT authentication."""

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.auth import create_access_token
from app.services.ws_manager import ConnectionManager


def _create_token(username: str = "testuser") -> str:
    """Create a valid JWT token for testing."""
    return create_access_token(
        data={"sub": username}, expires_delta=timedelta(minutes=30)
    )


def _create_expired_token(username: str = "testuser") -> str:
    """Create an expired JWT token for testing."""
    return create_access_token(
        data={"sub": username}, expires_delta=timedelta(minutes=-1)
    )


def _mock_player(player_id: int = 1, username: str = "testuser"):
    """Create a mock Player object."""
    player = MagicMock()
    player.id = player_id
    player.username = username
    return player


class TestWebSocketEndpoint:

    def test_connect_with_valid_token(self):
        """Test that a valid JWT token allows WebSocket connection."""
        token = _create_token("testuser")
        mock_player = _mock_player()

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1?token={token}") as ws:
                # Should receive the player_joined broadcast
                data = ws.receive_json()
                assert data["type"] == "player_joined"
                assert data["game_id"] == 1
                assert data["player"]["id"] == 1
                assert data["player"]["username"] == "testuser"

    def test_reject_without_token(self):
        """Test that connections without a token are rejected."""
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/1"):
                pass  # Should not reach here

    def test_reject_with_invalid_token(self):
        """Test that connections with an invalid token are rejected."""
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/1?token=invalid.token.here"):
                pass

    def test_reject_with_expired_token(self):
        """Test that connections with an expired token are rejected."""
        token = _create_expired_token("testuser")
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/1?token={token}"):
                pass

    def test_reject_with_unknown_user(self):
        """Test that a valid token for a non-existent user is rejected."""
        token = _create_token("nonexistent")

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=None):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/1?token={token}"):
                    pass

    def test_ping_pong(self):
        """Test that a ping message receives a pong response."""
        token = _create_token("testuser")
        mock_player = _mock_player()

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1?token={token}") as ws:
                # Consume the player_joined broadcast
                ws.receive_json()

                # Send a ping
                ws.send_json({"type": "ping"})
                data = ws.receive_json()
                assert data["type"] == "pong"

    def test_chat_message_broadcast(self):
        """Test that chat messages are broadcast to the room."""
        token = _create_token("testuser")
        mock_player = _mock_player()

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1?token={token}") as ws:
                # Consume the player_joined broadcast
                ws.receive_json()

                # Send a chat message
                ws.send_json({"type": "chat", "message": "Hello!"})
                data = ws.receive_json()
                assert data["type"] == "chat"
                assert data["game_id"] == 1
                assert data["message"] == "Hello!"
                assert data["player"]["username"] == "testuser"

    def test_unknown_message_type(self):
        """Test that unknown message types receive an error response."""
        token = _create_token("testuser")
        mock_player = _mock_player()

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1?token={token}") as ws:
                # Consume the player_joined broadcast
                ws.receive_json()

                # Send an unknown message type
                ws.send_json({"type": "unknown_action"})
                data = ws.receive_json()
                assert data["type"] == "error"
                assert "Unknown message type" in data["message"]

    def test_disconnect_broadcasts_player_left(self):
        """Test that disconnecting broadcasts a player_left message.

        We verify the disconnect path by connecting, then closing,
        and checking that the manager cleaned up.
        """
        token = _create_token("testuser")
        mock_player = _mock_player()

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            from app.services.ws_manager import manager

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1?token={token}") as ws:
                ws.receive_json()  # player_joined

            # After context exit (disconnect), the manager should have cleaned up
            # The room should be empty or removed
            assert manager.get_room_count(1) == 0


class TestWebSocketBroadcasting:
    """Tests for game state broadcasting via WebSocket."""

    def test_two_clients_receive_broadcast(self):
        """Two clients in the same game room both receive broadcasts."""
        token1 = _create_token("player1")
        token2 = _create_token("player2")
        mock_player1 = _mock_player(player_id=1, username="player1")
        mock_player2 = _mock_player(player_id=2, username="player2")

        def get_player_side_effect(db, username):
            if username == "player1":
                return mock_player1
            if username == "player2":
                return mock_player2
            return None

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", side_effect=get_player_side_effect):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1?token={token1}") as ws1:
                # ws1 receives its own player_joined
                data1 = ws1.receive_json()
                assert data1["type"] == "player_joined"
                assert data1["player"]["username"] == "player1"

                with client.websocket_connect(f"/ws/1?token={token2}") as ws2:
                    # ws2 receives player_joined for player2
                    data2 = ws2.receive_json()
                    assert data2["type"] == "player_joined"
                    assert data2["player"]["username"] == "player2"

                    # ws1 also receives player_joined for player2
                    data1_broadcast = ws1.receive_json()
                    assert data1_broadcast["type"] == "player_joined"
                    assert data1_broadcast["player"]["username"] == "player2"

    def test_chat_broadcast_to_all_clients(self):
        """A chat message from one client is broadcast to all clients in the room."""
        token1 = _create_token("player1")
        token2 = _create_token("player2")
        mock_player1 = _mock_player(player_id=1, username="player1")
        mock_player2 = _mock_player(player_id=2, username="player2")

        def get_player_side_effect(db, username):
            if username == "player1":
                return mock_player1
            if username == "player2":
                return mock_player2
            return None

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", side_effect=get_player_side_effect):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(f"/ws/1?token={token1}") as ws1:
                ws1.receive_json()  # player_joined

                with client.websocket_connect(f"/ws/1?token={token2}") as ws2:
                    ws2.receive_json()  # player_joined for player2
                    ws1.receive_json()  # player_joined for player2 (broadcast)

                    # player1 sends a chat
                    ws1.send_json({"type": "chat", "message": "Hello everyone!"})

                    # Both clients receive the chat broadcast
                    chat1 = ws1.receive_json()
                    assert chat1["type"] == "chat"
                    assert chat1["message"] == "Hello everyone!"
                    assert chat1["player"]["username"] == "player1"

                    chat2 = ws2.receive_json()
                    assert chat2["type"] == "chat"
                    assert chat2["message"] == "Hello everyone!"
                    assert chat2["player"]["username"] == "player1"

    def test_different_rooms_isolated(self):
        """Clients in different game rooms do not receive each other's broadcasts."""
        token1 = _create_token("player1")
        token2 = _create_token("player2")
        mock_player1 = _mock_player(player_id=1, username="player1")
        mock_player2 = _mock_player(player_id=2, username="player2")

        def get_player_side_effect(db, username):
            if username == "player1":
                return mock_player1
            if username == "player2":
                return mock_player2
            return None

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", side_effect=get_player_side_effect):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            # player1 in game 1, player2 in game 2
            with client.websocket_connect(f"/ws/1?token={token1}") as ws1:
                ws1.receive_json()  # player_joined

                with client.websocket_connect(f"/ws/2?token={token2}") as ws2:
                    ws2.receive_json()  # player_joined

                    # player1 sends a chat in game 1
                    ws1.send_json({"type": "chat", "message": "Game 1 only"})
                    chat1 = ws1.receive_json()
                    assert chat1["type"] == "chat"
                    assert chat1["game_id"] == 1

                    # player2 should NOT receive it - send a ping to verify
                    ws2.send_json({"type": "ping"})
                    pong = ws2.receive_json()
                    assert pong["type"] == "pong"


class TestWebSocketReconnection:
    """Tests for WebSocket reconnection handling."""

    def test_reconnect_after_disconnect(self):
        """Client can reconnect to the same game room after disconnection."""
        token = _create_token("testuser")
        mock_player = _mock_player()

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            from app.services.ws_manager import manager
            client = TestClient(app)

            # First connection
            with client.websocket_connect(f"/ws/1?token={token}") as ws:
                data = ws.receive_json()
                assert data["type"] == "player_joined"

            # After disconnect, room should be cleaned up
            assert manager.get_room_count(1) == 0

            # Reconnect
            with client.websocket_connect(f"/ws/1?token={token}") as ws:
                data = ws.receive_json()
                assert data["type"] == "player_joined"
                assert data["player"]["username"] == "testuser"
                assert manager.get_room_count(1) == 1

                # Verify the connection works (ping/pong)
                ws.send_json({"type": "ping"})
                pong = ws.receive_json()
                assert pong["type"] == "pong"

    def test_reconnect_room_still_has_other_clients(self):
        """When one client disconnects and reconnects, other clients remain connected."""
        token1 = _create_token("player1")
        token2 = _create_token("player2")
        mock_player1 = _mock_player(player_id=1, username="player1")
        mock_player2 = _mock_player(player_id=2, username="player2")

        def get_player_side_effect(db, username):
            if username == "player1":
                return mock_player1
            if username == "player2":
                return mock_player2
            return None

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", side_effect=get_player_side_effect):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            from app.services.ws_manager import manager
            client = TestClient(app)

            with client.websocket_connect(f"/ws/1?token={token2}") as ws2:
                ws2.receive_json()  # player_joined for player2

                # player1 connects then disconnects
                with client.websocket_connect(f"/ws/1?token={token1}") as ws1:
                    ws1.receive_json()  # player_joined for player1
                    ws2.receive_json()  # broadcast: player_joined for player1
                    assert manager.get_room_count(1) == 2

                # player1 disconnected, room still has player2
                # Consume the player_left broadcast
                left_msg = ws2.receive_json()
                assert left_msg["type"] == "player_left"
                assert left_msg["player"]["username"] == "player1"
                assert manager.get_room_count(1) == 1

                # player1 reconnects
                with client.websocket_connect(f"/ws/1?token={token1}") as ws1:
                    ws1.receive_json()  # player_joined
                    rejoined = ws2.receive_json()  # player2 receives player_joined
                    assert rejoined["type"] == "player_joined"
                    assert rejoined["player"]["username"] == "player1"
                    assert manager.get_room_count(1) == 2

    def test_authorization_header_fallback(self):
        """Test that WebSocket accepts token from Authorization header."""
        token = _create_token("testuser")
        mock_player = _mock_player()

        with patch("app.api.routes.ws._get_db") as mock_get_db, \
             patch("app.api.routes.ws._get_player", return_value=mock_player):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            client = TestClient(app)
            with client.websocket_connect(
                "/ws/1",
                headers={"Authorization": f"Bearer {token}"},
            ) as ws:
                data = ws.receive_json()
                assert data["type"] == "player_joined"
                assert data["player"]["username"] == "testuser"
