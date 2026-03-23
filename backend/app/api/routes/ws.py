"""WebSocket endpoint with JWT authentication for real-time game updates."""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import Player
from app.services.ws_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Action message types that spectators are not allowed to send
_ACTION_TYPES = frozenset({"chat", "action", "develop", "end_actions"})


def _get_db() -> Session:
    """Create a database session for WebSocket handlers (not using Depends)."""
    return SessionLocal()


def _authenticate_token(token: Optional[str]) -> Optional[dict]:
    """Validate a JWT token and return the decoded payload, or None if invalid."""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def _get_player(db: Session, username: str) -> Optional[Player]:
    """Look up a player by username."""
    return db.query(Player).filter(Player.username == username).first()


def _extract_token(websocket: WebSocket, token: Optional[str]) -> Optional[str]:
    """Extract JWT token from query param or Authorization header."""
    auth_token = token
    if not auth_token:
        headers = dict(websocket.headers)
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]
    return auth_token


@router.websocket("/ws/{game_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: int,
    token: Optional[str] = Query(default=None),
) -> None:
    """WebSocket endpoint for real-time game updates.

    Authenticate via query parameter: /ws/{game_id}?token=<jwt>
    Or via the first message after connecting (fallback).

    On success the connection is added to the game room and will receive
    broadcast messages.  On auth failure the socket is closed with code 4001.
    """
    auth_token = _extract_token(websocket, token)

    # Validate the token
    payload = _authenticate_token(auth_token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    username: Optional[str] = payload.get("sub")
    is_spectator: bool = payload.get("is_spectator", False)

    if is_spectator:
        # Spectator connection — no player lookup required
        await manager.connect_spectator(websocket, game_id)
        await manager.send_personal(
            websocket,
            {"type": "spectator_joined", "game_id": game_id},
        )
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")
                if msg_type == "ping":
                    await manager.send_personal(websocket, {"type": "pong"})
                else:
                    # Spectators cannot send game actions
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "error",
                            "code": 403,
                            "message": "Spectators cannot send actions",
                        },
                    )
        except WebSocketDisconnect:
            manager.disconnect_spectator(websocket)
        except Exception:
            logger.exception("WebSocket error for spectator in game %d", game_id)
            manager.disconnect_spectator(websocket)
        return

    # Player connection
    if not username:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Look up the player in the database
    db = _get_db()
    try:
        player = _get_player(db, username)
        if not player:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        player_id = player.id
        player_username = player.username
    finally:
        db.close()

    # Accept and register in the game room
    await manager.connect(websocket, game_id)

    # Notify the room that a player joined
    await manager.broadcast_to_room(
        game_id,
        {
            "type": "player_joined",
            "game_id": game_id,
            "player": {"id": player_id, "username": player_username},
        },
    )

    try:
        while True:
            # Receive and handle incoming messages
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
            elif msg_type == "chat":
                await manager.broadcast_to_room(
                    game_id,
                    {
                        "type": "chat",
                        "game_id": game_id,
                        "player": {"id": player_id, "username": player_username},
                        "message": data.get("message", ""),
                    },
                )
            else:
                # Echo unrecognised messages back with an error
                await manager.send_personal(
                    websocket,
                    {"type": "error", "message": f"Unknown message type: {msg_type}"},
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast_to_room(
            game_id,
            {
                "type": "player_left",
                "game_id": game_id,
                "player": {"id": player_id, "username": player_username},
            },
        )
    except Exception:
        logger.exception("WebSocket error for player %s in game %d", player_username, game_id)
        manager.disconnect(websocket)


@router.websocket("/ws/{game_id}/spectate")
async def spectator_websocket_endpoint(
    websocket: WebSocket,
    game_id: int,
    token: Optional[str] = Query(default=None),
) -> None:
    """WebSocket endpoint for spectators.

    Spectators receive all game state broadcasts but cannot send action
    messages.  Action attempts are rejected with a 403 error message.
    Only ``ping`` messages are allowed from spectators.

    Authenticate via query parameter: /ws/{game_id}/spectate?token=<jwt>
    """
    auth_token = _extract_token(websocket, token)

    username = _authenticate_token(auth_token)
    if not username:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Look up the player in the database (spectators still need a valid account)
    db = _get_db()
    try:
        player = _get_player(db, username)
        if not player:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        player_username = player.username
    finally:
        db.close()

    # Accept and register as a spectator
    await manager.connect_spectator(websocket, game_id)

    # Notify the room that a spectator joined
    await manager.broadcast_to_room(
        game_id,
        {
            "type": "spectator_joined",
            "game_id": game_id,
            "spectator_count": manager.get_spectator_count(game_id),
        },
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
            elif msg_type in _ACTION_TYPES:
                # Reject action messages from spectators with 403
                await manager.send_personal(
                    websocket,
                    {
                        "type": "error",
                        "code": 403,
                        "message": "Spectators cannot perform actions",
                    },
                )
            else:
                await manager.send_personal(
                    websocket,
                    {
                        "type": "error",
                        "code": 403,
                        "message": "Spectators cannot perform actions",
                    },
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast_to_room(
            game_id,
            {
                "type": "spectator_left",
                "game_id": game_id,
                "spectator_count": manager.get_spectator_count(game_id),
            },
        )
    except Exception:
        logger.exception("Spectator WebSocket error for %s in game %d", player_username, game_id)
        manager.disconnect(websocket)
