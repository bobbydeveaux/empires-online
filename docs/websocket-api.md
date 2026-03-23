# WebSocket API

## Endpoints

### Player endpoint

```
WS /ws/{game_id}?token=<jwt>
```

### Spectator endpoint

```
WS /ws/{game_id}/spectate?token=<jwt>
```

## Authentication

Both endpoints require a valid JWT token. Provide it via:

1. **Query parameter** (recommended): `/ws/1?token=eyJhbGci...`
2. **Authorization header**: `Authorization: Bearer eyJhbGci...`

Invalid or missing tokens result in a close with code `1008` (Policy Violation).

## Connection Flow

### Player connection
1. Client connects with a valid JWT token
2. Server validates the token and looks up the player
3. Connection is accepted and added to the game room
4. A `player_joined` message is broadcast to the room
5. Client can send/receive messages
6. On disconnect, a `player_left` message is broadcast

### Spectator connection
1. Client obtains a spectator token via `POST /api/games/{game_id}/spectate`
2. Client connects with the spectator token to the `/spectate` endpoint (contains `is_spectator: true` claim)
3. Connection is accepted and added to the game room as a spectator
4. A `spectator_joined` message (with `spectator_count`) is broadcast to the room
5. Spectator receives all game state broadcasts
6. Only `ping` messages are allowed from spectators; all other messages are rejected with a `403` error
7. On disconnect, a `spectator_left` message (with `spectator_count`) is broadcast

## Message Types

### Client → Server

| Type | Payload | Description |
|------|---------|-------------|
| `ping` | `{}` | Health check; server responds with `pong` (allowed for both players and spectators) |
| `chat` | `{"message": "text"}` | Send a chat message to the game room (players only; rejected with 403 for spectators) |

### Server → Client

#### Connection Events

| Type | Payload | Description |
|------|---------|-------------|
| `player_joined` | `{"game_id", "player": {"id", "username"}}` | A player connected to the WebSocket room |
| `player_left` | `{"game_id", "player": {"id", "username"}}` | A player disconnected from the WebSocket room |
| `spectator_joined` | `{"game_id", "spectator_count"}` | A spectator connected to the game room |
| `spectator_left` | `{"game_id", "spectator_count"}` | A spectator disconnected from the game room |
| `pong` | `{}` | Response to a `ping` |
| `chat` | `{"game_id", "player": {"id", "username"}, "message"}` | Chat message broadcast |
| `error` | `{"message": "...", "code?": number}` | Error response; `code: 403` for spectator action rejections |

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

### Player connection
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

### Spectator connection
```javascript
const token = "eyJhbGci..."; // JWT from /api/auth/token
const ws = new WebSocket(`ws://localhost:3000/ws/1/spectate?token=${token}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "error" && data.code === 403) {
    console.warn("Action rejected:", data.message);
  } else {
    console.log("Game update:", data);
  }
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
- On `game_state_update`, applies the included `game_state` directly (or refetches via REST if absent)
- Refetches state when `player_joined`, `player_left`, or `round_changed` messages arrive
- Implements exponential backoff reconnection (1s, 2s, 4s, ... up to 30s max)
- Does not reconnect on auth failure (close code 1008)
- Sends ping keepalive every 25 seconds
- Cleans up on unmount

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

## Spectator Mode

Spectators can watch in-progress games in real-time without being able to perform any actions.

### Flow

1. From the game lobby, click **Spectate** on an in-progress game card
2. The frontend calls `POST /api/games/{game_id}/spectate` to obtain a spectator JWT token
3. The spectator token is stored in `localStorage` as `spectatorToken:{gameId}`
4. The user is navigated to `/spectate/{gameId}` which renders a read-only `SpectatorView`
5. The `SpectatorView` connects to the same WebSocket endpoint using the spectator token
6. All game state updates are received in real-time, but no action controls are shown

### Spectator Token

The spectator token is a standard JWT with an additional `is_spectator: true` claim and `game_id` field. It is issued by the `POST /games/{game_id}/spectate` endpoint and requires the user to be authenticated.

### SpectatorView Route

- **Route**: `/spectate/:gameId`
- **Component**: `SpectatorView` (`frontend/src/pages/SpectatorView.tsx`)
- **Features**: Read-only game state display, leaderboard, player status, connection status banner

## Architecture

- **ConnectionManager** (`backend/app/services/ws_manager.py`): Manages active connections organized by game rooms, with separate tracking for players and spectators. Supports connect, disconnect, connect_spectator, disconnect_spectator, join_room, join_room_as_spectator, leave_room, broadcast_to_room (reaches both players and spectators), is_spectator, and get_spectator_count. Includes PostgreSQL NOTIFY/LISTEN support for cross-process event fanout.
- **GameBroadcast** (`backend/app/services/game_broadcast.py`): Provides message builders for each game event type (including `game_state_update` with full game state) and an async `broadcast_event()` function used as a FastAPI `BackgroundTask`.
- **WebSocket Route** (`backend/app/api/routes/ws.py`): Handles the `/ws/{game_id}` player endpoint and `/ws/{game_id}/spectate` spectator endpoint. Both require JWT validation. Spectators can only send `ping`; all other messages are rejected with a 403 error.
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
