"""Game state broadcasting via WebSocket.

Provides helper functions that build and broadcast game-event messages
to all WebSocket clients connected to a game room.  These are designed
to be scheduled as FastAPI BackgroundTasks from synchronous REST handlers.
"""

import logging
from typing import Any, Dict, List, Optional

from app.services.ws_manager import manager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------

def _player_summary(player_id: int, username: str) -> Dict[str, Any]:
    return {"id": player_id, "username": username}


def game_started_message(game_id: int, phase: str) -> Dict[str, Any]:
    return {
        "type": "game_started",
        "game_id": game_id,
        "phase": phase,
    }


def development_completed_message(
    game_id: int,
    player_id: int,
    username: str,
    completed_count: int,
    total_count: int,
) -> Dict[str, Any]:
    return {
        "type": "development_completed",
        "game_id": game_id,
        "player": _player_summary(player_id, username),
        "completed_count": completed_count,
        "total_count": total_count,
    }


def phase_changed_message(game_id: int, new_phase: str) -> Dict[str, Any]:
    return {
        "type": "phase_changed",
        "game_id": game_id,
        "phase": new_phase,
    }


def action_performed_message(
    game_id: int,
    player_id: int,
    username: str,
    action: str,
    quantity: int,
) -> Dict[str, Any]:
    return {
        "type": "action_performed",
        "game_id": game_id,
        "player": _player_summary(player_id, username),
        "action": action,
        "quantity": quantity,
    }


def round_advanced_message(
    game_id: int,
    new_round: int,
    phase: str,
) -> Dict[str, Any]:
    return {
        "type": "round_advanced",
        "game_id": game_id,
        "round": new_round,
        "phase": phase,
    }


def game_completed_message(
    game_id: int,
    leaderboard: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "type": "game_completed",
        "game_id": game_id,
        "leaderboard": leaderboard,
    }


def game_state_update_message(
    game_id: int,
    game_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    msg: Dict[str, Any] = {
        "type": "game_state_update",
        "game_id": game_id,
    }
    if game_state is not None:
        msg["game_state"] = game_state
    return msg


def player_joined_game_message(
    game_id: int,
    player_id: int,
    username: str,
    country_name: str,
) -> Dict[str, Any]:
    return {
        "type": "player_joined_game",
        "game_id": game_id,
        "player": _player_summary(player_id, username),
        "country_name": country_name,
    }


def actions_completed_message(
    game_id: int,
    player_id: int,
    username: str,
    completed_count: int,
    total_count: int,
) -> Dict[str, Any]:
    return {
        "type": "actions_completed",
        "game_id": game_id,
        "player": _player_summary(player_id, username),
        "completed_count": completed_count,
        "total_count": total_count,
    }



def stability_check_message(
    game_id: int,
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "type": "stability_check",
        "game_id": game_id,
        "results": results,
    }


def round_summary_message(
    game_id: int,
    round_number: int,
    summary: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "type": "round_summary",
        "game_id": game_id,
        "round": round_number,
        "summary": summary,
    }



def trade_proposed_message(
    game_id: int,
    trade: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "type": "trade_proposed",
        "game_id": game_id,
        "trade": trade,
    }


def trade_resolved_message(
    game_id: int,
    trade: Dict[str, Any],
    resolution: str,
) -> Dict[str, Any]:
    return {
        "type": "trade_resolved",
        "game_id": game_id,
        "trade": trade,
        "resolution": resolution,
    }


# ---------------------------------------------------------------------------
# Broadcast dispatcher (runs as a BackgroundTask)
# ---------------------------------------------------------------------------

async def _broadcast(game_id: int, message: Dict[str, Any]) -> None:
    """Send *message* to every WebSocket in the game room."""
    try:
        await manager.broadcast_to_room(game_id, message)
    except Exception:
        logger.exception("Failed to broadcast %s to game %d", message.get("type"), game_id)


async def broadcast_event(game_id: int, message: Dict[str, Any]) -> None:
    """Broadcast a game event via WebSocket.

    This is an async function so it can be passed directly to
    ``background_tasks.add_task()`` — FastAPI natively awaits async
    background task callables on the main event loop.
    """
    await _broadcast(game_id, message)
