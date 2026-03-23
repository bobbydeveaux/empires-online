"""Unit tests for the TradeService.

Covers propose, accept, reject flows and validation edge cases including
insufficient resources, self-trade, invalid status transitions, and
wrong game phase.
"""

import pytest
from fastapi import HTTPException

from app.models.models import Trade, SpawnedCountry, Game, Player, Country
from app.services.trade_service import TradeService


class TestTradeServicePropose:
    """Tests for TradeService.propose_trade."""

    def test_propose_trade_happy_path(self, db_session, seed_data):
        """Proposing a valid trade creates a pending Trade row."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=6,
        )
        sc2 = SpawnedCountry(
            country_id=countries[1].id, game_id=game.id, player_id=p2.id,
            gold=8, bonds=0, territories=6, goods=5, people=5,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()
        db_session.refresh(sc1)
        db_session.refresh(sc2)

        trade = TradeService.propose_trade(
            db=db_session,
            game_id=game.id,
            proposer_country_id=sc1.id,
            receiver_country_id=sc2.id,
            offer={"gold": 3, "people": 0, "territory": 0},
            request={"gold": 0, "people": 2, "territory": 0},
        )

        assert trade.id is not None
        assert trade.status == "pending"
        assert trade.offer_gold == 3
        assert trade.request_people == 2
        assert trade.proposer_country_id == sc1.id
        assert trade.receiver_country_id == sc2.id

    def test_propose_trade_self_trade_rejected(self, db_session, seed_data):
        """Cannot propose a trade with yourself."""
        p1 = seed_data["player1"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=6,
        )
        db_session.add(sc1)
        db_session.commit()
        db_session.refresh(sc1)

        with pytest.raises(HTTPException) as exc_info:
            TradeService.propose_trade(
                db=db_session,
                game_id=game.id,
                proposer_country_id=sc1.id,
                receiver_country_id=sc1.id,
                offer={"gold": 1},
                request={"gold": 1},
            )
        assert exc_info.value.status_code == 400
        assert "yourself" in exc_info.value.detail.lower()

    def test_propose_trade_wrong_phase(self, db_session, seed_data):
        """Cannot trade during development phase."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="development", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=6,
        )
        sc2 = SpawnedCountry(
            country_id=countries[1].id, game_id=game.id, player_id=p2.id,
            gold=8, bonds=0, territories=6, goods=5, people=5,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()
        db_session.refresh(sc1)
        db_session.refresh(sc2)

        with pytest.raises(HTTPException) as exc_info:
            TradeService.propose_trade(
                db=db_session,
                game_id=game.id,
                proposer_country_id=sc1.id,
                receiver_country_id=sc2.id,
                offer={"gold": 1},
                request={"gold": 1},
            )
        assert exc_info.value.status_code == 400
        assert "phase" in exc_info.value.detail.lower()

    def test_propose_trade_insufficient_gold(self, db_session, seed_data):
        """Cannot offer more gold than you have."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=2, bonds=0, territories=5, goods=4, people=6,
        )
        sc2 = SpawnedCountry(
            country_id=countries[1].id, game_id=game.id, player_id=p2.id,
            gold=8, bonds=0, territories=6, goods=5, people=5,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()
        db_session.refresh(sc1)
        db_session.refresh(sc2)

        with pytest.raises(HTTPException) as exc_info:
            TradeService.propose_trade(
                db=db_session,
                game_id=game.id,
                proposer_country_id=sc1.id,
                receiver_country_id=sc2.id,
                offer={"gold": 5},
                request={"gold": 1},
            )
        assert exc_info.value.status_code == 400
        assert "gold" in exc_info.value.detail.lower()

    def test_propose_trade_insufficient_people(self, db_session, seed_data):
        """Cannot offer more people than you have."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=2,
        )
        sc2 = SpawnedCountry(
            country_id=countries[1].id, game_id=game.id, player_id=p2.id,
            gold=8, bonds=0, territories=6, goods=5, people=5,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()
        db_session.refresh(sc1)
        db_session.refresh(sc2)

        with pytest.raises(HTTPException) as exc_info:
            TradeService.propose_trade(
                db=db_session,
                game_id=game.id,
                proposer_country_id=sc1.id,
                receiver_country_id=sc2.id,
                offer={"people": 5},
                request={"gold": 1},
            )
        assert exc_info.value.status_code == 400
        assert "people" in exc_info.value.detail.lower()

    def test_propose_trade_insufficient_territory(self, db_session, seed_data):
        """Cannot offer more territories than you have."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=1, goods=4, people=6,
        )
        sc2 = SpawnedCountry(
            country_id=countries[1].id, game_id=game.id, player_id=p2.id,
            gold=8, bonds=0, territories=6, goods=5, people=5,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()
        db_session.refresh(sc1)
        db_session.refresh(sc2)

        with pytest.raises(HTTPException) as exc_info:
            TradeService.propose_trade(
                db=db_session,
                game_id=game.id,
                proposer_country_id=sc1.id,
                receiver_country_id=sc2.id,
                offer={"territory": 5},
                request={"gold": 1},
            )
        assert exc_info.value.status_code == 400
        assert "territor" in exc_info.value.detail.lower()

    def test_propose_trade_game_not_found(self, db_session, seed_data):
        """Cannot propose a trade for a non-existent game."""
        with pytest.raises(HTTPException) as exc_info:
            TradeService.propose_trade(
                db=db_session,
                game_id=9999,
                proposer_country_id=1,
                receiver_country_id=2,
                offer={"gold": 1},
                request={"gold": 1},
            )
        assert exc_info.value.status_code == 404

    def test_propose_trade_receiver_not_in_game(self, db_session, seed_data):
        """Cannot propose a trade to a country not in the game."""
        p1 = seed_data["player1"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=6,
        )
        db_session.add(sc1)
        db_session.commit()
        db_session.refresh(sc1)

        with pytest.raises(HTTPException) as exc_info:
            TradeService.propose_trade(
                db=db_session,
                game_id=game.id,
                proposer_country_id=sc1.id,
                receiver_country_id=9999,
                offer={"gold": 1},
                request={"gold": 1},
            )
        assert exc_info.value.status_code == 404

    def test_propose_trade_empty_trade_rejected(self, db_session, seed_data):
        """Cannot propose a trade with all zeros."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=6,
        )
        sc2 = SpawnedCountry(
            country_id=countries[1].id, game_id=game.id, player_id=p2.id,
            gold=8, bonds=0, territories=6, goods=5, people=5,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()
        db_session.refresh(sc1)
        db_session.refresh(sc2)

        with pytest.raises(HTTPException) as exc_info:
            TradeService.propose_trade(
                db=db_session,
                game_id=game.id,
                proposer_country_id=sc1.id,
                receiver_country_id=sc2.id,
                offer={"gold": 0, "people": 0, "territory": 0},
                request={"gold": 0, "people": 0, "territory": 0},
            )
        assert exc_info.value.status_code == 400
        assert "at least one" in exc_info.value.detail.lower()

    def test_propose_trade_negative_amounts_rejected(self, db_session, seed_data):
        """Cannot offer negative resource amounts."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=6,
        )
        sc2 = SpawnedCountry(
            country_id=countries[1].id, game_id=game.id, player_id=p2.id,
            gold=8, bonds=0, territories=6, goods=5, people=5,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()
        db_session.refresh(sc1)
        db_session.refresh(sc2)

        with pytest.raises(HTTPException) as exc_info:
            TradeService.propose_trade(
                db=db_session,
                game_id=game.id,
                proposer_country_id=sc1.id,
                receiver_country_id=sc2.id,
                offer={"gold": -1},
                request={"gold": 1},
            )
        assert exc_info.value.status_code == 400
        assert "negative" in exc_info.value.detail.lower()


class TestTradeServiceAccept:
    """Tests for TradeService.accept_trade."""

    def _create_pending_trade(self, db_session, seed_data):
        """Helper: create a game with 2 players in actions phase and a pending trade."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=6,
        )
        sc2 = SpawnedCountry(
            country_id=countries[1].id, game_id=game.id, player_id=p2.id,
            gold=8, bonds=0, territories=6, goods=5, people=5,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()
        db_session.refresh(sc1)
        db_session.refresh(sc2)

        trade = Trade(
            game_id=game.id,
            proposer_country_id=sc1.id,
            receiver_country_id=sc2.id,
            offer_gold=3,
            offer_people=0,
            offer_territory=1,
            request_gold=0,
            request_people=2,
            request_territory=0,
            status="pending",
        )
        db_session.add(trade)
        db_session.commit()
        db_session.refresh(trade)

        return game, sc1, sc2, trade

    def test_accept_trade_happy_path(self, db_session, seed_data):
        """Accepting a trade atomically transfers resources."""
        game, sc1, sc2, trade = self._create_pending_trade(db_session, seed_data)

        # Before: sc1 has gold=10, territories=5, people=6
        #         sc2 has gold=8, territories=6, people=5
        # Trade: sc1 offers gold=3, territory=1; requests people=2

        result = TradeService.accept_trade(
            db=db_session,
            trade_id=trade.id,
            current_user_country_id=sc2.id,
        )

        assert result.status == "accepted"

        db_session.refresh(sc1)
        db_session.refresh(sc2)

        # sc1: lost gold=3, territory=1; gained people=2
        assert sc1.gold == 10 - 3
        assert sc1.territories == 5 - 1
        assert sc1.people == 6 + 2

        # sc2: gained gold=3, territory=1; lost people=2
        assert sc2.gold == 8 + 3
        assert sc2.territories == 6 + 1
        assert sc2.people == 5 - 2

    def test_accept_trade_not_receiver_forbidden(self, db_session, seed_data):
        """Only the receiver can accept a trade."""
        game, sc1, sc2, trade = self._create_pending_trade(db_session, seed_data)

        with pytest.raises(HTTPException) as exc_info:
            TradeService.accept_trade(
                db=db_session,
                trade_id=trade.id,
                current_user_country_id=sc1.id,  # proposer, not receiver
            )
        assert exc_info.value.status_code == 403

    def test_accept_trade_already_accepted(self, db_session, seed_data):
        """Cannot accept an already accepted trade."""
        game, sc1, sc2, trade = self._create_pending_trade(db_session, seed_data)
        trade.status = "accepted"
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            TradeService.accept_trade(
                db=db_session,
                trade_id=trade.id,
                current_user_country_id=sc2.id,
            )
        assert exc_info.value.status_code == 400
        assert "already" in exc_info.value.detail.lower()

    def test_accept_trade_already_rejected(self, db_session, seed_data):
        """Cannot accept an already rejected trade."""
        game, sc1, sc2, trade = self._create_pending_trade(db_session, seed_data)
        trade.status = "rejected"
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            TradeService.accept_trade(
                db=db_session,
                trade_id=trade.id,
                current_user_country_id=sc2.id,
            )
        assert exc_info.value.status_code == 400

    def test_accept_trade_not_found(self, db_session, seed_data):
        """Cannot accept a non-existent trade."""
        with pytest.raises(HTTPException) as exc_info:
            TradeService.accept_trade(
                db=db_session,
                trade_id=9999,
                current_user_country_id=1,
            )
        assert exc_info.value.status_code == 404

    def test_accept_trade_proposer_lost_resources(self, db_session, seed_data):
        """If proposer spent gold since proposing, accept fails."""
        game, sc1, sc2, trade = self._create_pending_trade(db_session, seed_data)

        # Drain proposer's gold so they can't fulfill the offer
        sc1.gold = 1
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            TradeService.accept_trade(
                db=db_session,
                trade_id=trade.id,
                current_user_country_id=sc2.id,
            )
        assert exc_info.value.status_code == 400
        assert "proposer" in exc_info.value.detail.lower()

    def test_accept_trade_receiver_insufficient_resources(self, db_session, seed_data):
        """If receiver doesn't have enough resources to fulfill request, accept fails."""
        game, sc1, sc2, trade = self._create_pending_trade(db_session, seed_data)

        # The trade requests people=2 from receiver; drain receiver's people
        sc2.people = 0
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            TradeService.accept_trade(
                db=db_session,
                trade_id=trade.id,
                current_user_country_id=sc2.id,
            )
        assert exc_info.value.status_code == 400
        assert "people" in exc_info.value.detail.lower()

    def test_accept_trade_wrong_phase(self, db_session, seed_data):
        """Cannot accept a trade if game phase has changed."""
        game, sc1, sc2, trade = self._create_pending_trade(db_session, seed_data)

        game.phase = "development"
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            TradeService.accept_trade(
                db=db_session,
                trade_id=trade.id,
                current_user_country_id=sc2.id,
            )
        assert exc_info.value.status_code == 400
        assert "phase" in exc_info.value.detail.lower()


class TestTradeServiceReject:
    """Tests for TradeService.reject_trade."""

    def _create_pending_trade(self, db_session, seed_data):
        """Helper: same as TestTradeServiceAccept."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=6,
        )
        sc2 = SpawnedCountry(
            country_id=countries[1].id, game_id=game.id, player_id=p2.id,
            gold=8, bonds=0, territories=6, goods=5, people=5,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()
        db_session.refresh(sc1)
        db_session.refresh(sc2)

        trade = Trade(
            game_id=game.id,
            proposer_country_id=sc1.id,
            receiver_country_id=sc2.id,
            offer_gold=3, offer_people=0, offer_territory=0,
            request_gold=0, request_people=2, request_territory=0,
            status="pending",
        )
        db_session.add(trade)
        db_session.commit()
        db_session.refresh(trade)

        return game, sc1, sc2, trade

    def test_reject_trade_happy_path(self, db_session, seed_data):
        """Rejecting a trade sets status to rejected with no resource changes."""
        game, sc1, sc2, trade = self._create_pending_trade(db_session, seed_data)

        result = TradeService.reject_trade(
            db=db_session,
            trade_id=trade.id,
            current_user_country_id=sc2.id,
        )

        assert result.status == "rejected"

        # No resource changes
        db_session.refresh(sc1)
        db_session.refresh(sc2)
        assert sc1.gold == 10
        assert sc2.gold == 8

    def test_reject_trade_not_receiver_forbidden(self, db_session, seed_data):
        """Only the receiver can reject a trade."""
        game, sc1, sc2, trade = self._create_pending_trade(db_session, seed_data)

        with pytest.raises(HTTPException) as exc_info:
            TradeService.reject_trade(
                db=db_session,
                trade_id=trade.id,
                current_user_country_id=sc1.id,  # proposer
            )
        assert exc_info.value.status_code == 403

    def test_reject_trade_already_accepted(self, db_session, seed_data):
        """Cannot reject an already accepted trade."""
        game, sc1, sc2, trade = self._create_pending_trade(db_session, seed_data)
        trade.status = "accepted"
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            TradeService.reject_trade(
                db=db_session,
                trade_id=trade.id,
                current_user_country_id=sc2.id,
            )
        assert exc_info.value.status_code == 400

    def test_reject_trade_not_found(self, db_session, seed_data):
        """Cannot reject a non-existent trade."""
        with pytest.raises(HTTPException) as exc_info:
            TradeService.reject_trade(
                db=db_session,
                trade_id=9999,
                current_user_country_id=1,
            )
        assert exc_info.value.status_code == 404


class TestTradeServiceListPending:
    """Tests for TradeService.list_pending_trades."""

    def test_list_pending_trades(self, db_session, seed_data):
        """Returns only pending trades for the given game."""
        p1, p2 = seed_data["player1"], seed_data["player2"]
        countries = seed_data["countries"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        sc1 = SpawnedCountry(
            country_id=countries[0].id, game_id=game.id, player_id=p1.id,
            gold=10, bonds=0, territories=5, goods=4, people=6,
        )
        sc2 = SpawnedCountry(
            country_id=countries[1].id, game_id=game.id, player_id=p2.id,
            gold=8, bonds=0, territories=6, goods=5, people=5,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()
        db_session.refresh(sc1)
        db_session.refresh(sc2)

        # Create 2 pending and 1 accepted trade
        for status in ["pending", "pending", "accepted"]:
            t = Trade(
                game_id=game.id,
                proposer_country_id=sc1.id,
                receiver_country_id=sc2.id,
                offer_gold=1, offer_people=0, offer_territory=0,
                request_gold=0, request_people=1, request_territory=0,
                status=status,
            )
            db_session.add(t)
        db_session.commit()

        pending = TradeService.list_pending_trades(db=db_session, game_id=game.id)
        assert len(pending) == 2
        assert all(t.status == "pending" for t in pending)

    def test_list_pending_trades_empty(self, db_session, seed_data):
        """Returns empty list when no pending trades exist."""
        p1 = seed_data["player1"]

        game = Game(rounds=5, rounds_remaining=5, phase="actions", creator_id=p1.id)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        pending = TradeService.list_pending_trades(db=db_session, game_id=game.id)
        assert pending == []
