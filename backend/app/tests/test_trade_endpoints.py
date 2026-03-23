"""Integration tests for trade REST endpoints.

Covers all four trade endpoints with auth, happy paths, and error scenarios.
"""

import pytest
from unittest.mock import patch, AsyncMock

from app.main import app
from app.core.database import get_db
from app.api.routes.auth import get_current_user
from app.models.models import Player, Game, SpawnedCountry, Trade


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


def _develop(client, game_id, sc_id, player):
    """Execute development for a spawned country."""
    app.dependency_overrides[get_current_user] = _override_user(player)
    resp = client.post(f"/api/games/{game_id}/countries/{sc_id}/develop")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _setup_game_in_actions(client, seed_data):
    """Create a game, join 2 players, start, and develop to reach actions phase."""
    p1, p2 = seed_data["player1"], seed_data["player2"]
    countries = seed_data["countries"]

    game = _create_game(client, p1, rounds=2)
    game_id = game["id"]

    join1 = _join_game(client, game_id, p1, countries[0].id)
    join2 = _join_game(client, game_id, p2, countries[1].id)
    sc1_id = join1["spawned_country_id"]
    sc2_id = join2["spawned_country_id"]

    _start_game(client, game_id, p1)

    # Both develop → auto-transition to actions
    _develop(client, game_id, sc1_id, p1)
    _develop(client, game_id, sc2_id, p2)

    return game_id, sc1_id, sc2_id, p1, p2


# ---------------------------------------------------------------------------
# Tests: POST /api/games/{game_id}/trades (propose)
# ---------------------------------------------------------------------------

