# Player Stats & Global Leaderboard

## Overview

The player stats system tracks performance across completed games and provides a global leaderboard ranking all players.

## Pages & Components

### Global Leaderboard (`/stats`)

Displays all players ranked by wins (primary) then average score (secondary). Each row links to the player's detailed stats page.

**Columns:** Rank, Player, Wins, Games Played, Win Rate, Average Score, Best Score

The leaderboard is accessible from the navbar ("Leaderboard" link) and requires authentication.

### Player Stats Page (`/stats/:playerId`)

Shows detailed statistics for a single player:

- **Summary cards**: Games Played, Wins (with win rate), Best Score
- **Performance panel**: Average Score, Favorite Country, Member Since date
- **Countries Played**: Breakdown of how many games played with each country
- **Game History table**: All completed games with placement, score, country, rounds, and date

## API Endpoints

### `GET /api/players/leaderboard`

Returns the global leaderboard across all completed games.

**Response:**
```json
[
  {
    "player_id": 1,
    "player_name": "alice",
    "games_played": 5,
    "wins": 3,
    "average_score": 24.5,
    "best_score": 30
  }
]
```

Sorted by wins descending, then average score descending.

### `GET /api/players/{player_id}/stats`

Returns detailed stats for a specific player.

**Response:**
```json
{
  "player_id": 1,
  "username": "alice",
  "created_at": "2026-01-15T10:30:00",
  "games_played": 5,
  "wins": 3,
  "average_score": 24.5,
  "best_score": 30,
  "favorite_country": "England",
  "countries_played": {
    "England": 3,
    "France": 2
  },
  "game_history": [
    {
      "game_id": 10,
      "placement": 1,
      "score": 30,
      "country_name": "England",
      "duration_rounds": 5,
      "finished_at": "2026-03-20T15:00:00"
    }
  ]
}
```

**Error:** Returns 404 if the player does not exist.

## Frontend Components

| Component | File | Purpose |
|-----------|------|---------|
| `StatsPage` | `frontend/src/pages/PlayerStats.tsx` | Route handler that renders either the leaderboard or player detail |
| `GlobalLeaderboard` | `frontend/src/components/GlobalLeaderboard.tsx` | Reusable leaderboard table component |

## Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/stats` | `StatsPage` | Global leaderboard view |
| `/stats/:playerId` | `StatsPage` | Individual player stats view |

## Data Source

Stats are computed from `GameResult` records, which are automatically created when a game reaches the `completed` phase. The `final_rankings` JSON field contains placement, score, and breakdown for each player in the game.
