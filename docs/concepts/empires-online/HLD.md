222 lines — well within the 250-line limit. The HLD document has been written to `/worktree/planning/empires-online-planning/docs/concepts/empires-online/HLD.md`.

Key architectural decisions in the document:

1. **Modular monolith** — three-tier architecture (React SPA → Nginx → FastAPI + PostgreSQL) with WebSocket layer added alongside existing REST API
2. **Native WebSocket over Socket.IO** — simpler, no extra server dependency, meets latency requirements
3. **PostgreSQL NOTIFY/LISTEN over Redis** — avoids new infrastructure; sufficient for 50-game concurrency target
4. **Database-first state persistence** — all state written to PostgreSQL before WebSocket broadcast for crash safety
5. **Alembic migrations** — replaces `create_all()` for safe schema evolution, auto-run on startup
6. **In-process connection manager** — in-memory WebSocket tracking per process, scales via NOTIFY/LISTEN

The document covers all 11 sections: architecture overview with diagram, system components, data model with schema changes, API contracts (new WebSocket endpoint + round summary + extended actions), full technology stack, integration points, security architecture, deployment with new Nginx WebSocket config, scalability strategy, monitoring approach, and 5 ADRs with rationale.