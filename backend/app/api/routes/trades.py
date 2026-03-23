"""REST endpoints for the trading system."""

from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Player, SpawnedCountry, Trade
from app.schemas.schemas import TradePropose, TradeResponse, TradeList
from app.api.routes.auth import get_current_user
from app.services.trade_service import TradeService
from app.services.game_broadcast import (
    broadcast_event,
    trade_proposed_message,
    trade_resolved_message,
)

router = APIRouter()


def _get_player_country(db: Session, game_id: int, player_id: int) -> SpawnedCountry:
    """Find the SpawnedCountry for a player in a game."""
    sc = (
        db.query(SpawnedCountry)
        .filter(
            SpawnedCountry.game_id == game_id,
            SpawnedCountry.player_id == player_id,
        )
        .first()
    )
    if not sc:
        raise HTTPException(
            status_code=404, detail="You are not a player in this game"
        )
    return sc


@router.post("/{game_id}/trades", response_model=TradeResponse)
def propose_trade(
    game_id: int,
    trade_data: TradePropose,
    background_tasks: BackgroundTasks,
    current_user: Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Propose a new trade."""
    proposer = _get_player_country(db, game_id, current_user.id)

    trade = TradeService.propose_trade(
        db=db,
        game_id=game_id,
        proposer_country_id=proposer.id,
        receiver_country_id=trade_data.receiver_country_id,
        offer={
            "gold": trade_data.offer_gold,
            "people": trade_data.offer_people,
            "territory": trade_data.offer_territory,
        },
        request={
            "gold": trade_data.request_gold,
            "people": trade_data.request_people,
            "territory": trade_data.request_territory,
        },
    )

    trade_dict = {
        "id": trade.id,
        "game_id": trade.game_id,
        "proposer_country_id": trade.proposer_country_id,
        "receiver_country_id": trade.receiver_country_id,
        "offer_gold": trade.offer_gold,
        "offer_people": trade.offer_people,
        "offer_territory": trade.offer_territory,
        "request_gold": trade.request_gold,
        "request_people": trade.request_people,
        "request_territory": trade.request_territory,
        "status": trade.status,
    }
    background_tasks.add_task(
        broadcast_event,
        game_id,
        trade_proposed_message(game_id=game_id, trade=trade_dict),
    )

    return trade


@router.post("/{game_id}/trades/{trade_id}/accept", response_model=TradeResponse)
def accept_trade(
    game_id: int,
    trade_id: int,
    background_tasks: BackgroundTasks,
    current_user: Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Accept a pending trade."""
    receiver = _get_player_country(db, game_id, current_user.id)

    trade = TradeService.accept_trade(
        db=db,
        trade_id=trade_id,
        current_user_country_id=receiver.id,
    )

    trade_dict = {
        "id": trade.id,
        "game_id": trade.game_id,
        "proposer_country_id": trade.proposer_country_id,
        "receiver_country_id": trade.receiver_country_id,
        "offer_gold": trade.offer_gold,
        "offer_people": trade.offer_people,
        "offer_territory": trade.offer_territory,
        "request_gold": trade.request_gold,
        "request_people": trade.request_people,
        "request_territory": trade.request_territory,
        "status": trade.status,
    }
    background_tasks.add_task(
        broadcast_event,
        game_id,
        trade_resolved_message(game_id=game_id, trade=trade_dict, resolution="accepted"),
    )

    return trade


@router.post("/{game_id}/trades/{trade_id}/reject", response_model=TradeResponse)
def reject_trade(
    game_id: int,
    trade_id: int,
    background_tasks: BackgroundTasks,
    current_user: Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject a pending trade."""
    receiver = _get_player_country(db, game_id, current_user.id)

    trade = TradeService.reject_trade(
        db=db,
        trade_id=trade_id,
        current_user_country_id=receiver.id,
    )

    trade_dict = {
        "id": trade.id,
        "game_id": trade.game_id,
        "proposer_country_id": trade.proposer_country_id,
        "receiver_country_id": trade.receiver_country_id,
        "offer_gold": trade.offer_gold,
        "offer_people": trade.offer_people,
        "offer_territory": trade.offer_territory,
        "request_gold": trade.request_gold,
        "request_people": trade.request_people,
        "request_territory": trade.request_territory,
        "status": trade.status,
    }
    background_tasks.add_task(
        broadcast_event,
        game_id,
        trade_resolved_message(game_id=game_id, trade=trade_dict, resolution="rejected"),
    )

    return trade


@router.get("/{game_id}/trades", response_model=TradeList)
def list_trades(
    game_id: int,
    current_user: Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List pending trades for a game."""
    trades = TradeService.list_pending_trades(db=db, game_id=game_id)
    return TradeList(trades=trades)
