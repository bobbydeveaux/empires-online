"""Integration tests for spectator mode.

Covers:
- POST /games/{game_id}/spectate endpoint
- Spectator token validation
- GET /games/ with spectator_count and games_with_spectators filter
- WebSocket spectator connection flow
"""

import json
import pytest
from datetime import timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.api.routes.auth import get_current_user, create_access_token
from app.models.models import Player, Game
from app.services.ws_manager import ConnectionManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _override_user(player: Player):
    """Dependency override that returns *player* as the current user."""
    async def _inner():
        return player
    return _inner


def _create_game(client, player, rounds=2):
    """Create a game as *player* and return the response JSON."""
    app.dependency_overrides[get_current_user] = _override_user(player)
    resp = client.post("/api/games/", json={"rounds": rounds, "countries": ["England", "France"]})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _join_game(client, game_id, player, country_id):
    """Join a game as *player* with *country_id*."""
    app.dependency_overrides[get_current_user] = _override_user(player)
    resp = client.post(f"/api/games/{game_id}/join", json={"country_id": country_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _start_game(client, game_id, creator):
    """Start a game as *creator*."""
    app.dependency_overrides[get_current_user] = _override_user(creator)
    resp = client.post(f"/api/games/{game_id}/start")
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests: POST /games/{game_id}/spectate
# ---------------------------------------------------------------------------

@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestSpectateEndpoint:
    """POST /api/games/{game_id}/spectate"""

    def test_spectate_returns_token_for_waiting_game(self, mock_bc, client, seed_data):
        p1 = seed_data["player1"]
        game = _create_game(client, p1)

        resp = client.post(f"/api/games/{game['id']}/spectate")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["is_spectator"] is True

    def test_spectate_returns_token_for_started_game(self, mock_bc, client, seed_data):
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = _create_game(client, p1)
        _join_game(client, game["id"], p1, countries[0].id)
        _join_game(client, game["id"], p2, countries[1].id)
        _start_game(client, game["id"], p1)

        resp = client.post(f"/api/games/{game['id']}/spectate")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["is_spectator"] is True

    def test_spectate_404_for_missing_game(self, mock_bc, client, seed_data):
        resp = client.post("/api/games/9999/spectate")
        assert resp.status_code == 404

    def test_spectate_400_for_completed_game(self, mock_bc, client, seed_data, db_session):
        p1 = seed_data["player1"]
        game_data = _create_game(client, p1)

        # Manually set game to completed
        game = db_session.query(Game).filter(Game.id == game_data["id"]).first()
        game.phase = "completed"
        db_session.commit()

        resp = client.post(f"/api/games/{game_data['id']}/spectate")
        assert resp.status_code == 400
        assert "not active" in resp.json()["detail"]

    def test_spectate_token_contains_spectator_claims(self, mock_bc, client, seed_data):
        """The JWT token should contain is_spectator and game_id claims."""
        from jose import jwt
        from app.core.config import settings

        p1 = seed_data["player1"]
        game = _create_game(client, p1)

        resp = client.post(f"/api/games/{game['id']}/spectate")
        token = resp.json()["access_token"]

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["is_spectator"] is True
        assert payload["game_id"] == game["id"]
        assert payload["sub"] == f"spectator-game-{game['id']}"

    def test_spectate_no_auth_required(self, mock_bc, client, seed_data):
        """Spectate endpoint should work without authentication."""
        p1 = seed_data["player1"]
        game = _create_game(client, p1)

        # Clear all auth overrides
        app.dependency_overrides.pop(get_current_user, None)

        resp = client.post(f"/api/games/{game['id']}/spectate")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: GET /games/ with spectator features
# ---------------------------------------------------------------------------

@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestListGamesWithSpectators:
    """GET /api/games/ with spectator_count and filtering."""

    def test_list_games_includes_spectator_count(self, mock_bc, client, seed_data):
        p1 = seed_data["player1"]
        _create_game(client, p1)

        resp = client.get("/api/games/")
        assert resp.status_code == 200
        games = resp.json()
        assert len(games) >= 1
        # Each game should have spectator_count field
        for game in games:
            assert "spectator_count" in game

    def test_spectator_count_defaults_to_zero(self, mock_bc, client, seed_data):
        p1 = seed_data["player1"]
        _create_game(client, p1)

        resp = client.get("/api/games/")
        games = resp.json()
        assert games[0]["spectator_count"] == 0

    def test_games_with_spectators_filter_excludes_empty(self, mock_bc, client, seed_data):
        """When games_with_spectators=true, games with 0 spectators are excluded."""
        p1 = seed_data["player1"]
        _create_game(client, p1)

        resp = client.get("/api/games/?games_with_spectators=true")
        assert resp.status_code == 200
        games = resp.json()
        # No games have spectators, so result should be empty
        assert len(games) == 0

    def test_games_with_spectators_filter_includes_active(self, mock_bc, client, seed_data):
        """When a game has spectators and filter is on, it should be included."""
        p1 = seed_data["player1"]
        game_data = _create_game(client, p1)

        # Simulate a spectator connection via the manager
        with patch("app.api.routes.games.manager") as mock_manager:
            mock_manager.get_spectator_count.return_value = 2
            resp = client.get("/api/games/?games_with_spectators=true")
            assert resp.status_code == 200
            games = resp.json()
            assert len(games) >= 1
            assert games[0]["spectator_count"] == 2

    def test_list_games_without_filter_returns_all(self, mock_bc, client, seed_data):
        p1 = seed_data["player1"]
        _create_game(client, p1)

        resp = client.get("/api/games/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ---------------------------------------------------------------------------
# Tests: GameState includes spectator_count
# ---------------------------------------------------------------------------

@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestGameStateSpectatorCount:
    """GET /api/games/{game_id} includes spectator_count."""

    def test_game_state_includes_spectator_count(self, mock_bc, client, seed_data):
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = _create_game(client, p1)
        _join_game(client, game["id"], p1, countries[0].id)
        _join_game(client, game["id"], p2, countries[1].id)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.get(f"/api/games/{game['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert "spectator_count" in data
        assert data["spectator_count"] == 0


# ---------------------------------------------------------------------------
# Tests: WebSocket spectator flow
# ---------------------------------------------------------------------------

class TestWebSocketSpectatorFlow:
    """WebSocket connection with spectator token."""

    def test_spectator_connects_with_valid_token(self, client, seed_data):
        """A spectator with a valid token should connect successfully."""
        p1 = seed_data["player1"]
        game = _create_game(client, p1)

        # Get spectator token
        resp = client.post(f"/api/games/{game['id']}/spectate")
        token = resp.json()["access_token"]

        with client.websocket_connect(f"/ws/{game['id']}?token={token}") as ws:
            # Should receive spectator_joined message
            data = ws.receive_json()
            assert data["type"] == "spectator_joined"
            assert data["game_id"] == game["id"]

    def test_spectator_receives_pong(self, client, seed_data):
        """Spectators should be able to send ping and receive pong."""
        p1 = seed_data["player1"]
        game = _create_game(client, p1)

        resp = client.post(f"/api/games/{game['id']}/spectate")
        token = resp.json()["access_token"]

        with client.websocket_connect(f"/ws/{game['id']}?token={token}") as ws:
            ws.receive_json()  # spectator_joined
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_spectator_action_rejected(self, client, seed_data):
        """Spectators cannot send game actions — should get 403 error."""
        p1 = seed_data["player1"]
        game = _create_game(client, p1)

        resp = client.post(f"/api/games/{game['id']}/spectate")
        token = resp.json()["access_token"]

        with client.websocket_connect(f"/ws/{game['id']}?token={token}") as ws:
            ws.receive_json()  # spectator_joined
            ws.send_json({"type": "chat", "message": "hello"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert data["code"] == 403
            assert "Spectators cannot send actions" in data["message"]

    def test_spectator_unknown_action_rejected(self, client, seed_data):
        """Any non-ping message from a spectator should be rejected."""
        p1 = seed_data["player1"]
        game = _create_game(client, p1)

        resp = client.post(f"/api/games/{game['id']}/spectate")
        token = resp.json()["access_token"]

        with client.websocket_connect(f"/ws/{game['id']}?token={token}") as ws:
            ws.receive_json()  # spectator_joined
            ws.send_json({"type": "perform_action", "action": "buy_bond"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert data["code"] == 403

    def test_invalid_token_rejected(self, client, seed_data):
        """An invalid token should close the WebSocket."""
        p1 = seed_data["player1"]
        game = _create_game(client, p1)

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/{game['id']}?token=invalid-token") as ws:
                ws.receive_json()
