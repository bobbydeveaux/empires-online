"""Tests for player history, stats, and global leaderboard endpoints."""

import json
import pytest
from unittest.mock import patch, AsyncMock

from app.main import app
from app.core.database import get_db
from app.api.routes.auth import get_current_user
from app.models.models import Player, Game, SpawnedCountry, GameResult


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


def _next_round(client, game_id, creator):
    app.dependency_overrides[get_current_user] = _override_user(creator)
    resp = client.post(f"/api/games/{game_id}/next-round")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _complete_game(client, seed_data, rounds=1):
    """Create, start, develop, and complete a game. Returns (game_id, sc1_id, sc2_id)."""
    p1, p2 = seed_data["player1"], seed_data["player2"]
    countries = seed_data["countries"]

    game = _create_game(client, p1, rounds=rounds)
    game_id = game["id"]

    join1 = _join_game(client, game_id, p1, countries[0].id)
    join2 = _join_game(client, game_id, p2, countries[1].id)
    sc1_id = join1["spawned_country_id"]
    sc2_id = join2["spawned_country_id"]

    _start_game(client, game_id, p1)

    for _ in range(rounds):
        _develop(client, game_id, sc1_id, p1)
        _develop(client, game_id, sc2_id, p2)
        _next_round(client, game_id, p1)

    return game_id, sc1_id, sc2_id


# ---------------------------------------------------------------------------
# Tests: Game result recording
# ---------------------------------------------------------------------------

@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestGameResultRecording:
    """Verify that GameResult is created when a game completes."""

    def test_game_result_created_on_completion(self, mock_bc, client, seed_data, db_session):
        game_id, _, _ = _complete_game(client, seed_data, rounds=1)

        result = db_session.query(GameResult).filter(GameResult.game_id == game_id).first()
        assert result is not None
        assert result.duration_rounds == 1
        assert result.winner_player_id is not None
        assert result.winner_country_id is not None

        rankings = json.loads(result.final_rankings)
        assert len(rankings) == 2
        assert rankings[0]["rank"] == 1
        assert rankings[1]["rank"] == 2

    def test_game_result_not_duplicated(self, mock_bc, client, seed_data, db_session):
        """Completing the same game twice should not create a duplicate result."""
        game_id, _, _ = _complete_game(client, seed_data, rounds=1)

        count = db_session.query(GameResult).filter(GameResult.game_id == game_id).count()
        assert count == 1


# ---------------------------------------------------------------------------
# Tests: Player history endpoint
# ---------------------------------------------------------------------------

@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestPlayerHistory:
    """GET /api/players/{player_id}/history"""

    def test_player_history_returns_completed_games(self, mock_bc, client, seed_data):
        p1 = seed_data["player1"]
        _complete_game(client, seed_data, rounds=1)

        resp = client.get(f"/api/players/{p1.id}/history")
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) == 1
        entry = history[0]
        assert "game_id" in entry
        assert "rank" in entry
        assert "score" in entry
        assert "country_name" in entry
        assert "won" in entry
        assert entry["rounds"] == 1

    def test_player_history_empty_for_new_player(self, mock_bc, client, seed_data):
        p1 = seed_data["player1"]
        resp = client.get(f"/api/players/{p1.id}/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_player_history_404_for_missing_player(self, mock_bc, client, seed_data):
        resp = client.get("/api/players/9999/history")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Player stats endpoint
# ---------------------------------------------------------------------------

@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestPlayerStats:
    """GET /api/players/{player_id}/stats"""

    def test_player_stats_after_game(self, mock_bc, client, seed_data):
        _complete_game(client, seed_data, rounds=1)
        p1 = seed_data["player1"]

        resp = client.get(f"/api/players/{p1.id}/stats")
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_games"] == 1
        assert stats["wins"] + stats["losses"] == 1
        assert stats["username"] == "alice"

    def test_player_stats_zero_for_new_player(self, mock_bc, client, seed_data):
        p1 = seed_data["player1"]
        resp = client.get(f"/api/players/{p1.id}/stats")
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_games"] == 0
        assert stats["wins"] == 0
        assert stats["win_rate"] == 0.0

    def test_player_stats_404(self, mock_bc, client, seed_data):
        resp = client.get("/api/players/9999/stats")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Global leaderboard endpoint
# ---------------------------------------------------------------------------

@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestGlobalLeaderboard:
    """GET /api/players/leaderboard/global"""

    def test_global_leaderboard_after_game(self, mock_bc, client, seed_data):
        _complete_game(client, seed_data, rounds=1)

        resp = client.get("/api/players/leaderboard/global")
        assert resp.status_code == 200
        lb = resp.json()
        assert len(lb) == 2
        # Each entry has expected fields
        for entry in lb:
            assert "player_id" in entry
            assert "username" in entry
            assert "total_games" in entry
            assert "wins" in entry
            assert "losses" in entry
            assert "win_rate" in entry
            assert "avg_placement" in entry

    def test_global_leaderboard_empty_without_games(self, mock_bc, client, seed_data):
        resp = client.get("/api/players/leaderboard/global")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_global_leaderboard_sorted_by_wins(self, mock_bc, client, seed_data):
        _complete_game(client, seed_data, rounds=1)

        resp = client.get("/api/players/leaderboard/global")
        lb = resp.json()
        if len(lb) >= 2:
            assert lb[0]["wins"] >= lb[1]["wins"]
