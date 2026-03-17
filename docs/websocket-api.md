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

- **ConnectionManager** (`backend/app/services/ws_manager.py`): Manages active connections organized by game rooms with connect, disconnect, join_room, leave_room, and broadcast_to_room operations. Includes PostgreSQL NOTIFY/LISTEN support for cross-process event fanout.
- **WebSocket Route** (`backend/app/api/routes/ws.py`): Handles the `/ws/{game_id}` endpoint, JWT validation, and message dispatch.
- **Nginx Proxy** (`frontend/nginx.conf`): Proxies `/ws/` to the backend with WebSocket upgrade headers and a 24-hour `proxy_read_timeout` to support long-lived connections.

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
