# Spectator Mode

Spectator mode allows authenticated users to watch a game in progress without participating. The spectator view provides a read-only display of the full game state with real-time updates via WebSocket.

## Frontend Route

- **URL**: `/spectate/:gameId`
- **Component**: `SpectatorView.tsx`
- **Auth**: Requires authentication (protected route)

## Features

### Read-Only Game Display
- All countries' resources (gold, bonds, territories, goods, people, banks, supporters, revolters)
- Current round number and phase (waiting, development, actions, completed)
- Development and action completion status per player
- Net stability calculation per player

### Leaderboard
- Ranked player list with scores
- Score breakdown (base score, territory bonus, stability bonus)
- Instability penalty indicator

### Real-Time Updates
- WebSocket connection receives game state updates without polling
- Connection status banner with reconnect button
- Round summary with per-player resource deltas shown on round transitions

### Spectator Badge
- Purple "Spectating" badge in the game header
- Spectator count badge (when `spectator_count` is available from the backend)

## No Action Controls
The spectator view intentionally excludes all action buttons:
- No "Start Game" button
- No "Execute Development" button
- No action panel (buy bonds, build banks, recruit people, acquire territory)
- No "Advance to Next Round" button

## Types

The `GameState` interface includes an optional `spectator_count` field:

```typescript
interface GameState {
  game: Game;
  players: SpawnedCountryWithDetails[];
  leaderboard: LeaderboardEntry[];
  spectator_count?: number;
}
```

## API

### POST /games/{game_id}/spectate

Returns a spectator JWT token for watching a game. **No authentication required.**

- Allowed when game phase is `waiting`, `development`, or `actions`
- Returns `400` when game phase is `completed`
- Returns `404` when game does not exist

**Response:**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "is_spectator": true,
  "game_id": 1
}
```

The JWT contains claims: `sub` (spectator-game-{id}), `game_id`, and `is_spectator: true`.

### WebSocket /ws/{game_id}/spectate

Dedicated spectator WebSocket endpoint. Authenticate via query parameter: `/ws/{game_id}/spectate?token=<jwt>`.

- Validates the JWT and checks the `is_spectator` claim — no player database lookup is required (the `sub` is a synthetic identifier, not a real username)
- Spectators receive all game state broadcasts but cannot send action messages
- Only `ping` messages are accepted; all other messages are rejected with a 403 error
- On connect, a `spectator_joined` event with `spectator_count` is broadcast to the game room
- On disconnect, a `spectator_left` event with updated `spectator_count` is broadcast

### GET /games/

Returns all active games with `spectator_count` field. Supports `?games_with_spectators=true` query parameter to filter to games that have at least one connected spectator.

### GET /games/{game_id}

The `GameState` response includes a `spectator_count` field (integer, defaults to 0).

The frontend `gamesAPI.spectateGame(gameId)` method calls the spectate endpoint to obtain the token.

## WebSocket Hook

The `useGameWebSocket` hook accepts an optional `isSpectator` flag:

```typescript
const { gameState, connectionStatus, reconnect } = useGameWebSocket({
  gameId,
  token,
  onMessage: handleWsMessage,
  isSpectator: true,
});
```

## Dependencies

- `task-empires-online-feat-spectator-ui-1`: Types, API method, routing (implemented)
- `task-empires-online-feat-spectator-backend-*`: Backend spectate endpoint and spectator tracking (separate feature)
