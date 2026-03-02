# WebSocket Connection Manager

## Overview

The `ConnectionManager` (`backend/app/services/ws_manager.py`) provides real-time WebSocket communication for Empires Online. It organizes connections into game rooms and supports cross-process message fanout via PostgreSQL NOTIFY/LISTEN.

## Architecture

```
Client A ──┐                         ┌── Client C
            ├── Worker Process 1 ──┐ │
Client B ──┘     (ConnectionManager)│ │
                                    ├─── PostgreSQL NOTIFY/LISTEN
Client D ──┐     (ConnectionManager)│     (game_events channel)
            ├── Worker Process 2 ──┘
Client E ──┘
```

Each worker process maintains its own `ConnectionManager` instance tracking local WebSocket connections. PostgreSQL NOTIFY/LISTEN bridges messages across processes so a broadcast in one worker reaches clients connected to other workers.

## API Reference

### `ConnectionManager`

#### Connection Lifecycle

- **`connect(websocket)`** - Accept and register a new WebSocket connection.
- **`disconnect(websocket)`** - Remove a connection from all rooms and clean up tracking state.

#### Room Management

- **`join_room(websocket, room_id)`** - Add a connection to a game room. The connection must be registered via `connect()` first.
- **`leave_room(websocket, room_id)`** - Remove a connection from a room. Empty rooms are automatically cleaned up.

#### Broadcasting

- **`broadcast_to_room(room_id, message)`** - Send a JSON message to all connections in a room. Stale connections are automatically removed.

#### Room Queries

- **`get_room_connections(room_id)`** - Returns a copy of the connections set for a room.
- **`get_connection_count(room_id)`** - Returns the number of connections in a room.

### PostgreSQL NOTIFY/LISTEN

- **`start_pg_listener()`** - Start the background listener on the `game_events` channel. Call this on application startup.
- **`stop_pg_listener()`** - Stop the background listener. Call this on application shutdown.
- **`pg_notify(room_id, event_type, data)`** - Static method to publish a notification. Other services use this to broadcast events across all worker processes.

#### Notification Payload Format

```json
{
  "room": "<game_id>",
  "type": "<event_type>",
  "data": { ... }
}
```

## Usage

### Singleton Instance

A singleton `manager` instance is exported from the module:

```python
from app.services.ws_manager import manager
```

### Startup/Shutdown Integration

```python
@app.on_event("startup")
async def startup():
    await manager.start_pg_listener()

@app.on_event("shutdown")
async def shutdown():
    await manager.stop_pg_listener()
```

### Broadcasting from Game Logic

```python
from app.services.ws_manager import ConnectionManager

await ConnectionManager.pg_notify(
    room_id=str(game_id),
    event_type="game_update",
    data={"phase": "development", "round": 3}
)
```

## Testing

```bash
cd backend
python -m pytest app/tests/test_ws_manager.py -v
```

Tests cover:
- Connection lifecycle (connect, disconnect, cleanup)
- Room management (join, leave, multiple rooms)
- Broadcast targeting and stale connection cleanup
- PostgreSQL notification handling and listener management