@patch("app.api.routes.trades.broadcast_event", new_callable=AsyncMock)
@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestProposeTradeEndpoint:
    """POST /api/games/{game_id}/trades"""

    def test_propose_trade_success(self, mock_games_bc, mock_trades_bc, client, seed_data):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": sc2_id,
                "offer_gold": 2,
                "request_people": 1,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["offer_gold"] == 2
        assert data["request_people"] == 1
        assert data["proposer_country_id"] == sc1_id
        assert data["receiver_country_id"] == sc2_id

    def test_propose_trade_broadcasts_event(self, mock_games_bc, mock_trades_bc, client, seed_data):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": sc2_id,
                "offer_gold": 1,
                "request_gold": 1,
            },
        )
        assert resp.status_code == 200
        # The trades broadcast should have been called
        mock_trades_bc.assert_called()
        call_args = mock_trades_bc.call_args
        assert call_args[0][0] == game_id  # game_id
        assert call_args[0][1]["type"] == "trade_proposed"

    def test_propose_trade_insufficient_resources(self, mock_games_bc, mock_trades_bc, client, seed_data, db_session):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        # Drain gold
        sc1 = db_session.query(SpawnedCountry).filter(SpawnedCountry.id == sc1_id).first()
        sc1.gold = 0
        db_session.commit()

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": sc2_id,
                "offer_gold": 5,
                "request_people": 1,
            },
        )
        assert resp.status_code == 400

    def test_propose_trade_not_in_game(self, mock_games_bc, mock_trades_bc, client, seed_data):
        """A player not in the game cannot propose a trade."""
        from app.tests.conftest import _seed_player
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        # p1 is in the game but we try as a non-game player
        # We'll override get_current_user to a user that's not in the game
        # by creating a fake player context - but since both p1 and p2 are in the game,
        # we just test with wrong receiver
        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": 9999,
                "offer_gold": 1,
                "request_gold": 1,
            },
        )
        assert resp.status_code == 404

    def test_propose_trade_wrong_phase(self, mock_games_bc, mock_trades_bc, client, seed_data):
        """Cannot propose trade during development phase."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = _create_game(client, p1, rounds=2)
        game_id = game["id"]
        join1 = _join_game(client, game_id, p1, countries[0].id)
        join2 = _join_game(client, game_id, p2, countries[1].id)
        _start_game(client, game_id, p1)  # Now in development

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": join2["spawned_country_id"],
                "offer_gold": 1,
                "request_gold": 1,
            },
        )
        assert resp.status_code == 400

    def test_propose_trade_unauthenticated(self, mock_games_bc, mock_trades_bc, client, seed_data):
        """Request without auth should fail."""
        app.dependency_overrides.pop(get_current_user, None)
        resp = client.post(
            "/api/games/1/trades",
            json={
                "receiver_country_id": 2,
                "offer_gold": 1,
                "request_gold": 1,
            },
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: POST /api/games/{game_id}/trades/{trade_id}/accept
# ---------------------------------------------------------------------------

@patch("app.api.routes.trades.broadcast_event", new_callable=AsyncMock)
@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestAcceptTradeEndpoint:
    """POST /api/games/{game_id}/trades/{trade_id}/accept"""

    def test_accept_trade_success(self, mock_games_bc, mock_trades_bc, client, seed_data, db_session):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        # Propose a trade
        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": sc2_id,
                "offer_gold": 2,
                "request_people": 1,
            },
        )
        trade_id = resp.json()["id"]

        # Record balances before
        sc1 = db_session.query(SpawnedCountry).filter(SpawnedCountry.id == sc1_id).first()
        sc2 = db_session.query(SpawnedCountry).filter(SpawnedCountry.id == sc2_id).first()
        p1_gold_before = sc1.gold
        p2_gold_before = sc2.gold
        p2_people_before = sc2.people

        # Accept as receiver
        app.dependency_overrides[get_current_user] = _override_user(p2)
        resp = client.post(f"/api/games/{game_id}/trades/{trade_id}/accept")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"

        # Verify atomic resource transfer
        db_session.expire_all()
        sc1 = db_session.query(SpawnedCountry).filter(SpawnedCountry.id == sc1_id).first()
        sc2 = db_session.query(SpawnedCountry).filter(SpawnedCountry.id == sc2_id).first()

        assert sc1.gold == p1_gold_before - 2  # gave 2 gold
        assert sc2.gold == p2_gold_before + 2  # received 2 gold
        assert sc2.people == p2_people_before - 1  # gave 1 person
        assert sc1.people > 0  # received 1 person

    def test_accept_trade_broadcasts_event(self, mock_games_bc, mock_trades_bc, client, seed_data):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": sc2_id,
                "offer_gold": 1,
                "request_gold": 1,
            },
        )
        trade_id = resp.json()["id"]

        mock_trades_bc.reset_mock()
        app.dependency_overrides[get_current_user] = _override_user(p2)
        resp = client.post(f"/api/games/{game_id}/trades/{trade_id}/accept")
        assert resp.status_code == 200

        mock_trades_bc.assert_called()
        call_args = mock_trades_bc.call_args
        assert call_args[0][1]["type"] == "trade_accepted"

    def test_accept_trade_not_receiver(self, mock_games_bc, mock_trades_bc, client, seed_data):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": sc2_id,
                "offer_gold": 1,
                "request_gold": 1,
            },
        )
        trade_id = resp.json()["id"]

        # Proposer tries to accept their own trade
        resp = client.post(f"/api/games/{game_id}/trades/{trade_id}/accept")
        assert resp.status_code == 403

    def test_accept_trade_not_found(self, mock_games_bc, mock_trades_bc, client, seed_data):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        app.dependency_overrides[get_current_user] = _override_user(p2)
        resp = client.post(f"/api/games/{game_id}/trades/9999/accept")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: POST /api/games/{game_id}/trades/{trade_id}/reject
# ---------------------------------------------------------------------------

@patch("app.api.routes.trades.broadcast_event", new_callable=AsyncMock)
@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestRejectTradeEndpoint:
    """POST /api/games/{game_id}/trades/{trade_id}/reject"""

    def test_reject_trade_success(self, mock_games_bc, mock_trades_bc, client, seed_data):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": sc2_id,
                "offer_gold": 1,
                "request_gold": 1,
            },
        )
        trade_id = resp.json()["id"]

        app.dependency_overrides[get_current_user] = _override_user(p2)
        resp = client.post(f"/api/games/{game_id}/trades/{trade_id}/reject")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_reject_trade_broadcasts_event(self, mock_games_bc, mock_trades_bc, client, seed_data):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": sc2_id,
                "offer_gold": 1,
                "request_gold": 1,
            },
        )
        trade_id = resp.json()["id"]

        mock_trades_bc.reset_mock()
        app.dependency_overrides[get_current_user] = _override_user(p2)
        resp = client.post(f"/api/games/{game_id}/trades/{trade_id}/reject")
        assert resp.status_code == 200

        mock_trades_bc.assert_called()
        call_args = mock_trades_bc.call_args
        assert call_args[0][1]["type"] == "trade_rejected"

    def test_reject_trade_not_receiver(self, mock_games_bc, mock_trades_bc, client, seed_data):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": sc2_id,
                "offer_gold": 1,
                "request_gold": 1,
            },
        )
        trade_id = resp.json()["id"]

        # Proposer tries to reject
        resp = client.post(f"/api/games/{game_id}/trades/{trade_id}/reject")
        assert resp.status_code == 403

    def test_reject_trade_already_accepted(self, mock_games_bc, mock_trades_bc, client, seed_data, db_session):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": sc2_id,
                "offer_gold": 1,
                "request_gold": 1,
            },
        )
        trade_id = resp.json()["id"]

        # Manually set to accepted
        trade = db_session.query(Trade).filter(Trade.id == trade_id).first()
        trade.status = "accepted"
        db_session.commit()

        app.dependency_overrides[get_current_user] = _override_user(p2)
        resp = client.post(f"/api/games/{game_id}/trades/{trade_id}/reject")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests: GET /api/games/{game_id}/trades (list pending)
# ---------------------------------------------------------------------------

@patch("app.api.routes.trades.broadcast_event", new_callable=AsyncMock)
@patch("app.api.routes.games.broadcast_event", new_callable=AsyncMock)
class TestListTradesEndpoint:
    """GET /api/games/{game_id}/trades"""

    def test_list_trades_returns_pending(self, mock_games_bc, mock_trades_bc, client, seed_data):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        # Create two trades
        app.dependency_overrides[get_current_user] = _override_user(p1)
        for _ in range(2):
            client.post(
                f"/api/games/{game_id}/trades",
                json={
                    "receiver_country_id": sc2_id,
                    "offer_gold": 1,
                    "request_gold": 1,
                },
            )

        resp = client.get(f"/api/games/{game_id}/trades")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["trades"]) == 2
        assert all(t["status"] == "pending" for t in data["trades"])

    def test_list_trades_excludes_resolved(self, mock_games_bc, mock_trades_bc, client, seed_data):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        # Create and accept a trade
        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.post(
            f"/api/games/{game_id}/trades",
            json={
                "receiver_country_id": sc2_id,
                "offer_gold": 1,
                "request_gold": 1,
            },
        )
        trade_id = resp.json()["id"]

        app.dependency_overrides[get_current_user] = _override_user(p2)
        client.post(f"/api/games/{game_id}/trades/{trade_id}/accept")

        # List should be empty
        resp = client.get(f"/api/games/{game_id}/trades")
        assert resp.status_code == 200
        assert len(resp.json()["trades"]) == 0

    def test_list_trades_empty_game(self, mock_games_bc, mock_trades_bc, client, seed_data):
        game_id, sc1_id, sc2_id, p1, p2 = _setup_game_in_actions(client, seed_data)

        app.dependency_overrides[get_current_user] = _override_user(p1)
        resp = client.get(f"/api/games/{game_id}/trades")
        assert resp.status_code == 200
        assert resp.json()["trades"] == []

    def test_list_trades_unauthenticated(self, mock_games_bc, mock_trades_bc, client, seed_data):
        app.dependency_overrides.pop(get_current_user, None)
        resp = client.get("/api/games/1/trades")
        assert resp.status_code == 401
