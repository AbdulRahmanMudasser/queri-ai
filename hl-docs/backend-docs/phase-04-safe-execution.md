# Phase 04: Safe Query Execution & AI Explanation

## 1. Phase Purpose
This document controls execution for running validated SQL queries securely on the Postgres database and generating natural language summaries of the returned records.

## 2. Feature Objective
* **Phase Goal:** Execute validated SQL queries inside a read-only transaction with a 5-second timeout and 100-row limit, and prompt the Gemini API to explain the results in English.
* **User Or System Outcome:** The user gets a tabular result grid and a clear, easy-to-understand explanation of what the query returned.
* **In Scope:** Endpoint `POST /api/v1/query/execute`, endpoint `POST /api/v1/query/explain`, transaction wrappers, timeout setups, row limits, and route integration tests.
* **Out Of Scope:** Formatting UI themes, storing query results.

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** [Phase 03 - SQL Generation & AST Validation Service](./phase-03-sql-generation.md) -> Must be marked [x] in the Local Tracker.
* **Downstream Tasks (Unlocks):** None (Backend MVP Complete).
* **Target Git Commit Prefix:** `feat(backend-executor): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** [YYYY-MM-DD to YYYY-MM-DD]
* **Related PRD Section:** Feature 5 (Query Execution), Feature 6 (Result Visualization), Feature 7 (AI Explanation), and Section 16 (Security)
* **Related Build Plan Section:** Section 5 (Lifespan & Connections) and Section 7 (Error Handling)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `DATABASE_URL` (requires a read-only user configuration), `GEMINI_API_KEY`.
* **Database/Index Changes:** Session transaction mode must be configured as `READ ONLY`. Capped execution duration to 5.0 seconds.
* **Feature Flags / Config Switches:** None.
* **Seed / Fixture Requirements:** Integration test suite requires mock database rows setup in `conftest.py`.
* **Required Reusable Utilities:**
  - Import `get_db` from `app.db.session`.
  - Import `validate_sql` from `app.services.validator`.

## 6. API & Data Contract Specifications

### A. Execution Endpoint: `POST /api/v1/query/execute`
* **Request Schema (JSON):**
  ```json
  {
    "sql": "SELECT name, city FROM hotels WHERE city = 'Lahore';"
  }
  ```
* **Response Schema (JSON):**
  ```json
  {
    "columns": ["name", "city"],
    "rows": [
      ["Marriott", "Lahore"],
      ["Pearl Continental", "Lahore"]
    ]
  }
  ```

### B. Explanation Endpoint: `POST /api/v1/query/explain`
* **Request Schema (JSON):**
  ```json
  {
    "question": "Show hotels in Lahore",
    "sql": "SELECT name, city FROM hotels WHERE city = 'Lahore';",
    "columns": ["name", "city"],
    "rows": [
      ["Marriott", "Lahore"],
      ["Pearl Continental", "Lahore"]
    ]
  }
  ```
* **Response Schema (JSON):**
  ```json
  {
    "explanation": "There are 2 hotels in Lahore in the database: Marriott and Pearl Continental."
  }
  ```

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** None directly.
* **System Behavior Change:** Submitting a query runs it inside a read-only, timeout-monitored connection block. Returning the grid and details lets the frontend display data and insights together.
* **Error States To Support:**
  - Database Execution Timeout: If query runs longer than 5.0 seconds, cancel execution and return HTTP 408 Request Timeout.
  - SQL Syntax Error: If Postgres parser fails, capture the exception and return HTTP 400 Bad Request.
  - Validation Fail: Block any custom SQL executed directly that fails validator rules.

## 8. Acceptance Criteria
- Incoming queries are re-validated through SQLGlot immediately before execution.
- Connections run inside a read-only transaction block (`SET TRANSACTION READ ONLY`).
- Timeouts of 5.0 seconds are strictly enforced on db statements.
- Results are capped at 100 rows.
- Endpoint `/api/v1/query/explain` prompts Gemini with the question, the query, and the rows to produce a simple English summary.
- Integration tests in `tests/test_routes.py` verify routes with mock environments.

## 9. Implementation Steps (Component Audit)

### A. Data Layer
* [MODIFY] `backend/app/db/session.py`:
  - [ ] Add transaction interceptors or helper variables to enforce `READ ONLY` connection locks.

### B. Controller / API Layer
* [MODIFY] `backend/app/api/v1/endpoints/query.py`:
  - [ ] Implement `POST /api/v1/query/execute` endpoint. Incorporate SQL validation check, async execution statement timeouts, and row cap limit logic.
  - [ ] Implement `POST /api/v1/query/explain` endpoint. Formulate prompt containing the question and table data, call Gemini API, and return the summary.
* [NEW] `backend/tests/conftest.py`:
  - [ ] Configure client adapters and mock dependencies (mocking Gemini API calls and database connections).
* [NEW] `backend/tests/test_routes.py`:
  - [ ] Write integration test cases for endpoints `/schema`, `/query/generate`, `/query/execute`, and `/query/explain`.

### C. Client / UI Layer
* `No UI changes in this phase`

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** Slow query lockups hanging backend worker tasks.
* **Operational Risks:** Exhausting database connections due to unclosed sessions.
* **Rollback Approach:** Revert backend routers to state prior to execution endpoints.

## 11. Verification Protocol (Definition of Done)

### A. Automated Suite
* **Exact Command:** `poetry run pytest tests/test_routes.py` (runs API integration tests).

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Happy Path Execution | `POST /api/v1/query/execute` with valid query | Returns column names and data arrays | 200 OK |
| Unsafe Execution Attempt | `POST /api/v1/query/execute` with drop statement | Blocked by validator immediately | 400 Bad Request |
| Timeout Execution | Run query containing heavy sleep (`pg_sleep(6)`) | Execution aborted, timeout error | 408 Request Timeout |
| Happy Path Explain | `POST /api/v1/query/explain` with mock data | Returns English explanation summary | 200 OK |

### C. Evidence To Capture
- Pytest output showing all integration tests successfully passing.
- Response payloads showing query columns, rows, and summarized details.

## 12. Execution Notes
* **Status:** Planned
* **Started At:** [YYYY-MM-DD]
* **Completed At:** [YYYY-MM-DD]
* **Blockers Encountered:** None.
* **Notes:** None.
