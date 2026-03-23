# Trading API

## Overview

Players can propose, accept, reject, and cancel resource trades with other players in the same game. Trading is available during active game phases.

## REST Endpoints

All endpoints require JWT authentication via the `Authorization: Bearer <token>` header.

### Propose a Trade

```
POST /api/games/{game_id}/trades
```

**Request Body:**
```json
{
  "receiver_country_id": 2,
  "offer_gold": 100,
  "offer_people": 0,
  "offer_territory": 0,
  "request_gold": 0,
  "request_people": 50,
  "request_territory": 0
}
```

**Response:** `TradeOffer` object with status `"pending"`.

### List Pending Trades

```
GET /api/games/{game_id}/trades
```

**Response:** Array of `TradeOffer` objects with status `"pending"`.

### Accept a Trade

```
POST /api/games/{game_id}/trades/{trade_id}/accept
```

**Response:** `TradeOffer` object with status `"accepted"`. Resources are atomically transferred between both parties.

### Reject a Trade

```
POST /api/games/{game_id}/trades/{trade_id}/reject
```

**Response:** `TradeOffer` object with status `"rejected"`.

### Cancel a Trade

```
POST /api/games/{game_id}/trades/{trade_id}/cancel
```

**Response:** `TradeOffer` object with status `"cancelled"`. Only the proposer can cancel their own trade.

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
  offer_gold: 100,
  offer_people: 0,
  offer_territory: 0,
  request_gold: 0,
  request_people: 50,
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

Trade actions trigger WebSocket broadcasts to all players in the game:

- **`trade_proposed`** — Sent when a new trade is proposed. Payload includes the full `TradeOffer`.
- **`trade_resolved`** — Sent when a trade is accepted, rejected, or cancelled. Check `trade.status` for the outcome.

See [WebSocket API docs](websocket-api.md) for the full message type reference.
