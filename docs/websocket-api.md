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

## Frontend Integration

### TypeScript Types

All WebSocket message types are defined in `frontend/src/types/index.ts` as a discriminated union on the `type` field:

- **`WsClientMessage`** — union of messages the client can send (`ping`, `chat`)
- **`WsServerMessage`** — union of messages the server can send (`player_joined`, `player_left`, `pong`, `chat`, `error`, `game_state_update`, `round_changed`)

### Connection Utility

`buildWebSocketUrl(gameId: number)` in `frontend/src/services/api.ts` constructs the WebSocket URL:

- Derives `ws://` or `wss://` from the current page protocol or configured `REACT_APP_API_URL`
- Appends the JWT token from localStorage as a query parameter
- Strips `/api` suffix to hit the root-level `/ws` route

```typescript
import { buildWebSocketUrl } from '../services/api';

const url = buildWebSocketUrl(gameId);
const ws = new WebSocket(url);
```

## Architecture

- **ConnectionManager** (`backend/app/services/ws_manager.py`): Manages active connections organized by game rooms with connect, disconnect, join_room, leave_room, and broadcast_to_room operations.
- **WebSocket Route** (`backend/app/api/routes/ws.py`): Handles the `/ws/{game_id}` endpoint, JWT validation, and message dispatch.
