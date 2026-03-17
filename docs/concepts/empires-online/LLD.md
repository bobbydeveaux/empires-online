The refined LLD is **696 lines** — well within the 800-line limit.

Here's what the LLD covers, grounded in the actual codebase:

1. **Implementation Overview** — 5 workstreams with specific file references
2. **File Structure** — 10 new files + 14 modified files with exact paths and change descriptions
3. **Detailed Component Designs** — WebSocket manager extension, WS route additions, game logic for `recruit_people`/`acquire_territory`/`run_stability_check`, frontend `useGameWebSocket` hook, Toast system
4. **Database Schema** — Alembic setup + migration adding `stability_checked` column
5. **API Implementation** — WebSocket message types (verified against existing `ws.py`), round summary endpoint, modified `perform_action`/`next_round` flows with stability check, `end-actions` endpoint for auto phase transition
6. **Function Signatures** — Backend and frontend signatures aligned with existing code patterns
7. **State Management** — Database-first backend, WebSocket-driven frontend replacing the existing `setInterval(loadGameState, 5000)` polling in `Game.tsx`
8. **Error Handling** — Table covering WS, REST, DB, migration, game logic, and frontend layers
9. **Test Plan** — 8 unit tests, 8 integration tests, 3 manual E2E scenarios
10. **Migration Strategy** — 4-step process with deploy order
11. **Rollback Plan** — All changes additive, `alembic downgrade -1` + git revert
12. **Performance** — DB indexing, WS fan-out math (300 connections), Nginx WebSocket proxy config with `proxy_read_timeout`