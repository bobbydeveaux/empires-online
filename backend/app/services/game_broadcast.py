"""Game state broadcasting via WebSocket.

Provides helper functions that build and broadcast game-event messages
to all WebSocket clients connected to a game room.  These are designed
to be scheduled as FastAPI BackgroundTasks from synchronous REST handlers.
"""

import asyncio
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


# ---------------------------------------------------------------------------
# Broadcast dispatcher (runs as a BackgroundTask)
# ---------------------------------------------------------------------------

async def _broadcast(game_id: int, message: Dict[str, Any]) -> None:
    """Send *message* to every WebSocket in the game room."""
    try:
        await manager.broadcast_to_room(game_id, message)
    except Exception:
        logger.exception("Failed to broadcast %s to game %d", message.get("type"), game_id)


def broadcast_event(game_id: int, message: Dict[str, Any]) -> None:
    """Schedule a broadcast; safe to call from sync code (BackgroundTask target).

    When used as a BackgroundTask callable, FastAPI will ``await`` the
    coroutine returned by the inner async helper automatically.
    This function is intentionally synchronous so it can be passed directly
    to ``background_tasks.add_task()``.
    """
    loop = asyncio.get_event_loop()
    loop.create_task(_broadcast(game_id, message))
