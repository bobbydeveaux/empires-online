Good. Here is the completed ROAM analysis:

# ROAM Analysis: empires-online

**Feature Count:** 6
**Created:** 2026-02-27T20:44:20Z

## Risks

<!-- AI: Identify 5-10 project risks with severity (High/Medium/Low) -->

1. **WebSocket + PostgreSQL NOTIFY/LISTEN Reliability Under Load** (High): The architecture relies on PostgreSQL NOTIFY/LISTEN for cross-process WebSocket fan-out. NOTIFY messages are not queued — if a backend process is not actively listening (e.g., during restart or connection pool cycling), messages are silently dropped. With 50 concurrent games × 6 players, a missed NOTIFY means stale state for some clients until the next action triggers a broadcast.

2. **In-Memory WebSocket State Loss on Process Restart** (High): The `ConnectionManager` holds all active WebSocket connections in a Python dict in-process memory. Any backend restart (deploy, crash, Uvicorn worker recycle) drops all connections simultaneously. With `--reload` enabled in `start.sh`, this happens on every code change during development and could happen in production if the flag isn't removed.

3. **Alembic Migration on Startup Race Condition** (Medium): The plan calls for auto-running Alembic migrations in `start.sh` before Uvicorn starts. If multiple backend containers start simultaneously (horizontal scaling), concurrent migration execution can cause duplicate DDL errors or table lock contention on PostgreSQL, potentially corrupting the migration state in `alembic_version`.

4. **socket.io-client vs Native WebSocket Mismatch** (Medium): The frontend has `socket.io-client@4.7` installed in `package.json`, but the HLD chose native WebSocket over Socket.IO on the backend. Socket.IO client cannot connect to a plain WebSocket endpoint — it uses a custom protocol with handshake, heartbeat, and packet framing. If developers mistakenly use the installed `socket.io-client`, connections will fail silently or produce cryptic errors.

5. **Polling-to-WebSocket Migration Creates Dual State Sources** (Medium): During development, `Game.tsx` will need to transition from its 5-second `setInterval` polling to the `useGameWebSocket` hook. If both coexist temporarily (e.g., partial feature flag, incomplete migration), the component will receive state from two sources — HTTP responses and WebSocket pushes — causing race conditions, redundant renders, and potential UI inconsistency.

6. **Stability Check Ordering with Auto Phase Transitions** (Medium): The stability check must run at round end (after actions phase), but auto phase transitions also trigger at that boundary. The LLD doesn't specify whether stability check runs before or after the phase transition to the next round. If the transition fires first and increments the round counter before the stability check runs, gold deductions would apply to the wrong round's state.

7. **No WebSocket Rate Limiting Implementation Path** (Low): The PRD requires max 30 actions per minute per player, but the LLD doesn't specify where rate limiting is enforced for WebSocket-triggered actions. REST endpoints can use middleware, but WebSocket messages bypass FastAPI's dependency injection pipeline, requiring custom per-connection tracking in the `ConnectionManager`.

---

## Obstacles

<!-- AI: Current blockers or challenges (technical, resource, dependency) -->

- **Alembic not initialized despite being a dependency**: `alembic==1.12.1` is in `requirements.txt` but no `alembic/` directory, `alembic.ini`, or migration files exist. The `empires-online-feat-actions-stability` feature depends on `empires-online-feat-alembic-setup` for the `stability_checked` column, making Alembic setup a hard prerequisite before any game logic work can begin.

- **Nginx lacks WebSocket proxy configuration**: The current `nginx.conf` (26 lines) has no `Upgrade` or `Connection` header forwarding, no `proxy_http_version 1.1`, and no extended read/send timeouts. WebSocket connections through Nginx will fail with HTTP 400 until this is updated, blocking all integration testing of the real-time stack.

- **Backend runs in development mode in Docker**: `start.sh` unconditionally runs `uvicorn ... --reload`, which uses a file watcher that restarts the process on any file change. This is incompatible with persistent WebSocket connections (every restart drops all connections) and masks production behavior. There is no environment-based conditional to disable `--reload`.

