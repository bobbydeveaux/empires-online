# WebSocket API

## Endpoint

```
WS /ws/{game_id}?token=<jwt>
```

## Authentication

The WebSocket endpoint requires a valid JWT token. Provide it via:

1. **Query parameter** (recommended): `/ws/1?token=eyJhbGci...`
2. **Authorization header**: `Authorization: Bearer eyJhbGci...`

Invalid or missing tokens result in a close with code `1008` (Policy Violation).

## Connection Flow

1. Client connects with a valid JWT token
2. Server validates the token and looks up the player
3. Connection is accepted and added to the game room
4. A `player_joined` message is broadcast to the room
5. Client can send/receive messages
6. On disconnect, a `player_left` message is broadcast

## Message Types

### Client → Server

| Type | Payload | Description |
|------|---------|-------------|
| `ping` | `{}` | Health check; server responds with `pong` |
| `chat` | `{"message": "text"}` | Send a chat message to the game room |

### Server → Client

| Type | Payload | Description |
|------|---------|-------------|
| `player_joined` | `{"game_id", "player": {"id", "username"}}` | A player connected to the room |
| `player_left` | `{"game_id", "player": {"id", "username"}}` | A player disconnected |
| `pong` | `{}` | Response to a `ping` |
| `chat` | `{"game_id", "player": {"id", "username"}, "message"}` | Chat message broadcast |
| `error` | `{"message": "..."}` | Error response for unknown message types |

## Example (JavaScript)

```javascript
const token = "eyJhbGci..."; // JWT from /api/auth/token
const ws = new WebSocket(`ws://localhost:8000/ws/1?token=${token}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Received:", data);
};

ws.onopen = () => {
  // Send a chat message
  ws.send(JSON.stringify({ type: "chat", message: "Hello!" }));
};
```

### Future Server → Client (reserved)

| Type | Payload | Description |
|------|---------|-------------|
| `game_state_update` | `{"game_id", "game_state?": GameState}` | Full or partial game state push |
| `round_changed` | `{"game_id", "round", "phase"}` | Round/phase transition notification |

## Frontend Integration

### `useGameWebSocket` Hook

The `useGameWebSocket` hook (`frontend/src/hooks/useGameWebSocket.ts`) provides real-time game state updates, replacing the previous 5-second polling mechanism.

```typescript
import { useGameWebSocket } from '../hooks/useGameWebSocket';

const { gameState, connectionStatus, reconnect, refreshGameState } = useGameWebSocket({
  gameId: 1,
  token: 'jwt-token',
  onMessage: (msg) => console.log(msg),
});
```

**Returns:**
- `gameState` — Current `GameState` object (fetched via REST, kept in sync by WS events)
- `connectionStatus` — `'connecting' | 'connected' | 'disconnected' | 'reconnecting'`
- `reconnect()` — Manually trigger a reconnect
- `refreshGameState()` — Manually fetch fresh state via REST

**Behavior:**
- Connects to `WS /ws/{gameId}?token=<jwt>` on mount
- Fetches full game state via REST on connect and reconnect
- Refetches state when `player_joined`, `player_left`, `round_changed`, or `game_state_update` messages arrive
- Implements exponential backoff reconnection (1s, 2s, 4s, ... up to 30s max)
- Does not reconnect on auth failure (close code 1008)
- Sends ping keepalive every 25 seconds
- Cleans up on unmount

### `getWebSocketUrl` Utility

```typescript
import { getWebSocketUrl } from '../services/api';

const url = getWebSocketUrl(gameId, token);
// Returns: ws://host/ws/{gameId}?token={token}
// Or: wss://host/ws/{gameId}?token={token} (when on HTTPS)
```

Respects `REACT_APP_WS_URL` environment variable if set.

### Connection Status Banner

Both `Game.tsx` and `GameLobby.tsx` display a visual connection status indicator:
- **Yellow banner** when connecting or reconnecting
- **Red banner** with a reconnect button when disconnected
- **Hidden** when connected (normal state)

## Architecture

- **ConnectionManager** (`backend/app/services/ws_manager.py`): Manages active connections organized by game rooms with connect, disconnect, join_room, leave_room, and broadcast_to_room operations.
- **WebSocket Route** (`backend/app/api/routes/ws.py`): Handles the `/ws/{game_id}` endpoint, JWT validation, and message dispatch.
- **useGameWebSocket** (`frontend/src/hooks/useGameWebSocket.ts`): React hook that manages WebSocket lifecycle, reconnection, and state synchronization.
- **WebSocket Types** (`frontend/src/types/index.ts`): TypeScript discriminated union types for all WebSocket messages (`WsServerMessage`).
