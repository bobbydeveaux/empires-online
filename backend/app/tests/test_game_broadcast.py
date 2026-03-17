"""Unit tests for game state broadcasting module."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.game_broadcast import (
    game_started_message,
    development_completed_message,
    phase_changed_message,
    action_performed_message,
    round_advanced_message,
    game_completed_message,
    player_joined_game_message,
    broadcast_event,
    _broadcast,
)


class TestMessageBuilders:
    """Verify each message builder produces the expected structure."""

    def test_game_started_message(self):
        msg = game_started_message(game_id=1, phase="development")
        assert msg == {
            "type": "game_started",
            "game_id": 1,
            "phase": "development",
        }

    def test_development_completed_message(self):
        msg = development_completed_message(
            game_id=1,
            player_id=5,
            username="alice",
            completed_count=2,
            total_count=3,
        )
        assert msg == {
            "type": "development_completed",
            "game_id": 1,
            "player": {"id": 5, "username": "alice"},
            "completed_count": 2,
            "total_count": 3,
        }

    def test_phase_changed_message(self):
        msg = phase_changed_message(game_id=2, new_phase="actions")
        assert msg == {
            "type": "phase_changed",
            "game_id": 2,
            "phase": "actions",
        }

    def test_action_performed_message(self):
        msg = action_performed_message(
            game_id=1,
            player_id=3,
            username="bob",
            action="buy_bond",
            quantity=2,
        )
        assert msg == {
            "type": "action_performed",
            "game_id": 1,
            "player": {"id": 3, "username": "bob"},
            "action": "buy_bond",
            "quantity": 2,
        }

    def test_round_advanced_message(self):
        msg = round_advanced_message(game_id=1, new_round=3, phase="development")
        assert msg == {
            "type": "round_advanced",
            "game_id": 1,
            "round": 3,
            "phase": "development",
        }

    def test_game_completed_message(self):
        leaderboard = [
            {"player_name": "alice", "score": 100},
            {"player_name": "bob", "score": 80},
        ]
        msg = game_completed_message(game_id=1, leaderboard=leaderboard)
        assert msg == {
            "type": "game_completed",
            "game_id": 1,
            "leaderboard": leaderboard,
        }

    def test_player_joined_game_message(self):
        msg = player_joined_game_message(
            game_id=1,
            player_id=2,
            username="charlie",
            country_name="Germany",
        )
        assert msg == {
            "type": "player_joined_game",
            "game_id": 1,
            "player": {"id": 2, "username": "charlie"},
            "country_name": "Germany",
        }


class TestBroadcast:
    """Verify that _broadcast delegates to the ConnectionManager."""

    @pytest.mark.asyncio
    async def test_broadcast_calls_manager(self):
        message = {"type": "game_started", "game_id": 1, "phase": "development"}
        with patch("app.services.game_broadcast.manager") as mock_manager:
            mock_manager.broadcast_to_room = AsyncMock()
            await _broadcast(1, message)
            mock_manager.broadcast_to_room.assert_awaited_once_with(1, message)

    @pytest.mark.asyncio
    async def test_broadcast_handles_exception(self):
        """Exceptions in broadcast should be caught, not propagated."""
        with patch("app.services.game_broadcast.manager") as mock_manager:
            mock_manager.broadcast_to_room = AsyncMock(
                side_effect=Exception("connection lost")
            )
            # Should not raise
            await _broadcast(1, {"type": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_event_creates_task(self):
        """broadcast_event should schedule _broadcast on the event loop."""
        message = {"type": "game_started", "game_id": 1, "phase": "development"}
        with patch("app.services.game_broadcast.manager") as mock_manager:
            mock_manager.broadcast_to_room = AsyncMock()
            broadcast_event(1, message)
            # Allow the task to run
            await asyncio.sleep(0.01)
            mock_manager.broadcast_to_room.assert_awaited_once_with(1, message)