- **Test infrastructure gaps**: Only unit tests exist (`test_game_logic.py`, 17 cases). There are no integration tests for API endpoints, no test database configuration, no fixtures for multi-player game scenarios, and no WebSocket test utilities. The 80% coverage target (SM5) requires building the entire test harness from scratch — `httpx` and `pytest-asyncio` are installed but have no test files using them.

---

## Assumptions

<!-- AI: Key assumptions the plan depends on -->

1. **PostgreSQL NOTIFY/LISTEN is sufficient for the 50-game concurrency target**: The architecture avoids Redis by using PG NOTIFY for cross-process broadcasting. This assumes NOTIFY payload size (8000 bytes) is adequate for game state diffs, and that a single PostgreSQL instance can handle the NOTIFY throughput (~300 concurrent listeners × message frequency) without impacting query performance. **Validation:** Load test with 50 simulated games using `locust` or `k6` before committing to this path; measure NOTIFY latency and DB CPU impact.

2. **Native WebSocket API provides adequate browser compatibility**: The HLD chose native `WebSocket` over Socket.IO, which means no automatic fallback to HTTP long-polling for environments where WebSocket is blocked (corporate proxies, certain mobile networks). **Validation:** Confirm target user base doesn't require proxy traversal; all modern browsers support WebSocket natively, but network-level blocking is the real concern.

3. **Single Uvicorn process is the production deployment model**: The `ConnectionManager` stores WebSocket connections in-process memory, and PG NOTIFY/LISTEN handles cross-process fan-out. This assumes the initial deployment uses a single Uvicorn worker. If `--workers N` is used, each worker needs its own LISTEN connection and connection manager instance. **Validation:** Confirm `start.sh` and `Dockerfile` run a single worker; document the scaling model for future multi-worker deployment.

4. **Game state broadcasts can send full state (not deltas)**: The WebSocket design broadcasts the complete game state on every change rather than computing and sending diffs. This assumes game state JSON payloads remain small enough (~2-5 KB per game with 6 players) that full-state broadcast is cheaper than implementing delta logic. **Validation:** Measure serialized game state size with a full 10-round, 6-player game; confirm it stays under the PG NOTIFY 8000-byte limit.

5. **Alembic auto-migration on startup is safe for this deployment**: Running `alembic upgrade head` in `start.sh` assumes single-instance deployment where only one process runs migrations. **Validation:** If multi-container deployment is planned, add a migration lock or use a separate init container.

---

## Mitigations

<!-- AI: For each risk, propose mitigation strategies -->

### Risk 1: PG NOTIFY/LISTEN Reliability
- Add a **catch-up mechanism**: after processing each NOTIFY, compare the game's `updated_at` timestamp against the last broadcast version. If they diverge, fetch and re-broadcast current state.
- Implement a **client-side heartbeat** (every 15s) that triggers a state re-fetch if no WebSocket message has been received, acting as a safety net for missed NOTIFY events.
- Set `idle_in_transaction_session_timeout` on the LISTEN connection to prevent stale connections that silently stop receiving notifications.

### Risk 2: In-Memory WebSocket State Loss
- Implement **reconnection with state sync** in the `useGameWebSocket` hook: on WebSocket `onopen` (including reconnection), immediately request full game state via REST API before processing further WebSocket messages.
- Remove `--reload` from `start.sh` and add a conditional: `if [ "$ENV" = "development" ]; then uvicorn ... --reload; else uvicorn ...; fi`.
- Add a **graceful shutdown handler** in `ConnectionManager` that sends a close frame with code 1012 (Service Restart) so clients know to reconnect immediately rather than waiting for timeout.

### Risk 3: Concurrent Migration Execution
- Use a **PostgreSQL advisory lock** in `alembic/env.py` (`SELECT pg_advisory_lock(12345)`) before running migrations, ensuring only one process migrates at a time.
- Alternatively, run migrations in a **separate init container** in `docker-compose.yml` that completes before the backend service starts (using `depends_on` with a health check).

