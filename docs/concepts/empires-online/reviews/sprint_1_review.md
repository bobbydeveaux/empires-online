The sprint review document has been written to `docs/concepts/empires-online/reviews/sprint-1.md`. Here is the full document:

---

# Sprint Review: empires-online-sprint-1

**Date:** 2026-03-17
**Namespace:** coo-empires-online
**Duration:** 30m 0s (11:37 UTC → 12:06 UTC)
**Phase:** Completed

---

## Executive Summary

Sprint 1 delivered the full real-time WebSocket foundation for Empires Online. Three feature tracks ran in parallel and all landed cleanly:

- **WebSocket Backend Infrastructure** — `ws_manager.py` extended with PostgreSQL NOTIFY/LISTEN for cross-process fanout; all state-changing REST endpoints now trigger background-task broadcasts; Nginx configured for WebSocket proxy upgrades.
- **Alembic Migration Setup** — Migration framework bootstrapped (alembic.ini, env.py, initial migration for `stability_checked`); `init_db.py` updated to run `alembic upgrade head` on startup.
- **WebSocket Frontend Integration** — TypeScript WebSocket message types defined; `useGameWebSocket` hook built with exponential-backoff reconnection (1 s → 2 s → 4 s, cap 30 s); `Game.tsx` / `GameLobby.tsx` migrated from `setInterval` polling to WebSocket push.

All 18 tasks completed. Zero retries, zero merge conflicts. One review cycle was required (PR #50) — which caught and resolved a critical production-silent async bug before merge.

---

## Achievements

**Real-time architecture delivered end-to-end.** The full WebSocket stack — from the PostgreSQL NOTIFY channel to the reconnecting React hook — was built and integrated in a single sprint. All 7 game event types are now broadcast to connected clients.

**Polling eliminated.** `Game.tsx` no longer uses `setInterval`. All state is push-driven.

**Critical bug caught pre-merge.** Code review on PR #50 identified that `broadcast_event()` was a synchronous function calling `asyncio.get_event_loop().create_task()`. FastAPI runs sync background tasks in a threadpool where that call does not return the main event loop — all broadcasts would have **silently never executed in production** (raises `RuntimeError` in Python 3.12+). The fix (making `broadcast_event` async) was applied before merge. Unit tests masked the bug because `pytest.mark.asyncio` already provides an event loop.

**Clean migration baseline.** Alembic is fully configured with autogenerate support and a reversible initial migration.

**Zero retries, zero merge conflicts.** Well-scoped tasks with minimal overlapping file ownership.

**Documentation updated.** `docs/websocket-api.md` documents all 7 game event types and the broadcasting flow; `README.md` updated with links.

---

## Challenges

**Async/sync boundary footgun (PR #50).** The `broadcast_event()` bug is the sprint's most significant risk event. It is particularly dangerous because it produces no errors at runtime — it silently drops all broadcasts. The review process caught it, but the pattern should be proactively documented so it cannot recur.

**N+1 queries in `_build_leaderboard` (non-blocking, pre-existing).** The reviewer flagged that each `SpawnedCountry` row triggers individual `Country` and `Player` queries. This is pre-existing code that was extracted into a helper this sprint. Not blocking now, but will become a performance concern under load.

**Completion at 70%.** All 18 tasks completed, but the sprint-level completion is 70%, reflecting progress against the full project epic — Sprint 1 delivered foundational enablers ahead of the game logic and UI polish features in Sprint 2.

---

## Worker Performance

| Worker | Tasks | Share | Notes |
|--------|------:|------:|-------|
| code-reviewer | 9 | 50% | Reviewed every PR; caught 1 critical blocking issue |
| backend-engineer | 5 | 28% | WebSocket backend (2 tasks) + full Alembic chain (3 tasks) |
| frontend-engineer | 3 | 17% | All 3 WebSocket frontend tasks |
| devops-engineer | 1 | 6% | Nginx proxy config — smallest scope this sprint |

The `backend-engineer` carried the heaviest technical load, implementing the PostgreSQL NOTIFY/LISTEN fanout (the most architecturally complex piece) plus the full Alembic migration chain. The `frontend-engineer`'s longest task (19m, PR #47) reflects the breadth of changes across both `Game.tsx` and `GameLobby.tsx`. The `devops-engineer` was lightly utilised, as expected for a foundational infra sprint; Sprint 2 may offer more surface area.

---

## Recommendations

1. **Document async/sync background task conventions.** Add a note to `COPILOT_INSTRUCTIONS.md` or a `docs/async-patterns.md`: *always pass async callables directly to `BackgroundTasks.add_task()`; never call `asyncio.get_event_loop()` from a sync background task callable.* Flag this pattern explicitly in future reviews.

2. **Fix N+1 queries in `_build_leaderboard` in Sprint 2.** Add joined/eager loading for `Country` and `Player` on the `SpawnedCountry` query before the leaderboard endpoint sees real traffic.

3. **Add end-to-end WebSocket integration tests.** The current tests cover unit-level message builders but not the full round-trip: REST action → background broadcast → WebSocket client receives correct message. This is the most likely source of future regressions. Target this in Sprint 2 as part of `empires-online-feat-backend-tests`.

4. **Validate reconnection state-sync in staging.** The `useGameWebSocket` hook fetches full game state via REST on reconnect. Exercise this path against a real backend to verify the async timing between reconnect delay and in-flight REST response produces no stale-state window.

5. **Increase `devops-engineer` scope in Sprint 2.** With the WebSocket and migration infrastructure in place, Sprint 2 is a good opportunity for observability, CI pipeline coverage, and deployment improvements.

---

## Metrics Summary

| Metric | Value |
|--------|-------|
| Sprint Duration | 30m 0s |
| Total Tasks | 18 |
| Completed | 18 (100%) |
| Failed / Blocked | 0 / 0 |
| First-Time-Right Rate | 100% |
| Total Retries | 0 |
| Review Cycles | 1 |
| Merge Conflicts | 0 |
| Average Task Duration | 7m 0s |
| Longest Task | PR #47 — Wire hook into Game/GameLobby (19m) |
| Shortest Task | PR #46 — Nginx WebSocket proxy (4m) |
| Critical Issues Found in Review | 1 (async background task bug, PR #50) |
| PRs Merged | 9 (#43–#51) |
| Overall Epic Completion | 70% |