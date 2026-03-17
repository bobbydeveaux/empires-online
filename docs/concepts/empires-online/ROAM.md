Here's a summary of the refinements made:

**Added:**
- **Risk 3 (new, High):** Concurrent end-actions submissions race condition — when multiple players complete actions simultaneously, the `end-actions` endpoint could double-fire phase transitions without row-level locking
- **Assumption 6 (new):** PR #23's existing WebSocket infrastructure is stable and tested, since the backend feature builds on it rather than starting from scratch
- **Mitigation for Risk 3:** `SELECT ... FOR UPDATE` locking, idempotency guard, and integration test
- **`Last Refined` date** in header

**Updated:**
- **Risk 2:** Acknowledges PR #23 as the source of the `ConnectionManager` pattern, clarifying that the fragility is inherited from existing infrastructure
- **Risk 7 (was 6):** Refined to note the LLD now specifies the `end-actions` endpoint and modified `next_round` flow, but emphasizes the atomicity requirement within a single transaction remains critical
- **Obstacles:** Nginx obstacle now cross-references the epic's explicit file list; test infrastructure obstacle updated with LLD's refined test counts (8 unit/8 integration)
- **Assumptions 1 & 4:** Added ADR cross-references (ADR-002, ADR-005) to tie back to HLD decisions
- **Mitigations:** Risk numbering updated; Risk 2 mitigation references the epic's specified exponential backoff; Risk 5/7 mitigations reference ADR numbers

**Removed:**
- **Appendix section** containing full PRD duplicate and HLD/LLD summaries — this was ~190 lines of bloat duplicating documents available elsewhere
- AI instruction comments (`<!-- AI: ... -->`)