### Risk 4: socket.io-client vs Native WebSocket
- **Remove `socket.io-client`** from `package.json` during the `empires-online-feat-websocket-frontend` feature implementation to prevent accidental usage.
- Add a code comment in `useGameWebSocket.ts` header documenting the architectural decision: native WebSocket chosen per ADR in HLD, Socket.IO not used.

### Risk 5: Dual State Sources During Migration
- Implement an **atomic cutover** in `Game.tsx`: add a `useGameWebSocket` hook that returns `{ connected, gameState }`. When `connected` is true, clear the polling interval and use only WebSocket state. When `connected` is false (during reconnection backoff), fall back to a single REST fetch — not polling.
- Gate the WebSocket path behind a **feature constant** (`const USE_WEBSOCKET = true`) that can be toggled for debugging, rather than leaving both paths active simultaneously.

### Risk 6: Stability Check Ordering
- Define an explicit **phase transition sequence** in `game_logic.py`: (1) all players complete actions → (2) run `apply_stability_check()` for each player → (3) persist updated state → (4) increment round → (5) broadcast. Encode this as a single `end_round()` method that orchestrates the steps atomically within one database transaction.
- Add an **integration test** that verifies gold is deducted before the round counter increments, using a game with a player who has revolters > supporters.

### Risk 7: WebSocket Rate Limiting
- Implement a **per-connection message counter** in `ConnectionManager` using a sliding window (e.g., `collections.deque` with timestamps). On each incoming WebSocket message, check the count in the last 60 seconds. If > 30, send an error frame and ignore the action.
- This can be deferred to a follow-up since the REST action endpoints already go through FastAPI middleware where rate limiting can be applied — WebSocket messages that trigger actions still call the same `perform_action()` service method.

---

## Appendix: Plan Documents

### PRD
Now I have a thorough understanding of the codebase and design document. Let me write the PRD.

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

### HLD
222 lines — well within the 250-line limit. The HLD document has been written to `/worktree/planning/empires-online-planning/docs/concepts/empires-online/HLD.md`.

Key architectural decisions in the document:

1. **Modular monolith** — three-tier architecture (React SPA → Nginx → FastAPI + PostgreSQL) with WebSocket layer added alongside existing REST API
2. **Native WebSocket over Socket.IO** — simpler, no extra server dependency, meets latency requirements
3. **PostgreSQL NOTIFY/LISTEN over Redis** — avoids new infrastructure; sufficient for 50-game concurrency target
4. **Database-first state persistence** — all state written to PostgreSQL before WebSocket broadcast for crash safety
5. **Alembic migrations** — replaces `create_all()` for safe schema evolution, auto-run on startup
6. **In-process connection manager** — in-memory WebSocket tracking per process, scales via NOTIFY/LISTEN

The document covers all 11 sections: architecture overview with diagram, system components, data model with schema changes, API contracts (new WebSocket endpoint + round summary + extended actions), full technology stack, integration points, security architecture, deployment with new Nginx WebSocket config, scalability strategy, monitoring approach, and 5 ADRs with rationale.

### LLD
The document is complete and reads correctly at 368 lines. Here's what the LLD covers:

- **Section 1**: Implementation overview — Phase 2 scope summary
- **Section 2**: 10 new files + 14 modified files with specific paths and change descriptions
- **Section 3**: Detailed designs for WebSocket manager, WS route, game logic extensions, frontend hook, and toast system
- **Section 4**: Alembic setup + one migration adding `stability_checked` column
- **Section 5**: WebSocket endpoint contract, round summary endpoint, modified `perform_action` and `next_round` flows
- **Section 6**: Key function signatures across backend and frontend
- **Section 7**: Database-first backend state, WebSocket hook replacing polling on frontend
- **Section 8**: Error handling table covering WS, REST, DB, migration, and frontend layers
- **Section 9**: 7 unit tests, 7 integration tests, 3 manual E2E scenarios
- **Section 10**: 4-step migration strategy with deploy order
- **Section 11**: Rollback plan — all changes additive, safe to revert
- **Section 12**: Performance — DB indexing, WS fan-out math, Nginx config for WebSocket proxy