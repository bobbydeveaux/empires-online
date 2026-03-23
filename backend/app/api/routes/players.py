from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.core.database import get_db
from app.models.models import Player, Country, GameResult, SpawnedCountry, Game
from app.schemas.schemas import (
    Player as PlayerSchema,
    Country as CountrySchema,
    PlayerStats,
    PlayerGameHistory,
    GlobalLeaderboardEntry,
)
from app.api.routes.auth import get_current_user

router = APIRouter()


@router.get("/me", response_model=PlayerSchema)
def get_current_player(current_user: Player = Depends(get_current_user)):
    """Get current player information."""
    return current_user


@router.get("/countries", response_model=List[CountrySchema])
def list_countries(db: Session = Depends(get_db)):
    """List all available countries."""
    return db.query(Country).all()


@router.get("/", response_model=List[PlayerSchema])
def list_players(db: Session = Depends(get_db)):
    """List all players (for leaderboards, etc.)."""
    return db.query(Player).all()


@router.get("/{player_id}/history", response_model=List[PlayerGameHistory])
def get_player_history(player_id: int, db: Session = Depends(get_db)):
    """Get a player's game history with placement and stats."""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Find all completed games this player participated in
    results = (
        db.query(GameResult)
        .join(Game, Game.id == GameResult.game_id)
        .join(SpawnedCountry, SpawnedCountry.game_id == Game.id)
        .filter(SpawnedCountry.player_id == player_id)
        .all()
    )

    history = []
    for result in results:
        rankings = json.loads(result.final_rankings) if result.final_rankings else []
        player_ranking = next(
            (r for r in rankings if r["player_id"] == player_id), None
        )
        if player_ranking is None:
            continue

        history.append(
            PlayerGameHistory(
                game_id=result.game_id,
                rounds=result.duration_rounds,
                finished_at=result.finished_at,
                rank=player_ranking["rank"],
                score=player_ranking["score"],
                country_name=player_ranking["country_name"],
                won=result.winner_player_id == player_id,
            )
        )

    # Sort by most recent first
    history.sort(key=lambda h: h.finished_at or "", reverse=True)
    return history


@router.get("/{player_id}/stats", response_model=PlayerStats)
def get_player_stats(player_id: int, db: Session = Depends(get_db)):
    """Get aggregated stats for a player."""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    total_games, wins = _compute_player_stats(db, player_id)
    losses = total_games - wins
    win_rate = (wins / total_games * 100) if total_games > 0 else 0.0

    return PlayerStats(
        id=player.id,
        username=player.username,
        email=player.email,
        total_games=total_games,
        wins=wins,
        losses=losses,
        win_rate=round(win_rate, 1),
    )


@router.get("/leaderboard/global", response_model=List[GlobalLeaderboardEntry])
def get_global_leaderboard(db: Session = Depends(get_db)):
    """Get the global leaderboard with all-time win counts, win rates, and average placement."""
    # Find all players who have participated in completed games
    player_ids = (
        db.query(SpawnedCountry.player_id)
        .join(Game, Game.id == SpawnedCountry.game_id)
        .filter(Game.phase == "completed")
        .distinct()
        .all()
    )

    entries = []
    for (pid,) in player_ids:
        player = db.query(Player).filter(Player.id == pid).first()
        if not player:
            continue

        total_games, wins = _compute_player_stats(db, pid)
        if total_games == 0:
            continue

        losses = total_games - wins
        win_rate = (wins / total_games * 100) if total_games > 0 else 0.0

        # Calculate average placement from final_rankings
        avg_placement = _compute_avg_placement(db, pid)

        entries.append(
            GlobalLeaderboardEntry(
                player_id=pid,
                username=player.username,
                total_games=total_games,
                wins=wins,
                losses=losses,
                win_rate=round(win_rate, 1),
                avg_placement=round(avg_placement, 2),
            )
        )

    # Sort by wins desc, then win_rate desc
    entries.sort(key=lambda e: (e.wins, e.win_rate), reverse=True)
    return entries


def _compute_avg_placement(db: Session, player_id: int) -> float:
    """Compute the average placement across all completed games for a player."""
    results = (
        db.query(GameResult)
        .join(Game, Game.id == GameResult.game_id)
        .join(SpawnedCountry, SpawnedCountry.game_id == Game.id)
        .filter(SpawnedCountry.player_id == player_id)
        .all()
    )

    placements = []
    for result in results:
        rankings = json.loads(result.final_rankings) if result.final_rankings else []
        player_ranking = next(
            (r for r in rankings if r["player_id"] == player_id), None
        )
        if player_ranking:
            placements.append(player_ranking["rank"])

    return sum(placements) / len(placements) if placements else 0.0


def _compute_player_stats(db: Session, player_id: int) -> tuple:
    """Return (total_games, wins) for a player."""
    # Count games this player participated in that have results
    total_games = (
        db.query(GameResult)
        .join(Game, Game.id == GameResult.game_id)
        .join(SpawnedCountry, SpawnedCountry.game_id == Game.id)
        .filter(SpawnedCountry.player_id == player_id)
        .count()
    )

    wins = (
        db.query(GameResult)
        .filter(GameResult.winner_player_id == player_id)
        .count()
    )

    return total_games, wins
