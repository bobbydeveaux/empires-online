# Player Stats & Global Leaderboard

## Overview

The player stats system tracks performance across completed games and provides a global leaderboard ranking all players by wins.

## Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/stats` | `PlayerStats` | Current user's stats (protected) |
| `/stats/:playerId` | `PlayerStats` | Specific player's stats (protected) |

## Navigation

- **Navbar**: "Stats" link visible when authenticated
- **Game Lobby**: "History & Stats" button in the page header
- **Leaderboard rows**: Click a player row to view their stats

## Frontend Components

### `PlayerStats` (`pages/PlayerStats.tsx`)

The main stats page with two tabs:

- **My Stats tab**: Shows a stats overview (games played, wins, losses, win rate) and a recent games history table.
- **Leaderboard tab**: Renders the `GlobalLeaderboard` component.

Accepts an optional `playerId` URL parameter. If omitted, defaults to the current authenticated user.

### `GlobalLeaderboard` (`components/GlobalLeaderboard.tsx`)

Displays all players who have completed at least one game, ranked by wins (then win rate). Each row is clickable and navigates to that player's stats page.

## Backend API

### `GET /api/players/leaderboard`

Returns an array of players ranked by wins. Only includes players with at least one completed game.

**Response:**
```json
[
  {
    "player_id": 1,
    "username": "alice",
    "games_played": 10,
    "wins": 7,
    "losses": 3,
    "win_rate": 70.0
  }
]
```

### `GET /api/players/{player_id}/stats`

Returns a player's stats and recent game history (up to 20 games).

**Response:**
```json
{
  "player_id": 1,
  "username": "alice",
  "games_played": 10,
  "wins": 7,
  "losses": 3,
  "win_rate": 70.0,
  "history": [
    {
      "game_id": 42,
      "country_name": "England",
      "rounds": 5,
      "placement": 1,
      "won": true,
      "finished_at": "2024-06-15T12:00:00"
    }
  ]
}
```

**Error:** Returns 404 if the player does not exist.

## TypeScript Types

Defined in `frontend/src/types/index.ts`:

- `PlayerStatsData` — Player stats response including history array
- `GameHistoryEntry` — Single game result in history
- `GlobalLeaderboardEntry` — Leaderboard row data

## Data Source

Stats are computed from `GameResult` records, which are automatically created when a game reaches the `completed` phase. The `winner_player_id` field and `final_rankings` JSON field contain placement, score, and breakdown for each player in the game.
