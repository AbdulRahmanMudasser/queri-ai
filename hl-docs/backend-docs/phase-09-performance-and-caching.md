# Phase 09: Performance and Distributed Caching

<!---
DOCUMENTATION RULES:
1. File naming:
   - Standard: phase-[00]-[name].md (e.g., phase-01-auth-setup.md)
   - Large/Sub-phase: phase-[00][a/b/c]-[name].md (e.g., phase-01a-jwt-logic.md)
2. Workflow Tracker Link:
   - Local Platform Tracker: [execution-workflow.md](./execution-workflow.md)
3. High-Level PRD Link:
   - Project PRD: [project-name-prd.md](../[project-name]-prd.md)
--->

## 1. Phase Purpose
This document controls execution for Phase 09. The focus is to eliminate severe CPU bottlenecks and scale out the application's memory footprint by replacing localized state with distributed caching and offloading blocking operations from the async event loop.

## 2. Feature Objective
* **Phase Goal:** Integrate Redis for caching and vectorize/offload blocking math operations.
* **User Or System Outcome:** Reduced latency, increased API concurrency, and lower memory usage per worker.
* **In Scope:** Adding Redis integration, caching DB schema and few-shot/rules contexts, optimizing `cosine_similarity`.
* **Out Of Scope:** Any changes to the actual Gemini translation logic or AST safety validation.

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** Phase 08 -> Must be marked [x] in the Local Tracker.
* **Downstream Tasks (Unlocks):** Phase 10
* **Target Git Commit Prefix:** `refactor(backend-caching): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** July 2026
* **Related PRD Section:** N/A (Technical Debt Resolution)
* **Related Build Plan Section:** 6. Data Flow And State Strategy

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `REDIS_URL`
* **Database/Index Changes:** None
* **Feature Flags / Config Switches:** None
* **Seed / Fixture Requirements:** None
* **Required Reusable Utilities:**
  - Import `redis` driver for caching.
  - Require `docker-compose.yml` at project root for spinning up local Redis container.

## 6. API & Data Contract Specifications
* **Endpoint:** N/A (Internal refactoring)
* **Request Schema (Zod/JSON):** N/A
* **Response Schema (JSON):** N/A

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** Faster query generation responses.
* **System Behavior Change:** FastAPI workers will share schema/embedding states, and event loop won't be blocked.
* **Error States To Support:** Graceful degradation if Redis is unavailable.
* **Accessibility / Platform Constraints:** None

## 8. Acceptance Criteria
- `[x]` Schema context is cached in Redis instead of local `dict`.
- `[x]` Few-shot examples and business rules are cached with TTL.
- `[x]` `cosine_similarity` does not block the async event loop.

## 9. Implementation Steps (Component Audit)

### A. Data Layer
* [NEW] `docker-compose.yml`:
  - [ ] Add a Docker Compose file at the project root to spin up a local Redis instance for development.
* [MODIFY] `app/services/context.py`:
  - **Target Anchor:** Cache implementation lines.
  - [ ] Implement Redis-backed TTL caching using the Redis server.
  - [ ] Refactor `cosine_similarity` to use `asyncio.to_thread` or NumPy.

### B. Controller / API Layer
* [MODIFY] `app/api/v1/endpoints/query.py`:
  - **Target Anchor:** `generate_query` route
  - [ ] Update function to read from the new caching layer instead of hitting DB every time.

### C. Client / UI Layer
* N/A

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** Redis connection errors bringing down the context fetch.
* **Operational Risks:** Redis cache invalidation issues.
* **Rollback Approach:** Revert to in-memory dictionaries if Redis proves unstable.

## 11. Verification Protocol (Definition of Done)

### A. Automated Suite
* **Exact Command:** `poetry run pytest`

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Happy Path | Generate Query | Query returns quickly without DB load | 200 OK |
| Cache Hit | Generate Query (2nd time) | Returns from Redis cache | 200 OK |

### C. Evidence To Capture
- `pytest` executed successfully (70 tests passing).
- See `walkthrough.md` for specific details.

## 12. Execution Notes
* **Status:** Completed
* **Started At:** 2026-07-02
* **Completed At:** 2026-07-02
* **Blockers Encountered:** Redis initialization logic required `AsyncMock` patches in test suite. Fixed successfully.
* **Notes:** All endpoints and tests fully reflect the new Redis architecture.
