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

#### Connection Events

| Type | Payload | Description |
|------|---------|-------------|
| `player_joined` | `{"game_id", "player": {"id", "username"}}` | A player connected to the WebSocket room |
| `player_left` | `{"game_id", "player": {"id", "username"}}` | A player disconnected from the WebSocket room |
| `pong` | `{}` | Response to a `ping` |
| `chat` | `{"game_id", "player": {"id", "username"}, "message"}` | Chat message broadcast |
| `error` | `{"message": "..."}` | Error response for unknown message types |

#### Game State Events

These messages are broadcast from REST endpoints when game state changes occur, enabling real-time updates without polling.

| Type | Payload | Description |
|------|---------|-------------|
| `player_joined_game` | `{"game_id", "player": {"id", "username"}, "country_name"}` | A player joined the game (via REST `/join`) |
| `game_started` | `{"game_id", "phase"}` | The game was started by the creator |
| `development_completed` | `{"game_id", "player": {"id", "username"}, "completed_count", "total_count"}` | A player completed their development phase |
| `phase_changed` | `{"game_id", "phase"}` | The game phase transitioned (e.g., development → actions) |
| `action_performed` | `{"game_id", "player": {"id", "username"}, "action", "quantity"}` | A player performed an action (buy_bond, build_bank, recruit_people, acquire_territory) |
| `actions_completed` | `{"game_id", "player": {"id", "username"}, "completed_count", "total_count"}` | A player ended their actions phase |
| `stability_check` | `{"game_id", "results": [{"player_id", "player_name", "country_name", "stable", "gold_lost", ...}]}` | Stability check results at end of round |
| `round_summary` | `{"game_id", "round", "summary": [{"player_id", "player_name", "country_name", "actions": [...]}]}` | Per-player summary of all actions taken during the round |
| `round_advanced` | `{"game_id", "round", "phase"}` | The game advanced to a new round |
| `game_completed` | `{"game_id", "leaderboard": [...]}` | The game ended; includes the final leaderboard |
| `game_state_update` | `{"game_id", "game_state?": GameState}` | Full game state push after actions and phase transitions |

#### Reserved / Future Server → Client

| Type | Payload | Description |
|------|---------|-------------|
| `round_changed` | `{"game_id", "round", "phase"}` | Round/phase transition notification |

## Example (JavaScript)

```javascript
const token = "eyJhbGci..."; // JWT from /api/auth/token
// Via Nginx proxy (recommended)
const ws = new WebSocket(`ws://localhost:3000/ws/1?token=${token}`);
// Direct backend (development only)
// const ws = new WebSocket(`ws://localhost:8000/ws/1?token=${token}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Received:", data);
};

ws.onopen = () => {
  // Send a chat message
  ws.send(JSON.stringify({ type: "chat", message: "Hello!" }));
};
```

## Frontend Integration

### TypeScript Types

All WebSocket message types are defined in `frontend/src/types/index.ts` as a discriminated union on the `type` field:

- **`WsClientMessage`** — union of messages the client can send (`ping`, `chat`)
- **`WsServerMessage`** — union of messages the server can send (`player_joined`, `player_left`, `pong`, `chat`, `error`, `game_state_update`, `round_changed`)

### `useGameWebSocket` Hook

The `useGameWebSocket` hook (`frontend/src/hooks/useGameWebSocket.ts`) provides real-time game state updates, replacing the previous 5-second polling mechanism.

```typescript
import { useGameWebSocket } from '../hooks/useGameWebSocket';

const { gameState, connectionStatus, reconnect, refreshGameState, sendMessage, isSpectator } = useGameWebSocket({
  gameId: 1,
  token: 'jwt-token',
  onMessage: (msg) => console.log(msg),
  isSpectator: false, // optional, defaults to false
});
```

**Returns:**
- `gameState` — Current `GameState` object (fetched via REST, kept in sync by WS events)
- `connectionStatus` — `'connecting' | 'connected' | 'disconnected' | 'reconnecting'`
- `reconnect()` — Manually trigger a reconnect
- `refreshGameState()` — Manually fetch fresh state via REST
- `sendMessage(msg)` — Send a `WsClientMessage` over the WebSocket. Returns `false` if in spectator mode or not connected.
- `isSpectator` — Whether this connection is in spectator (read-only) mode

**Behavior:**
- Connects to `WS /ws/{gameId}?token=<jwt>` on mount
- Fetches full game state via REST on connect and reconnect
- On `game_state_update`, applies the included `game_state` directly (or refetches via REST if absent)
- Refetches state when `player_joined`, `player_left`, or `round_changed` messages arrive
- Implements exponential backoff reconnection (1s, 2s, 4s, ... up to 30s max)
- Does not reconnect on auth failure (close code 1008)
- Sends ping keepalive every 25 seconds
- Cleans up on unmount
- **Spectator mode**: When `isSpectator` is `true`, `sendMessage()` always returns `false` and no outbound messages are sent

### Spectator Mode

Spectators can watch a game in real-time without participating:

1. Call `POST /games/{gameId}/spectate` to get a spectator token
2. Connect to the WebSocket using the spectator token
3. The `useGameWebSocket` hook with `isSpectator: true` prevents sending action messages

**Route:** `/spectate/:gameId` — Protected route that renders a read-only game view.

**API:** `gamesAPI.spectateGame(gameId)` — Returns `{ spectator_token, game_id }`.

**Types:**
- `GameState.spectator_count` — Optional field indicating how many spectators are watching
- `SpectateTokenResponse` — Response type from the spectate endpoint

### WebSocket URL Utilities

**`getWebSocketUrl`** — Used by `useGameWebSocket`, accepts explicit token:

```typescript
import { getWebSocketUrl } from '../services/api';

