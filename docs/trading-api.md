# Trading API

## Overview

Players can propose, accept, reject, and cancel resource trades with other players in the same game. Trading is available during the **actions** phase of a game.

## Endpoints

All trading endpoints are nested under `/api/games/{game_id}/trades` and require JWT authentication via the `Authorization: Bearer <token>` header.

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

**Response:** `TradeOffer` object with status `"accepted"`.

### POST /api/games/{game_id}/trades/{trade_id}/reject — Reject a Trade

Reject a pending trade. Only the **receiver** can reject. No resources are exchanged.

**Response:** `TradeOffer` object with status `"rejected"`.

### POST /api/games/{game_id}/trades/{trade_id}/cancel — Cancel a Trade

Cancel a pending trade. Only the **proposer** can cancel their own trade.

**Response:** `TradeOffer` object with status `"cancelled"`.

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

## GameState `trade_allowed` Flag

The `GameState` schema (returned by `GET /api/games/{game_id}` and included in `game_state_update` WebSocket broadcasts) contains a `trade_allowed` boolean field:

- **`true`** — the game is in the `actions` phase and players may propose, accept, or reject trades
- **`false`** — the game is in any other phase (`waiting`, `development`, `completed`) and trading is disabled

Frontend clients should use this flag to show or hide the trading UI.

## TypeScript Types

Defined in `frontend/src/types/index.ts`:

- **`TradeStatus`** — `'pending' | 'accepted' | 'rejected' | 'cancelled'`
- **`TradeResource`** — Object with `gold`, `people`, and `territory` fields
- **`TradeOffer`** — Full trade object with proposer/receiver IDs, offer/request amounts, status, and timestamps
- **`TradePropose`** — Input type for proposing a new trade (receiver ID + resource amounts)

## Frontend API Service

The `tradesAPI` object in `frontend/src/services/api.ts` provides:

```typescript
import { tradesAPI } from '../services/api';

// Propose a trade
const trade = await tradesAPI.proposeTrade(gameId, {
  receiver_country_id: 2,
  offer_gold: 3,
  offer_people: 0,
  offer_territory: 1,
  request_gold: 0,
  request_people: 2,
  request_territory: 0,
});

// List pending trades
const trades = await tradesAPI.listTrades(gameId);

// Accept / reject / cancel
await tradesAPI.acceptTrade(gameId, tradeId);
await tradesAPI.rejectTrade(gameId, tradeId);
await tradesAPI.cancelTrade(gameId, tradeId);
```

## WebSocket Events

Trade actions broadcast events to all players in the game:

| Event Type | Trigger | Payload |
|---|---|---|
| `trade_proposed` | New trade created | `game_id`, `trade` (full `TradeOffer`) |
| `trade_resolved` | Trade accepted, rejected, or cancelled | `game_id`, `trade` (full `TradeOffer`), `resolution` |

See [WebSocket API docs](websocket-api.md) for the full message type reference.

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
