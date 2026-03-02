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
