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

The `gamesAPI.spectateGame(gameId)` method calls `POST /games/{gameId}/spectate` to obtain a spectator token. This endpoint requires backend support from the spectator-backend feature.

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
