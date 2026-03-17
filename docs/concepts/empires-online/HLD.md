The HLD is 302 lines — well within the 500-line limit. Here's what I did:

The existing `HLD.md` did **not** contain an actual HLD document — it contained a summary description of the HLD plus a full duplicate of the PRD. I wrote a proper HLD from scratch based on:

1. **The PRD requirements** — all functional/non-functional requirements are addressed
2. **Actual codebase analysis** — verified existing code structure, models, routes, WebSocket implementation, Docker setup, and Nginx config

The HLD covers all 11 sections:
- **Architecture overview** with ASCII diagram showing the three-tier architecture + WebSocket layer
- **System components** for frontend, backend, database, and infrastructure with Phase 2 change tracking
- **Data model** with existing schema and the new `stability_checked` migration
- **API contracts** — WebSocket message types, round summary endpoint, extended action types
- **Technology stack** — full matrix with version info and phase 2 additions
- **Integration points** — WebSocket↔REST flow, auto phase transitions, PG NOTIFY/LISTEN
- **Security architecture** — auth, authorization, input validation, rate limiting
- **Deployment** — Docker Compose updates, Nginx WebSocket proxy config
- **Scalability strategy** — current target (300 connections) and future scaling path
- **Monitoring** — health checks, logging, future metrics
- **5 ADRs** — Native WS over Socket.IO, PG NOTIFY over Redis, DB-first persistence, Alembic over create_all, full state over deltas