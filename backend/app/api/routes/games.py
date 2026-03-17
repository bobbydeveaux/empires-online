from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.database import get_db
from app.models.models import Game, Player, Country, SpawnedCountry, GameHistory
from app.schemas.schemas import (
    GameCreate,
    Game as GameSchema,
    GameJoin,
    SpawnedCountry as SpawnedCountrySchema,
    GameState,
    SpawnedCountryWithDetails,
    DevelopmentResult,
    ActionResult,
    GameAction,
    VictoryPoints,
)
from app.api.routes.auth import get_current_user
from app.services.game_logic import GameLogic
from app.services.game_broadcast import (
    broadcast_event,
    game_started_message,
    development_completed_message,
    phase_changed_message,
    action_performed_message,
    round_advanced_message,
    game_completed_message,
    player_joined_game_message,
    game_state_update_message,
)
import json

router = APIRouter()


def _build_leaderboard(db: Session, game_id: int) -> list:
    """Build the leaderboard for a game (used for game_completed broadcasts)."""
    spawned_countries = (
        db.query(SpawnedCountry).filter(SpawnedCountry.game_id == game_id).all()
    )
    leaderboard = []
    for sc in spawned_countries:
        country = db.query(Country).filter(Country.id == sc.country_id).first()
        player = db.query(Player).filter(Player.id == sc.player_id).first()
        victory_points = GameLogic.calculate_victory_points(sc)
        leaderboard.append(
            {
                "player_id": sc.player_id,
                "player_name": player.username,
                "country_name": country.name,
                "score": victory_points["total_score"],
                "breakdown": victory_points["breakdown"],
            }
        )
    leaderboard.sort(key=lambda x: x["score"], reverse=True)
    return leaderboard


def _build_game_state_payload(db: Session, game: Game) -> dict:
    """Build a serialisable game-state dict for WebSocket broadcasts."""
    spawned_countries = (
        db.query(SpawnedCountry).filter(SpawnedCountry.game_id == game.id).all()
    )
    players = []
    leaderboard = []
    for sc in spawned_countries:
        country = db.query(Country).filter(Country.id == sc.country_id).first()
        player = db.query(Player).filter(Player.id == sc.player_id).first()
        players.append({
            "id": sc.id,
            "country_id": sc.country_id,
            "game_id": sc.game_id,
            "player_id": sc.player_id,
            "gold": sc.gold,
            "bonds": sc.bonds,
            "territories": sc.territories,
            "goods": sc.goods,
            "people": sc.people,
            "banks": sc.banks,
            "supporters": sc.supporters,
            "revolters": sc.revolters,
            "development_completed": sc.development_completed,
            "actions_completed": sc.actions_completed,
            "country": {
                "id": country.id,
                "name": country.name,
                "default_gold": country.default_gold,
                "default_bonds": country.default_bonds,
                "default_territories": country.default_territories,
                "default_goods": country.default_goods,
                "default_people": country.default_people,
            },
            "player": {
                "id": player.id,
                "username": player.username,
                "email": player.email,
                "email_verified": player.email_verified,
                "created_at": player.created_at.isoformat() if player.created_at else None,
            },
        })
        vp = GameLogic.calculate_victory_points(sc)
        leaderboard.append({
            "player_id": sc.player_id,
            "player_name": player.username,
            "country_name": country.name,
            "score": vp["total_score"],
            "breakdown": vp["breakdown"],
        })
    leaderboard.sort(key=lambda x: x["score"], reverse=True)
    return {
        "game": {
            "id": game.id,
            "rounds": game.rounds,
            "rounds_remaining": game.rounds_remaining,
            "phase": game.phase,
            "creator_id": game.creator_id,
            "created_at": game.created_at.isoformat() if game.created_at else None,
            "started_at": game.started_at.isoformat() if game.started_at else None,
        },
        "players": players,
        "leaderboard": leaderboard,
    }


