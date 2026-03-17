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
| `action_performed` | `{"game_id", "player": {"id", "username"}, "action", "quantity"}` | A player performed an action (buy_bond, build_bank) |
| `round_advanced` | `{"game_id", "round", "phase"}` | The game advanced to a new round |
| `game_completed` | `{"game_id", "leaderboard": [...]}` | The game ended; includes the final leaderboard |

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

## Architecture

- **ConnectionManager** (`backend/app/services/ws_manager.py`): Manages active connections organized by game rooms with connect, disconnect, join_room, leave_room, and broadcast_to_room operations.
- **GameBroadcast** (`backend/app/services/game_broadcast.py`): Provides message builders for each game event type and a `broadcast_event()` function that schedules broadcasts as FastAPI `BackgroundTasks` from synchronous REST handlers.
- **WebSocket Route** (`backend/app/api/routes/ws.py`): Handles the `/ws/{game_id}` endpoint, JWT validation, and message dispatch.
- **Game REST Routes** (`backend/app/api/routes/games.py`): State-changing endpoints (join, start, develop, actions, next-round) broadcast game events via `BackgroundTasks` after committing database changes.
- **Nginx Proxy** (`frontend/nginx.conf`): Proxies `/ws/` to the backend with WebSocket upgrade headers and a 24-hour `proxy_read_timeout` to support long-lived connections.

### Broadcasting Flow

1. Client calls a REST endpoint (e.g., `POST /api/games/{id}/start`)
2. The endpoint processes the request and commits database changes
3. A broadcast task is added to FastAPI's `BackgroundTasks`
4. The REST response is returned to the caller
5. The background task sends a WebSocket message to all clients in the game room
