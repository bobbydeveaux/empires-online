import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.database import get_db
from app.models.models import Player, Country, GameResult, SpawnedCountry, Game
from app.schemas.schemas import Player as PlayerSchema, Country as CountrySchema
from app.api.routes.auth import get_current_user

router = APIRouter()


@router.get("/me", response_model=PlayerSchema)
def get_current_player(current_user: Player = Depends(get_current_user)):
    """Get current player information."""
    return current_user


@router.get("/leaderboard")
def get_global_leaderboard(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get global leaderboard across all completed games.

    Returns players ranked by total wins, then by average score.
    """
    results = db.query(GameResult).all()

    # Aggregate stats per player
    player_stats: Dict[int, Dict[str, Any]] = {}

    for result in results:
        rankings = json.loads(result.final_rankings)
        for entry in rankings:
            pid = entry["player_id"]
            if pid not in player_stats:
                player_stats[pid] = {
                    "player_id": pid,
                    "player_name": entry["player_name"],
                    "games_played": 0,
                    "wins": 0,
                    "total_score": 0,
                    "best_score": 0,
                }
            stats = player_stats[pid]
            stats["games_played"] += 1
            stats["total_score"] += entry["score"]
            if entry["score"] > stats["best_score"]:
                stats["best_score"] = entry["score"]
            if entry["placement"] == 1:
                stats["wins"] += 1

    leaderboard = []
    for stats in player_stats.values():
        avg = stats["total_score"] / stats["games_played"] if stats["games_played"] > 0 else 0
        leaderboard.append({
            "player_id": stats["player_id"],
            "player_name": stats["player_name"],
            "games_played": stats["games_played"],
            "wins": stats["wins"],
            "average_score": round(avg, 1),
            "best_score": stats["best_score"],
        })

    leaderboard.sort(key=lambda x: (-x["wins"], -x["average_score"]))
    return leaderboard


@router.get("/{player_id}/stats")
def get_player_stats(player_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get stats for a specific player across all games."""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Count games played (completed games where the player had a spawned country)
    completed_game_ids = (
        db.query(Game.id).filter(Game.phase == "completed").subquery()
    )
    games_played = (
        db.query(func.count(SpawnedCountry.id))
        .filter(
            SpawnedCountry.player_id == player_id,
            SpawnedCountry.game_id.in_(completed_game_ids),
        )
        .scalar()
    ) or 0

    # Get wins and score data from GameResult
    results = db.query(GameResult).all()

    wins = 0
    total_score = 0.0
    best_score = 0.0
    game_history = []
    countries_played: Dict[str, int] = {}

    for result in results:
        rankings = json.loads(result.final_rankings)
        for entry in rankings:
            if entry["player_id"] == player_id:
                score = entry["score"]
                placement = entry["placement"]
                country = entry["country_name"]

                total_score += score
                if score > best_score:
                    best_score = score
                if placement == 1:
                    wins += 1

                countries_played[country] = countries_played.get(country, 0) + 1

                game_history.append({
                    "game_id": result.game_id,
                    "placement": placement,
                    "score": score,
                    "country_name": country,
                    "duration_rounds": result.duration_rounds,
                    "finished_at": result.finished_at.isoformat() if result.finished_at else None,
                })

    avg_score = round(total_score / games_played, 1) if games_played > 0 else 0
    favorite_country = max(countries_played, key=countries_played.get) if countries_played else None

    return {
        "player_id": player.id,
        "username": player.username,
        "created_at": player.created_at.isoformat() if player.created_at else None,
        "games_played": games_played,
        "wins": wins,
        "average_score": avg_score,
        "best_score": best_score,
        "favorite_country": favorite_country,
        "countries_played": countries_played,
        "game_history": sorted(game_history, key=lambda x: x["finished_at"] or "", reverse=True),
    }


@router.get("/", response_model=List[PlayerSchema])
def list_players(db: Session = Depends(get_db)):
    """List all players (for leaderboards, etc.)."""
    return db.query(Player).all()


@router.get("/countries", response_model=List[CountrySchema])
def list_countries(db: Session = Depends(get_db)):
    """List all available countries."""
    return db.query(Country).all()
