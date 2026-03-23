# Player Stats & Game History API

This document describes the player statistics, game history, and global leaderboard endpoints.

## Data Model

### GameResult

When a game reaches the `completed` phase, a `GameResult` record is automatically created:

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Primary key |
| `game_id` | int | FK to games (unique) |
| `winner_player_id` | int | FK to players — the player who won |
| `winner_country_id` | int | FK to countries — the country played by the winner |
| `duration_rounds` | int | Total rounds the game lasted |
| `finished_at` | datetime | Timestamp when the game completed |
| `final_rankings` | JSON text | Ordered list of all players with rank, score, country |

### final_rankings JSON format

```json
[
  {
    "rank": 1,
    "player_id": 3,
    "player_name": "alice",
    "country_name": "England",
    "score": 42.5
  },
  {
    "rank": 2,
    "player_id": 7,
    "player_name": "bob",
    "country_name": "France",
    "score": 31.0
  }
]
```

## Endpoints

### GET /api/players/{player_id}/history

Returns a list of completed games for the given player, most recent first.

**Response:**
```json
[
  {
    "game_id": 5,
    "rounds": 3,
    "finished_at": "2026-03-23T12:00:00Z",
    "rank": 1,
    "score": 42.5,
    "country_name": "England",
    "won": true
  }
]
```

### GET /api/players/{player_id}/stats

Returns aggregated statistics for a player.

**Response:**
```json
{
  "id": 3,
  "username": "alice",
  "email": "alice@example.com",
  "total_games": 10,
  "wins": 6,
  "losses": 4,
  "win_rate": 60.0
}
```

### GET /api/players/leaderboard/global

Returns the global all-time leaderboard, sorted by wins (descending).

**Response:**
```json
[
  {
    "player_id": 3,
    "username": "alice",
    "total_games": 10,
    "wins": 6,
    "losses": 4,
    "win_rate": 60.0,
    "avg_placement": 1.4
  }
]
```

## How Game Results Are Recorded

Game results are recorded automatically when a game's round advancement causes `rounds_remaining` to reach 0. The `_advance_round` helper in `games.py`:

1. Builds the final leaderboard (victory points for all players)
2. Calls `_record_game_result()` which persists a `GameResult` row
3. The winner is determined by the highest victory point score
4. A duplicate check prevents recording the same game twice

## Database Migration

The `game_results` table is created by Alembic migration `002_add_game_results.py`.
