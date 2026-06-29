# Phase 02: Database Connection & Schema Reader

## 1. Phase Purpose
This document controls execution for establishing connection pools to PostgreSQL and extracting metadata schemas dynamically.

## 2. Feature Objective
* **Phase Goal:** Establish asynchronous connection pools using SQLAlchemy + asyncpg, fetch database metadata from catalog tables, and expose the schema inspection endpoint.
* **User Or System Outcome:** The application can query active tables and columns in Postgres and output a clean JSON map, providing the context for both the schema tree UI and the AI prompt builder.
* **In Scope:** `app/db/session.py` (connection pooling), `app/db/reader.py` (metadata inspection queries), and endpoint route `GET /api/v1/schema`.
* **Out Of Scope:** SQL translation, SQL Validation, UI elements.

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** [Phase 01 - Scaffolding & Core Configuration](./phase-01-scaffolding.md) -> Must be marked [x] in the Local Tracker.
* **Downstream Tasks (Unlocks):** [Phase 03 - SQL Generation & AST Validation Service](./phase-03-sql-generation.md)
* **Target Git Commit Prefix:** `feat(backend-db): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** [YYYY-MM-DD to YYYY-MM-DD]
* **Related PRD Section:** Feature 1 (Database Schema Reader) and Section 16 (Security)
* **Related Build Plan Section:** Section 5 (Lifespan & Connections) and Section 6 (Domain Models)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `DATABASE_URL` (requires a valid connection to a Postgres database).
* **Database/Index Changes:** Read-only access to catalogs (`information_schema.tables`, `information_schema.columns`).
* **Feature Flags / Config Switches:** None.
* **Seed / Fixture Requirements:** A sample PostgreSQL instance containing sample tables (`hotels`, `bookings`) for integration testing.
* **Required Reusable Utilities:** 
  - Import `Settings` from `app.core.config`.

## 6. API & Data Contract Specifications
* **Endpoint:** `GET /api/v1/schema`
* **Request Schema:** None.
* **Response Schema (JSON):**
  ```json
  {
    "tables": [
      {
        "name": "hotels",
        "columns": [
          {"name": "id", "type": "INTEGER"},
          {"name": "name", "type": "VARCHAR"},
          {"name": "city", "type": "VARCHAR"}
        ]
      },
      {
        "name": "bookings",
        "columns": [
          {"name": "id", "type": "INTEGER"},
          {"name": "hotel_id", "type": "INTEGER"},
          {"name": "booking_date", "type": "DATE"}
        ]
      }
    ]
  }
  ```

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** None directly.
* **System Behavior Change:** FastAPI establishes database connection pool on boot. Submitting a GET to the schema endpoint inspects the live database catalogs and returns the structural layout.
* **Error States To Support:**
  - DB Connection Lost: Return HTTP 503 Service Unavailable with a clean notification if the server loses database connectivity.

## 8. Acceptance Criteria
- Asynchronous database engine initialized and session dependency `get_db()` successfully closes sessions after API requests.
- Catalog reader dynamically extracts tables, columns, and types from the Postgres schema.
- System caches the database schema metadata in-memory at startup to prevent redundant database overhead.
- Endpoint `GET /api/v1/schema` outputs the cached database layout successfully.
- Pytest suite successfully mocks database queries.

## 9. Implementation Steps (Component Audit)

### A. Data Layer
* [NEW] `backend/app/db/session.py`:
  - [x] Initialize SQLAlchemy `create_async_engine` and `sessionmaker`.
  - [x] Write async dependency `get_db()`.
* [NEW] `backend/app/db/reader.py`:
  - [x] Write database metadata inspection queries using SQLAlchemy sessions against `information_schema`.
  - [x] Implement caching mechanism for schema retrieval.

### B. Controller / API Layer
* [NEW] `backend/app/api/v1/endpoints/schema.py`:
  - [x] Define route handler for `GET /api/v1/schema` calling the metadata caching service.
* [MODIFY] `backend/app/api/v1/router.py`:
  - [x] Include the schema router endpoints.
* [MODIFY] `backend/app/main.py`:
  - [x] Pre-populate schema cache in lifespan startup.

### C. Client / UI Layer
* `No UI changes in this phase`

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** Blocking thread pools if SQL queries run synchronously.
* **Operational Risks:** Connection leaks causing database catalog lockups.
* **Rollback Approach:** Disable schema endpoints and close DB engines.

## 11. Verification Protocol (Definition of Done)

### A. Automated Suite
* **Exact Commands:**
  - `poetry run mypy app/`
  - `poetry run pytest tests/`

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Happy Path | `GET /api/v1/schema` | Returns JSON of tables, columns, and types | 200 OK |
| DB Disconnected | Shut down Postgres and call `GET /api/v1/schema` | Returns database unreachable warning message | 503 Service Unavailable |
| Type Check | Run `poetry run mypy app/` | Validation check passes | 0 |

### C. Evidence To Capture
- Database query logs showing schema extraction queries.
- JSON response payload from schema endpoint.

## 12. Execution Notes
* **Status:** Completed
* **Started At:** 2026-06-28
* **Completed At:** 2026-06-28
* **Blockers Encountered:** None.
* **Notes:**
  - `ruff check .` — All checks passed.
  - `mypy app/` — Success: no issues found in 14 source files.
  - `pytest` — 3 passed (health, schema 503, schema mocked).
  - Schema cache populated at startup via lifespan; graceful fallback if DB unavailable.
  - `GET /api/v1/schema` returns 503 when cache is empty.
