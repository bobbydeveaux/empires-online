"""Tests for player stats and global leaderboard endpoints."""

import json
import pytest
from datetime import datetime

from app.models.models import GameResult, Game, SpawnedCountry
from app.tests.conftest import _auth_header


class TestGlobalLeaderboard:
    """Tests for GET /api/players/leaderboard."""

    def test_empty_leaderboard(self, client):
        """Returns empty list when no games have been completed."""
        resp = client.get("/api/players/leaderboard")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_leaderboard_with_results(self, client, db_session, seed_data):
        """Returns players ranked by wins then average score."""
        p1 = seed_data["player1"]
        p2 = seed_data["player2"]
        countries = seed_data["countries"]

        # Create a completed game
        game = Game(rounds=3, rounds_remaining=0, phase="completed", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=6, banks=0,
            supporters=0, revolters=0,
        )
        db_session.add(sc1)
        db_session.commit()
        db_session.refresh(sc1)

        rankings = [
            {"placement": 1, "player_id": p1.id, "player_name": "alice", "country_name": "England", "score": 25, "breakdown": {}},
            {"placement": 2, "player_id": p2.id, "player_name": "bob", "country_name": "France", "score": 18, "breakdown": {}},
        ]
        result = GameResult(
            game_id=game.id,
            winner_country_id=sc1.id,
            winner_player_id=p1.id,
            duration_rounds=3,
            final_rankings=json.dumps(rankings),
        )
        db_session.add(result)
        db_session.commit()

        resp = client.get("/api/players/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["player_name"] == "alice"
        assert data[0]["wins"] == 1
        assert data[0]["games_played"] == 1
        assert data[0]["best_score"] == 25
        assert data[1]["player_name"] == "bob"
        assert data[1]["wins"] == 0


class TestPlayerStats:
    """Tests for GET /api/players/{player_id}/stats."""

    def test_player_not_found(self, client):
        """Returns 404 for non-existent player."""
        resp = client.get("/api/players/9999/stats")
        assert resp.status_code == 404

    def test_player_with_no_games(self, client, seed_data):
        """Returns zero stats when player has no completed games."""
        p1 = seed_data["player1"]
        resp = client.get(f"/api/players/{p1.id}/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "alice"
        assert data["games_played"] == 0
        assert data["wins"] == 0
        assert data["average_score"] == 0
        assert data["game_history"] == []

    def test_player_with_game_history(self, client, db_session, seed_data):
        """Returns correct stats when player has completed games."""
        p1 = seed_data["player1"]
        p2 = seed_data["player2"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=0, phase="completed", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=6, banks=0,
            supporters=0, revolters=0,
        )
        sc2 = SpawnedCountry(
            country_id=countries[1].id, game_id=game.id, player_id=p2.id,
            gold=8, bonds=1, territories=6, goods=5, people=5, banks=0,
            supporters=0, revolters=0,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()
        db_session.refresh(sc1)

        rankings = [
            {"placement": 1, "player_id": p1.id, "player_name": "alice", "country_name": "England", "score": 30, "breakdown": {}},
            {"placement": 2, "player_id": p2.id, "player_name": "bob", "country_name": "France", "score": 20, "breakdown": {}},
        ]
        result = GameResult(
            game_id=game.id,
            winner_country_id=sc1.id,
            winner_player_id=p1.id,
            duration_rounds=5,
            final_rankings=json.dumps(rankings),
        )
        db_session.add(result)
        db_session.commit()

        resp = client.get(f"/api/players/{p1.id}/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "alice"
        assert data["games_played"] == 1
        assert data["wins"] == 1
        assert data["best_score"] == 30
        assert data["average_score"] == 30.0
        assert data["favorite_country"] == "England"
        assert len(data["game_history"]) == 1
        assert data["game_history"][0]["placement"] == 1
        assert data["game_history"][0]["score"] == 30
        assert data["countries_played"]["England"] == 1