const url = getWebSocketUrl(gameId, token);
// Returns: ws://host/ws/{gameId}?token={token}
// Or: wss://host/ws/{gameId}?token={token} (when on HTTPS)
```

**`buildWebSocketUrl`** — Reads JWT from localStorage automatically:

```typescript
import { buildWebSocketUrl } from '../services/api';

const url = buildWebSocketUrl(gameId);
const ws = new WebSocket(url);
```

Both utilities derive `ws://` or `wss://` from the current page protocol (or configured `REACT_APP_API_URL` / `REACT_APP_WS_URL`) and strip the `/api` suffix to hit the root-level `/ws` route.

### Connection Status Banner

Both `Game.tsx` and `GameLobby.tsx` display a visual connection status indicator:
- **Yellow banner** when connecting or reconnecting
- **Red banner** with a reconnect button when disconnected
- **Hidden** when connected (normal state)

## Architecture

- **ConnectionManager** (`backend/app/services/ws_manager.py`): Manages active connections organized by game rooms with connect, disconnect, join_room, leave_room, and broadcast_to_room operations. Includes PostgreSQL NOTIFY/LISTEN support for cross-process event fanout.
- **GameBroadcast** (`backend/app/services/game_broadcast.py`): Provides message builders for each game event type (including `game_state_update` with full game state) and an async `broadcast_event()` function used as a FastAPI `BackgroundTask`.
- **WebSocket Route** (`backend/app/api/routes/ws.py`): Handles the `/ws/{game_id}` endpoint, JWT validation, and message dispatch.
- **Game REST Routes** (`backend/app/api/routes/games.py`): State-changing endpoints (join, start, develop, actions, end-actions, next-round) broadcast game events via `BackgroundTasks` after committing database changes. The end-actions endpoint triggers auto phase transitions when all players complete.
- **useGameWebSocket** (`frontend/src/hooks/useGameWebSocket.ts`): React hook that manages WebSocket lifecycle, reconnection, and state synchronization.
- **WebSocket Types** (`frontend/src/types/index.ts`): TypeScript discriminated union types for all WebSocket messages (`WsServerMessage`).
- **Nginx Proxy** (`frontend/nginx.conf`): Proxies `/ws/` to the backend with WebSocket upgrade headers and a 24-hour `proxy_read_timeout` to support long-lived connections.

### Broadcasting Flow

1. Client calls a REST endpoint (e.g., `POST /api/games/{id}/start`)
2. The endpoint processes the request and commits database changes
3. Event-specific broadcast tasks are added (e.g., `game_started`, `action_performed`)
4. A `game_state_update` broadcast with full game state is added so clients can refresh their UI
5. The REST response is returned to the caller
6. Background tasks send WebSocket messages to all clients in the game room

### Cross-Process Event Fanout (PostgreSQL NOTIFY/LISTEN)

When running multiple backend processes (e.g. behind a load balancer), game state changes must be broadcast to all WebSocket connections regardless of which process they are connected to. The `ConnectionManager` achieves this using PostgreSQL's built-in NOTIFY/LISTEN mechanism:

1. **On startup**, the manager creates:
   - A dedicated `asyncpg` connection that `LISTEN`s on the `game_events` channel
   - A connection pool for issuing `NOTIFY` commands

2. **Publishing events**: Game endpoints call `manager.notify(game_id, message)` which sends a `pg_notify('game_events', payload)` where the payload is JSON containing `game_id` and the message body.

3. **Receiving events**: The LISTEN connection receives notifications and the callback parses the payload, then broadcasts to all local WebSocket connections in the relevant game room.

4. **Fallback**: If PostgreSQL is unavailable (e.g. in tests), `notify()` falls back to a direct local broadcast.

```
┌─────────────┐     NOTIFY      ┌──────────────┐
│  Backend 1  │ ──────────────► │  PostgreSQL   │
│  (REST API) │                 │  game_events  │
└─────────────┘                 └──────┬───────┘
                                       │ LISTEN
                        ┌──────────────┼──────────────┐
                        ▼              ▼              ▼
                  ┌───────────┐  ┌───────────┐  ┌───────────┐
                  │ Backend 1 │  │ Backend 2 │  │ Backend N │
                  │ WebSocket │  │ WebSocket │  │ WebSocket │
                  │ clients   │  │ clients   │  │ clients   │
                  └───────────┘  └───────────┘  └───────────┘
```
