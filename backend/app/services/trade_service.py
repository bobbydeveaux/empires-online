"""Trading service for Empires Online.

Handles trade proposal, acceptance, and rejection with validation
and atomic resource transfers.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.models import Trade, SpawnedCountry, Game


# Valid game phases where trading is allowed
TRADE_PHASES = {"actions"}


class TradeService:

    @staticmethod
    def propose_trade(
        db: Session,
        game_id: int,
        proposer_country_id: int,
        receiver_country_id: int,
        offer: Dict[str, int],
        request: Dict[str, int],
    ) -> Trade:
        """Create a new trade proposal after validating all constraints."""

        # Cannot trade with yourself
        if proposer_country_id == receiver_country_id:
            raise HTTPException(status_code=400, detail="Cannot trade with yourself")

        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        if game.phase not in TRADE_PHASES:
            raise HTTPException(
                status_code=400,
                detail=f"Trading is not allowed in {game.phase} phase",
            )

        # Validate proposer exists in this game
        proposer = (
            db.query(SpawnedCountry)
            .filter(
                SpawnedCountry.id == proposer_country_id,
                SpawnedCountry.game_id == game_id,
            )
            .first()
        )
        if not proposer:
            raise HTTPException(
                status_code=404, detail="Proposer country not found in this game"
            )

        # Validate receiver exists in this game
        receiver = (
            db.query(SpawnedCountry)
            .filter(
                SpawnedCountry.id == receiver_country_id,
                SpawnedCountry.game_id == game_id,
            )
            .first()
        )
        if not receiver:
            raise HTTPException(
                status_code=404, detail="Receiver country not found in this game"
            )

        # Validate proposer has enough resources to offer
        offer_gold = offer.get("gold", 0)
        offer_people = offer.get("people", 0)
        offer_territory = offer.get("territory", 0)

        if offer_gold < 0 or offer_people < 0 or offer_territory < 0:
            raise HTTPException(
                status_code=400, detail="Offer amounts cannot be negative"
            )

        if (
            offer_gold == 0
            and offer_people == 0
            and offer_territory == 0
            and request.get("gold", 0) == 0
            and request.get("people", 0) == 0
            and request.get("territory", 0) == 0
        ):
            raise HTTPException(
                status_code=400, detail="Trade must involve at least one resource"
            )

        if offer_gold > proposer.gold:
            raise HTTPException(
                status_code=400, detail="Insufficient gold to offer"
            )
        if offer_people > proposer.people:
            raise HTTPException(
                status_code=400, detail="Insufficient people to offer"
            )
        if offer_territory > proposer.territories:
            raise HTTPException(
                status_code=400, detail="Insufficient territories to offer"
            )

        request_gold = request.get("gold", 0)
        request_people = request.get("people", 0)
        request_territory = request.get("territory", 0)

        if request_gold < 0 or request_people < 0 or request_territory < 0:
            raise HTTPException(
                status_code=400, detail="Request amounts cannot be negative"
            )

        trade = Trade(
            game_id=game_id,
            proposer_country_id=proposer_country_id,
            receiver_country_id=receiver_country_id,
            offer_gold=offer_gold,
            offer_people=offer_people,
            offer_territory=offer_territory,
            request_gold=request_gold,
            request_people=request_people,
            request_territory=request_territory,
            status="pending",
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        return trade

    @staticmethod
    def accept_trade(db: Session, trade_id: int, current_user_country_id: int) -> Trade:
        """Accept a pending trade and atomically transfer resources."""

        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")

        if trade.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Trade is already {trade.status}",
            )

        # Only the receiver can accept
        if trade.receiver_country_id != current_user_country_id:
            raise HTTPException(
                status_code=403, detail="Only the receiver can accept this trade"
            )

        # Verify game is still in a valid phase
        game = db.query(Game).filter(Game.id == trade.game_id).first()
        if game.phase not in TRADE_PHASES:
            raise HTTPException(
                status_code=400,
                detail=f"Trading is not allowed in {game.phase} phase",
            )

        proposer = (
            db.query(SpawnedCountry)
            .filter(SpawnedCountry.id == trade.proposer_country_id)
            .first()
        )
        receiver = (
            db.query(SpawnedCountry)
            .filter(SpawnedCountry.id == trade.receiver_country_id)
            .first()
        )

        # Validate proposer still has enough resources
        if proposer.gold < trade.offer_gold:
            raise HTTPException(
                status_code=400,
                detail="Proposer no longer has enough gold",
            )
        if proposer.people < trade.offer_people:
            raise HTTPException(
                status_code=400,
                detail="Proposer no longer has enough people",
            )
        if proposer.territories < trade.offer_territory:
            raise HTTPException(
                status_code=400,
                detail="Proposer no longer has enough territories",
            )

        # Validate receiver has enough resources to fulfill the request
        if receiver.gold < trade.request_gold:
            raise HTTPException(
                status_code=400,
                detail="You do not have enough gold to fulfill this trade",
            )
        if receiver.people < trade.request_people:
            raise HTTPException(
                status_code=400,
                detail="You do not have enough people to fulfill this trade",
            )
        if receiver.territories < trade.request_territory:
            raise HTTPException(
                status_code=400,
                detail="You do not have enough territories to fulfill this trade",
            )

        # Atomic resource transfer
        # Proposer gives offer, receives request
        proposer.gold -= trade.offer_gold
        proposer.people -= trade.offer_people
        proposer.territories -= trade.offer_territory
        proposer.gold += trade.request_gold
        proposer.people += trade.request_people
        proposer.territories += trade.request_territory

        # Receiver gives request, receives offer
        receiver.gold -= trade.request_gold
        receiver.people -= trade.request_people
        receiver.territories -= trade.request_territory
        receiver.gold += trade.offer_gold
        receiver.people += trade.offer_people
        receiver.territories += trade.offer_territory

        trade.status = "accepted"
        db.commit()
        db.refresh(trade)
        return trade

    @staticmethod
    def reject_trade(db: Session, trade_id: int, current_user_country_id: int) -> Trade:
        """Reject a pending trade. Only the receiver can reject."""

        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")

        if trade.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Trade is already {trade.status}",
            )

        # Only the receiver can reject
        if trade.receiver_country_id != current_user_country_id:
            raise HTTPException(
                status_code=403, detail="Only the receiver can reject this trade"
            )

        trade.status = "rejected"
        db.commit()
        db.refresh(trade)
        return trade

    @staticmethod
    def list_pending_trades(db: Session, game_id: int) -> List[Trade]:
        """List all pending trades for a game."""
        return (
            db.query(Trade)
            .filter(Trade.game_id == game_id, Trade.status == "pending")
            .all()
        )