@router.post("/", response_model=GameSchema)
def create_game(
    game_data: GameCreate,
    current_user: Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new game."""
    # Validate countries exist
    for country_name in game_data.countries:
        country = db.query(Country).filter(Country.name == country_name).first()
        if not country:
            raise HTTPException(
                status_code=400, detail=f"Country {country_name} not found"
            )

    # Create game
    db_game = Game(
        rounds=game_data.rounds,
        rounds_remaining=game_data.rounds,
        phase="waiting",
        creator_id=current_user.id,
    )
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    return db_game


@router.get("/", response_model=List[GameSchema])
def list_games(db: Session = Depends(get_db)):
    """List all available games."""
    return (
        db.query(Game)
        .filter(Game.phase.in_(["waiting", "development", "actions"]))
        .all()
    )


@router.get("/{game_id}", response_model=GameState)
def get_game_state(
    game_id: int,
    current_user: Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get complete game state."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Get all spawned countries with details
    spawned_countries = (
        db.query(SpawnedCountry).filter(SpawnedCountry.game_id == game_id).all()
    )

    players_data = []
    leaderboard = []

    for sc in spawned_countries:
        # Get country and player details
        country = db.query(Country).filter(Country.id == sc.country_id).first()
        player = db.query(Player).filter(Player.id == sc.player_id).first()

        player_data = SpawnedCountryWithDetails(
            **sc.__dict__, country=country, player=player
        )
        players_data.append(player_data)

        # Calculate victory points for leaderboard
        victory_points = GameLogic.calculate_victory_points(sc)
        leaderboard.append(
            {
                "player_id": sc.player_id,
                "player_name": player.username,
                "country_name": country.name,
                "score": victory_points["total_score"],
                "breakdown": victory_points["breakdown"],
            }
        )

    # Sort leaderboard by score
    leaderboard.sort(key=lambda x: x["score"], reverse=True)

    return GameState(game=game, players=players_data, leaderboard=leaderboard)


@router.post("/{game_id}/join")
def join_game(
    game_id: int,
    join_data: GameJoin,
    background_tasks: BackgroundTasks,
    current_user: Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Join a game with a specific country."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.phase != "waiting":
        raise HTTPException(status_code=400, detail="Game has already started")

    # Check if country exists
    country = db.query(Country).filter(Country.id == join_data.country_id).first()
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    # Check if country is already taken
    existing = (
        db.query(SpawnedCountry)
        .filter(
            SpawnedCountry.game_id == game_id,
            SpawnedCountry.country_id == join_data.country_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Country already taken")

    # Check if player is already in this game
    existing_player = (
        db.query(SpawnedCountry)
        .filter(
            SpawnedCountry.game_id == game_id,
            SpawnedCountry.player_id == current_user.id,
        )
        .first()
    )
    if existing_player:
        raise HTTPException(status_code=400, detail="Player already in this game")

    # Create spawned country with default values
    spawned_country = SpawnedCountry(
        country_id=join_data.country_id,
        game_id=game_id,
        player_id=current_user.id,
        gold=country.default_gold,
        bonds=country.default_bonds,
        territories=country.default_territories,
        goods=country.default_goods,
        people=country.default_people,
        banks=0,
        supporters=0,
        revolters=0,
    )

    db.add(spawned_country)
    db.commit()
    db.refresh(spawned_country)

    # Broadcast player joined game event
    background_tasks.add_task(
        broadcast_event,
        game_id,
        player_joined_game_message(
            game_id=game_id,
            player_id=current_user.id,
            username=current_user.username,
            country_name=country.name,
        ),
    )

    return {
        "spawned_country_id": spawned_country.id,
        "message": "Joined game successfully",
    }


@router.post("/{game_id}/start")
def start_game(
    game_id: int,
    background_tasks: BackgroundTasks,
    current_user: Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a game (only creator can start)."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.creator_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only game creator can start the game"
        )

    if game.phase != "waiting":
        raise HTTPException(status_code=400, detail="Game has already started")

    # Check if there are at least 2 players
    player_count = (
        db.query(SpawnedCountry).filter(SpawnedCountry.game_id == game_id).count()
    )
    if player_count < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players to start")

    # Start the game
    game.phase = "development"
    game.started_at = func.now()
    db.commit()

    # Broadcast game started event
    background_tasks.add_task(
        broadcast_event,
        game_id,
        game_started_message(game_id=game_id, phase="development"),
    )

    # Broadcast updated game state after phase transition
    db.refresh(game)  # refresh to pick up started_at set by func.now()
    game_state_payload = _build_game_state_payload(db, game)
    background_tasks.add_task(
        broadcast_event,
        game_id,
        game_state_update_message(game_id=game_id, game_state=game_state_payload),
    )

    return {"status": "started", "current_phase": "development"}


@router.post(
    "/{game_id}/countries/{spawned_country_id}/develop",
    response_model=DevelopmentResult,
)
def execute_development(
    game_id: int,
    spawned_country_id: int,
    background_tasks: BackgroundTasks,
    current_user: Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute development phase for a country."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.phase != "development":
        raise HTTPException(status_code=400, detail="Not in development phase")

    spawned_country = (
        db.query(SpawnedCountry)
        .filter(
            SpawnedCountry.id == spawned_country_id,
            SpawnedCountry.game_id == game_id,
            SpawnedCountry.player_id == current_user.id,
        )
        .first()
    )

    if not spawned_country:
        raise HTTPException(
            status_code=404, detail="Country not found or not owned by player"
        )

    if spawned_country.development_completed:
        raise HTTPException(
            status_code=400, detail="Development already completed this round"
        )

    # Execute development logic
    result = GameLogic.calculate_development(spawned_country)

    # Update the spawned country state
    new_state = result["new_state"]
    spawned_country.gold = new_state["gold"]
    spawned_country.supporters = new_state["supporters"]
    spawned_country.revolters = new_state["revolters"]
    spawned_country.goods = new_state["goods"]
    spawned_country.development_completed = True

    # Add to game history
    history_entry = GameHistory(
        game_id=game_id,
        spawned_country_id=spawned_country_id,
        round_number=game.rounds - game.rounds_remaining + 1,
        action_type="development",
        details=json.dumps(result["changes"]),
    )
    db.add(history_entry)

    db.commit()

    # Check if all players have completed development
    total_players = (
        db.query(SpawnedCountry).filter(SpawnedCountry.game_id == game_id).count()
    )
    completed_players = (
        db.query(SpawnedCountry)
        .filter(
            SpawnedCountry.game_id == game_id,
            SpawnedCountry.development_completed == True,
        )
        .count()
    )

    # Broadcast development completed event
    background_tasks.add_task(
        broadcast_event,
        game_id,
        development_completed_message(
            game_id=game_id,
            player_id=current_user.id,
            username=current_user.username,
            completed_count=completed_players,
            total_count=total_players,
        ),
    )

    # Broadcast updated game state so all clients see development progress
    game_state_payload = _build_game_state_payload(db, game)
    background_tasks.add_task(
        broadcast_event,
        game_id,
        game_state_update_message(game_id=game_id, game_state=game_state_payload),
    )

    if completed_players == total_players:
        # Move to actions phase
        game.phase = "actions"
        db.commit()

        # Broadcast phase change event
        background_tasks.add_task(
            broadcast_event,
            game_id,
            phase_changed_message(game_id=game_id, new_phase="actions"),
        )

        # Broadcast updated game state after phase transition
        game_state_payload = _build_game_state_payload(db, game)
        background_tasks.add_task(
            broadcast_event,
            game_id,
            game_state_update_message(game_id=game_id, game_state=game_state_payload),
        )

    return DevelopmentResult(
        success=True, new_state=result["new_state"], changes=result["changes"]
    )


@router.post(
    "/{game_id}/countries/{spawned_country_id}/actions", response_model=ActionResult
)
def perform_action(
    game_id: int,
    spawned_country_id: int,
    action_data: GameAction,
    background_tasks: BackgroundTasks,
    current_user: Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Perform an action during the actions phase."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.phase != "actions":
        raise HTTPException(status_code=400, detail="Not in actions phase")

    spawned_country = (
        db.query(SpawnedCountry)
        .filter(
            SpawnedCountry.id == spawned_country_id,
            SpawnedCountry.game_id == game_id,
            SpawnedCountry.player_id == current_user.id,
        )
        .first()
    )

    if not spawned_country:
        raise HTTPException(
            status_code=404, detail="Country not found or not owned by player"
        )

    # Perform the action
    result = GameLogic.perform_action(
        spawned_country, action_data.action, action_data.quantity
    )

    if result["success"]:
        # Add to game history
        history_entry = GameHistory(
            game_id=game_id,
            spawned_country_id=spawned_country_id,
            round_number=game.rounds - game.rounds_remaining + 1,
            action_type=action_data.action,
            details=json.dumps(result["changes"]),
        )
        db.add(history_entry)
        db.commit()

        # Broadcast action performed event
        background_tasks.add_task(
            broadcast_event,
            game_id,
            action_performed_message(
                game_id=game_id,
                player_id=current_user.id,
                username=current_user.username,
                action=action_data.action,
                quantity=action_data.quantity,
            ),
        )

        # Broadcast updated game state so all clients refresh their UI
        game_state_payload = _build_game_state_payload(db, game)
        background_tasks.add_task(
            broadcast_event,
            game_id,
            game_state_update_message(game_id=game_id, game_state=game_state_payload),
        )

    return ActionResult(**result)


@router.post("/{game_id}/next-round")
def next_round(
    game_id: int,
    background_tasks: BackgroundTasks,
    current_user: Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Move to the next round (admin action)."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.creator_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only game creator can advance rounds"
        )

    if game.phase != "actions":
        raise HTTPException(
            status_code=400, detail="Can only advance from actions phase"
        )

    # Reset development and action completion for all players
    db.query(SpawnedCountry).filter(SpawnedCountry.game_id == game_id).update(
        {"development_completed": False, "actions_completed": False}
    )

    # Decrease rounds remaining
    game.rounds_remaining -= 1

    if game.rounds_remaining <= 0:
        game.phase = "completed"
    else:
        game.phase = "development"

    db.commit()

    new_round_number = game.rounds - game.rounds_remaining + 1

    if game.phase == "completed":
        # Broadcast game completed with final leaderboard
        leaderboard = _build_leaderboard(db, game_id)
        background_tasks.add_task(
            broadcast_event,
            game_id,
            game_completed_message(game_id=game_id, leaderboard=leaderboard),
        )
    else:
        # Broadcast round advanced event
        background_tasks.add_task(
            broadcast_event,
            game_id,
            round_advanced_message(
                game_id=game_id,
                new_round=new_round_number,
                phase=game.phase,
            ),
        )

    # Broadcast updated game state after phase transition
    game_state_payload = _build_game_state_payload(db, game)
    background_tasks.add_task(
        broadcast_event,
        game_id,
        game_state_update_message(game_id=game_id, game_state=game_state_payload),
    )

    return {
        "message": f"Advanced to round {new_round_number}",
        "phase": game.phase,
    }


@router.get("/{game_id}/leaderboard")
def get_leaderboard(game_id: int, db: Session = Depends(get_db)):
    """Get current leaderboard for a game."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return _build_leaderboard(db, game_id)
