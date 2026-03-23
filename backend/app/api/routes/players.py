import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Country, Game, GameResult, Player, SpawnedCountry
from app.schemas.schemas import Country as CountrySchema
from app.schemas.schemas import Player as PlayerSchema
from app.api.routes.auth import get_current_user

router = APIRouter()


@router.get("/me", response_model=PlayerSchema)
def get_current_player(current_user: Player = Depends(get_current_user)):
    """Get current player information."""
    return current_user


@router.get("/", response_model=List[PlayerSchema])
def list_players(db: Session = Depends(get_db)):
    """List all players (for leaderboards, etc.)."""
    return db.query(Player).all()


@router.get("/countries", response_model=List[CountrySchema])
def list_countries(db: Session = Depends(get_db)):
    """List all available countries."""
    return db.query(Country).all()


@router.get("/leaderboard")
def get_global_leaderboard(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get global leaderboard ranked by win count (minimum 1 completed game)."""
    # Get all players who have participated in completed games
    players = db.query(Player).all()
    leaderboard: List[Dict[str, Any]] = []

    for player in players:
        # Count games where this player participated and game is completed
        games_played = (
            db.query(func.count(SpawnedCountry.id))
            .join(Game, SpawnedCountry.game_id == Game.id)
            .filter(
                SpawnedCountry.player_id == player.id,
                Game.phase == "completed",
            )
            .scalar()
        ) or 0

        if games_played == 0:
            continue

        wins = (
            db.query(func.count(GameResult.id))
            .filter(GameResult.winner_player_id == player.id)
            .scalar()
        ) or 0

        win_rate = round((wins / games_played) * 100, 1) if games_played > 0 else 0.0

        leaderboard.append({
            "player_id": player.id,
            "username": player.username,
            "games_played": games_played,
            "wins": wins,
            "losses": games_played - wins,
            "win_rate": win_rate,
        })

    leaderboard.sort(key=lambda x: (-x["wins"], -x["win_rate"], x["username"]))
    return leaderboard


@router.get("/{player_id}/stats")
def get_player_stats(player_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get stats and game history for a specific player."""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Count completed games
    games_played = (
        db.query(func.count(SpawnedCountry.id))
        .join(Game, SpawnedCountry.game_id == Game.id)
        .filter(
            SpawnedCountry.player_id == player_id,
            Game.phase == "completed",
        )
        .scalar()
    ) or 0

    wins = (
        db.query(func.count(GameResult.id))
        .filter(GameResult.winner_player_id == player_id)
        .scalar()
    ) or 0

    win_rate = round((wins / games_played) * 100, 1) if games_played > 0 else 0.0

    # Get recent game history
    game_results = (
        db.query(GameResult, Game, SpawnedCountry, Country)
        .join(Game, GameResult.game_id == Game.id)
        .join(SpawnedCountry, (SpawnedCountry.game_id == Game.id) & (SpawnedCountry.player_id == player_id))
        .join(Country, SpawnedCountry.country_id == Country.id)
        .order_by(GameResult.finished_at.desc())
        .limit(20)
        .all()
    )

    history: List[Dict[str, Any]] = []
    for result, game, sc, country in game_results:
        # Parse final_rankings to find this player's placement
        rankings = json.loads(result.final_rankings) if result.final_rankings else []
        placement = None
        for rank in rankings:
            if rank.get("player_id") == player_id:
                placement = rank.get("rank")
                break

        history.append({
            "game_id": game.id,
            "country_name": country.name,
            "rounds": game.rounds,
            "placement": placement,
            "won": result.winner_player_id == player_id,
            "finished_at": result.finished_at.isoformat() if result.finished_at else None,
        })

    return {
        "player_id": player.id,
        "username": player.username,
        "games_played": games_played,
        "wins": wins,
        "losses": games_played - wins,
        "win_rate": win_rate,
        "history": history,
    }
