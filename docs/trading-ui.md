# Trading UI Components

The trading system allows players to propose, accept, reject, and cancel resource trades with other players during active game phases.

## Components

### TradePanel (`frontend/src/components/TradePanel.tsx`)

Displays all pending trade offers for the current player, split into two sections:

- **Incoming Offers**: Trades proposed by other players where the current player is the receiver. Shows Accept and Reject buttons.
- **Outgoing Offers**: Trades proposed by the current player. Shows a Cancel button.

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `gameId` | `number` | Current game ID |
| `trades` | `TradeOffer[]` | List of pending trade offers |
| `currentPlayer` | `SpawnedCountryWithDetails` | The current player's country |
| `players` | `SpawnedCountryWithDetails[]` | All players in the game |
| `onTradeUpdate` | `() => void` | Callback to refresh trade list |
| `onOpenPropose` | `() => void` | Callback to open the ProposeTrade modal |
| `onToast` | `(message, type) => void` | Callback for toast notifications |

### ProposeTrade (`frontend/src/components/ProposeTrade.tsx`)

A modal dialog for creating new trade proposals. Features:

- **Player selector**: Dropdown to choose which player to trade with (excludes current player)
- **Offer sliders**: Range inputs for gold, people, and territory the player offers. Max values are capped to the player's current resources.
- **Request sliders**: Range inputs for gold, people, and territory the player requests. Max set to 999 (validated server-side).

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `gameId` | `number` | Current game ID |
| `currentPlayer` | `SpawnedCountryWithDetails` | The current player's country |
| `players` | `SpawnedCountryWithDetails[]` | All players in the game |
| `onClose` | `() => void` | Close the modal |
| `onTradeProposed` | `() => void` | Callback after successful proposal |
| `onToast` | `(message, type) => void` | Callback for toast notifications |

## Types

Defined in `frontend/src/types/index.ts`:

- **`TradeOffer`**: Full trade record with IDs, resource amounts, status, and timestamps
- **`TradePropose`**: Input payload for proposing a new trade
- **`TradeResource`**: Resource amounts (gold, people, territory)
- **`TradeStatus`**: `'pending' | 'accepted' | 'rejected'`

## API Functions

Defined in `frontend/src/services/api.ts` under `gamesAPI`:

| Function | Method | Endpoint |
|----------|--------|----------|
| `listTrades(gameId)` | GET | `/games/{gameId}/trades` |
| `proposeTrade(gameId, proposal)` | POST | `/games/{gameId}/trades` |
| `acceptTrade(gameId, tradeId)` | POST | `/games/{gameId}/trades/{tradeId}/accept` |
| `rejectTrade(gameId, tradeId)` | POST | `/games/{gameId}/trades/{tradeId}/reject` |
| `cancelTrade(gameId, tradeId)` | POST | `/games/{gameId}/trades/{tradeId}/reject` |

## CSS Classes

Styles are in `frontend/src/App.css`:

- `.trade-item` / `.trade-incoming` / `.trade-outgoing` — Trade list items with color-coded backgrounds
- `.trade-modal-overlay` / `.trade-modal` — Modal overlay and container
- `.trade-slider-section` — Resource slider grouping
