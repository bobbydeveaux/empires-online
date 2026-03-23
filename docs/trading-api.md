# Trading API

The trading system allows players to propose, accept, and reject resource trades during the **actions** phase of a game.

## Endpoints

All trading endpoints are nested under `/api/games/{game_id}/trades` and require JWT authentication.

### POST /api/games/{game_id}/trades — Propose a Trade

Create a new trade proposal. The authenticated user must be a player in the game.

**Request Body:**
```json
{
  "receiver_country_id": 2,
  "offer_gold": 3,
  "offer_people": 0,
  "offer_territory": 1,
  "request_gold": 0,
  "request_people": 2,
  "request_territory": 0
}
```

**Validation rules:**
- Game must be in `actions` phase
- Cannot trade with yourself
- Must offer or request at least one resource
- Cannot offer more resources than you currently have
- Amounts cannot be negative
- Both proposer and receiver must be players in the same game

**Response (200):**
```json
{
  "id": 1,
  "game_id": 1,
  "proposer_country_id": 1,
  "receiver_country_id": 2,
  "offer_gold": 3,
  "offer_people": 0,
  "offer_territory": 1,
  "request_gold": 0,
  "request_people": 2,
  "request_territory": 0,
  "status": "pending",
  "created_at": "2026-03-23T12:00:00Z"
}
```

### POST /api/games/{game_id}/trades/{trade_id}/accept — Accept a Trade

Accept a pending trade. Only the **receiver** can accept. Resources are transferred atomically.

**Resource transfer on acceptance:**
- Proposer loses offered resources, gains requested resources
- Receiver loses requested resources, gains offered resources

**Validation:**
- Trade must be `pending`
- Game must still be in `actions` phase
- Proposer must still have enough resources to fulfill the offer
- Receiver must have enough resources to fulfill the request

### POST /api/games/{game_id}/trades/{trade_id}/reject — Reject a Trade

Reject a pending trade. Only the **receiver** can reject. No resources are exchanged.

### GET /api/games/{game_id}/trades — List Pending Trades

Returns all pending (unresolved) trades for the given game.

**Response (200):**
```json
{
  "trades": [
    {
      "id": 1,
      "game_id": 1,
      "proposer_country_id": 1,
      "receiver_country_id": 2,
      "offer_gold": 3,
      "request_people": 2,
      "status": "pending",
      "...": "..."
    }
  ]
}
```

## WebSocket Events

Trade actions broadcast events to all players in the game:

| Event Type | Trigger | Payload |
|---|---|---|
| `trade_proposed` | New trade created | `game_id`, `trade_id`, `proposer_country_id`, `receiver_country_id` |
| `trade_accepted` | Trade accepted | `game_id`, `trade_id`, `proposer_country_id`, `receiver_country_id` |
| `trade_rejected` | Trade rejected | `game_id`, `trade_id`, `proposer_country_id`, `receiver_country_id` |

## Database Schema

The `trades` table stores all trade proposals:

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment |
| `game_id` | Integer (FK → games) | The game this trade belongs to |
| `proposer_country_id` | Integer (FK → spawned_countries) | Who proposed the trade |
| `receiver_country_id` | Integer (FK → spawned_countries) | Who the trade is offered to |
| `offer_gold` | Integer | Gold offered |
| `offer_people` | Integer | People offered |
| `offer_territory` | Integer | Territories offered |
| `request_gold` | Integer | Gold requested |
| `request_people` | Integer | People requested |
| `request_territory` | Integer | Territories requested |
| `status` | String | `pending`, `accepted`, `rejected`, `cancelled` |
| `created_at` | DateTime | Timestamp |

A database constraint prevents self-trades (`proposer_country_id != receiver_country_id`).
