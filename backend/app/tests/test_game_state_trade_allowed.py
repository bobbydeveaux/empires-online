"""Tests for trade_allowed flag in GameState and broadcast payloads."""

import pytest
from unittest.mock import patch, AsyncMock

from app.main import app
from app.core.database import get_db
from app.api.routes.auth import get_current_user
from app.models.models import Player, Game, SpawnedCountry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _override_user(player: Player):
    async def _inner():
        return player
    return _inner


def _create_game(client, player, rounds=2):
    app.dependency_overrides[get_current_user] = _override_user(player)
    resp = client.post("/api/games/", json={"rounds": rounds, "countries": ["England", "France"]})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _join_game(client, game_id, player, country_id):
    app.dependency_overrides[get_current_user] = _override_user(player)
    resp = client.post(f"/api/games/{game_id}/join", json={"country_id": country_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _start_game(client, game_id, creator):
    app.dependency_overrides[get_current_user] = _override_user(creator)
    resp = client.post(f"/api/games/{game_id}/start")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _develop(client, game_id, sc_id, player):
    app.dependency_overrides[get_current_user] = _override_user(player)
    resp = client.post(f"/api/games/{game_id}/countries/{sc_id}/develop")
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestTradeAllowedInGameState:
    """Verify trade_allowed is correctly set in GET /api/games/{game_id}."""

    def test_trade_allowed_false_in_waiting_phase(self, mock_bc, client, seed_data):
        """trade_allowed should be False when game is in waiting phase."""
        p1 = seed_data["player1"]
        game = _create_game(client, p1, rounds=2)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.get(f"/api/games/{game['id']}")
        assert resp.status_code == 200
        assert resp.json()["trade_allowed"] is False

    def test_trade_allowed_false_in_development_phase(self, mock_bc, client, seed_data):
        """trade_allowed should be False during development phase."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = _create_game(client, p1, rounds=2)
        game_id = game["id"]
        _join_game(client, game_id, p1, countries[0].id)
        _join_game(client, game_id, p2, countries[1].id)
        _start_game(client, game_id, p1)  # Now in development

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.get(f"/api/games/{game_id}")
        assert resp.status_code == 200
        assert resp.json()["trade_allowed"] is False

    def test_trade_allowed_true_in_actions_phase(self, mock_bc, client, seed_data):
        """trade_allowed should be True during actions phase."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = _create_game(client, p1, rounds=2)
        game_id = game["id"]
        join1 = _join_game(client, game_id, p1, countries[0].id)
        join2 = _join_game(client, game_id, p2, countries[1].id)
        _start_game(client, game_id, p1)

        # Both develop → auto-transition to actions
        _develop(client, game_id, join1["spawned_country_id"], p1)
        _develop(client, game_id, join2["spawned_country_id"], p2)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.get(f"/api/games/{game_id}")
        assert resp.status_code == 200
        assert resp.json()["trade_allowed"] is True


@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestTradeAllowedInBroadcastPayload:
    """Verify trade_allowed is included in WebSocket game_state_update payloads."""

    def test_broadcast_payload_includes_trade_allowed_false_in_development(
        self, mock_bc, client, seed_data
    ):
        """game_state_update broadcast during development should have trade_allowed=False."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = _create_game(client, p1, rounds=2)
        game_id = game["id"]
        _join_game(client, game_id, p1, countries[0].id)
        _join_game(client, game_id, p2, countries[1].id)
        _start_game(client, game_id, p1)

        # Find game_state_update broadcast calls
        for call in mock_bc.call_args_list:
            args = call[0]
            if len(args) >= 2 and isinstance(args[1], dict):
                msg = args[1]
                if msg.get("type") == "game_state_update" and "game_state" in msg:
                    assert msg["game_state"]["trade_allowed"] is False

    def test_broadcast_payload_includes_trade_allowed_true_in_actions(
        self, mock_bc, client, seed_data
    ):
        """game_state_update broadcast after transition to actions should have trade_allowed=True."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = _create_game(client, p1, rounds=2)
        game_id = game["id"]
        join1 = _join_game(client, game_id, p1, countries[0].id)
        join2 = _join_game(client, game_id, p2, countries[1].id)
        _start_game(client, game_id, p1)

        mock_bc.reset_mock()

        # Both develop → auto-transition to actions
        _develop(client, game_id, join1["spawned_country_id"], p1)
        _develop(client, game_id, join2["spawned_country_id"], p2)

        # Find the last game_state_update broadcast (after phase transition to actions)
        found_actions_payload = False
        for call in mock_bc.call_args_list:
            args = call[0]
            if len(args) >= 2 and isinstance(args[1], dict):
                msg = args[1]
                if (
                    msg.get("type") == "game_state_update"
                    and "game_state" in msg
                    and msg["game_state"]["trade_allowed"] is True
                ):
                    found_actions_payload = True
        assert found_actions_payload, "Expected a game_state_update with trade_allowed=True after actions phase transition"
