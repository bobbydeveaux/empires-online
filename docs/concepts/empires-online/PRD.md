

# Product Requirements Document: Empires Online

Empires Online
An online implementation of the classic Empires board game - a strategic economic game where players control historical empires, manage resources, and compete for dominance.

Game Overview

Empires is a turn-based strategy game where players:

Manage economic resources (gold, goods, people, territories)
Balance luxury production vs industrial development
Handle political stability through supporters and revolters
Make strategic banking and bond decisions
Compete over multiple rounds for the highest score
Architecture

This implementation consists of:

Backend: FastAPI-based REST API with PostgreSQL database
Frontend: React TypeScript SPA with real-time updates
Database: PostgreSQL with SQLAlchemy ORM
Deployment: Docker containers with docker-compose

**Created:** 2026-02-27T20:31:24Z
**Status:** Draft

## 1. Overview

**Concept:** Empires Online — a multiplayer turn-based strategy web game implementing the classic Empires board game with real-time updates.

**Description:** The core game engine (development algorithm, victory points, basic actions, auth, lobby, Docker deployment) is already implemented. This PRD covers Phase 2 enhancements: real-time WebSocket communication, completing the full action set, implementing the stability check phase, and improving UX/polish.

---

## 2. Goals

- **G1:** Replace 5-second polling with WebSocket push notifications for sub-second game state updates
- **G2:** Implement all remaining player actions (recruit people, acquire territories) per the DESIGN.md spec
- **G3:** Implement the stability check phase so revolters > supporters triggers resource loss
- **G4:** Deliver a polished, mobile-responsive UI with clear phase progression and player feedback
- **G5:** Achieve ≥80% backend test coverage including integration tests for all API endpoints

---

## 3. Non-Goals

- **NG1:** Trading between players (deferred to Phase 3)
- **NG2:** AI opponents or single-player mode
- **NG3:** Tournament/matchmaking systems
- **NG4:** Diplomatic relations, alliances, or random events
- **NG5:** Technology trees or advanced game variants

---

## 4. User Stories

- **US1:** As a player, I want to see other players' actions in real time so I stay engaged during their turns.
- **US2:** As a player, I want to recruit people and acquire territories so I can grow my empire beyond starting resources.
- **US3:** As a player, I want to see a stability check at end of round so I understand consequences of high revolt.
- **US4:** As a player, I want a responsive game board on mobile so I can play from any device.
- **US5:** As a player, I want visual feedback (animations, toasts) when resources change so I understand what happened.
- **US6:** As a game creator, I want automatic phase transitions when all players complete their actions so the game flows smoothly.
- **US7:** As a player, I want to see a detailed round summary showing all changes before the next round begins.

---

## 5. Acceptance Criteria

**US1 – Real-time Updates:**
- Given a player performs an action, When the server processes it, Then all players in the game see updated state within 500ms without page refresh.
- Given a player disconnects, When they reconnect, Then they receive the current game state automatically.

**US2 – New Actions:**
- Given a player has ≥2 gold, When they recruit 1 person, Then people increases by 1 and gold decreases by 2.
- Given a player has ≥3 gold, When they acquire 1 territory, Then territories increases by 1 and gold decreases by 3.

**US3 – Stability Check:**
- Given revolters > supporters at round end, When the stability check runs, Then the player loses 1 gold per excess revolter (minimum 0 gold).

**US6 – Auto Phase Transitions:**
- Given all players have completed development, When the last player submits, Then the game automatically transitions to the actions phase.

---

## 6. Functional Requirements

- **FR-001:** WebSocket server using FastAPI WebSocket endpoints, with room-based broadcasting per game.
- **FR-002:** Frontend WebSocket client replacing polling in Game.tsx and GameLobby.tsx.
- **FR-003:** `recruit_people` action: costs 2 gold, adds 1 person. Validated via `can_perform_action()`.
- **FR-004:** `acquire_territory` action: costs 3 gold, adds 1 territory. Validated via `can_perform_action()`.
- **FR-005:** Stability check logic in `GameLogic`: if revolters > supporters, deduct gold = (revolters - supporters), floor at 0.
- **FR-006:** Automatic phase transitions: development → actions when all `development_completed=True`; actions → next round (or completed) when all `actions_completed=True`.
- **FR-007:** Round summary endpoint returning per-player changes for the completed round.
- **FR-008:** Mobile-responsive layout using CSS media queries for screen widths ≤768px.
- **FR-009:** Toast notification system for action confirmations and errors.
- **FR-010:** Alembic migration setup for safe schema evolution.

---

## 7. Non-Functional Requirements

### Performance
- WebSocket message delivery ≤500ms end-to-end
- API response times ≤200ms for game state queries
- Support 50 concurrent active games with 6 players each

### Security
- WebSocket connections authenticated via JWT token passed on connection
- All player actions validated server-side (no client-trust)
- Rate limiting: max 30 actions per minute per player

### Scalability
- Stateless backend design allowing horizontal scaling behind a load balancer
- WebSocket connections managed per-process with shared state via PostgreSQL NOTIFY/LISTEN

### Reliability
- Graceful WebSocket reconnection with exponential backoff (1s, 2s, 4s, max 30s)
- Game state persisted to database before broadcasting, ensuring no data loss on crash
- Database connection pooling with health checks

---

## 8. Dependencies

- **FastAPI WebSockets** (built-in) — real-time communication
- **PostgreSQL NOTIFY/LISTEN** — cross-process event broadcasting
- **Alembic 1.12.1** (already in requirements.txt) — database migrations
- **socket.io-client 4.7** (already in package.json) — frontend WebSocket client (or native WebSocket API)
- **React-Toastify or similar** — toast notification UI

---

## 9. Out of Scope

- Player-to-player trading or resource exchange
- In-game chat or messaging system
- Spectator mode for non-players
- Custom game rules or house variants
- Player profiles, statistics, or historical win rates
- Email verification flow (endpoint exists but not enforced)

---

## 10. Success Metrics

- **SM1:** Zero polling requests in active games (all updates via WebSocket)
- **SM2:** All 4 action types (buy_bond, build_bank, recruit_people, acquire_territory) functional with test coverage
- **SM3:** Stability check executes correctly in ≥95% of rounds (validated by integration tests)
- **SM4:** Frontend usable on 375px-width screens without horizontal scrolling
- **SM5:** Backend test coverage ≥80% (measured via pytest-cov)
- **SM6:** Average game completion rate ≥70% (games started vs games reaching "completed" phase)

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers

*No clarification questions were raised — the concept and DESIGN.md provide sufficient specification for Phase 2 requirements.*