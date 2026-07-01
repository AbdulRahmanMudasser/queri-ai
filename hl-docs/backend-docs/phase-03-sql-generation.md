# Phase 03: SQL Generation & AST Validation Service

## 1. Phase Purpose
This document controls execution for translating user questions into SQL via Gemini and parsing/validating SQL queries using SQLGlot AST analysis.

## 2. Feature Objective
* **Phase Goal:** Integrate the Google Gemini API to translate English questions to PostgreSQL statements, and parse the output via SQLGlot to block any non-SELECT operations and stacked queries.
* **User Or System Outcome:** The user receives a safe, read-only SQL query block translation of their question, with absolute certainty that no destructive commands can execute.
* **In Scope:** `app/services/validator.py` (SQLGlot rules), `app/services/translator.py` (Gemini integration), and endpoint `POST /api/v1/query/generate`.
* **Out Of Scope:** Executing the queries, showing UI charts.

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** [Phase 02 - Database Connection & Schema Reader](./phase-02-database-schema.md) -> Must be marked [x] in the Local Tracker.
* **Downstream Tasks (Unlocks):** [Phase 04 - Safe Query Execution & AI Explanation](./phase-04-safe-execution.md)
* **Target Git Commit Prefix:** `feat(backend-generator): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** June - July 2026
* **Related PRD Section:** Feature 3 (SQL Generation), Feature 4 (SQL Validation), and Section 16 (Security)
* **Related Build Plan Section:** Section 5 (Lifespan & Connections) and Section 8 (Security)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `GEMINI_API_KEY` (must be active for translation queries).
* **Database/Index Changes:** None.
* **Feature Flags / Config Switches:** None.
* **Seed / Fixture Requirements:** None.
* **Required Reusable Utilities:**
  - Import `get_db` from `app.db.session`.
  - Import schema tree structure from cached database context.

## 6. API & Data Contract Specifications
* **Endpoint:** `POST /api/v1/query/generate`
* **Request Schema (JSON):**
  ```json
  {
    "question": "Show hotels booked last month"
  }
  ```
* **Response Schema (JSON):**
  ```json
  {
    "sql": "SELECT h.name FROM bookings b JOIN hotels h ON h.id = b.hotel_id WHERE b.booking_date >= '2026-05-01' AND b.booking_date < '2026-06-01';"
  }
  ```

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** None directly.
* **System Behavior Change:** Submitting a question triggers a schema-injected prompt to Gemini, receives SQL, parses it using SQLGlot, validates that it consists of a single `SELECT` or `WITH` expression, and returns the query.
* **Error States To Support:**
  - Validation Fail: If LLM produces an unauthorized keyword (e.g. `DROP`, `DELETE`), block it and return HTTP 400 Bad Request.
  - Rate Limits: Catch rate limits or missing credentials from the Gemini API and return HTTP 503 Service Unavailable.

## 8. Acceptance Criteria
- SQLGlot AST validation correctly allows standard `SELECT` and `WITH` CTEs.
- SQLGlot AST validation blocks stacked queries (multiple queries separated by semicolons).
- SQLGlot AST validation blocks all database modification statements (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`).
- Translator system builds context prompts incorporating active schemas and prompts Gemini 2.5 Flash Lite.
- Endpoint `POST /api/v1/query/generate` works end-to-end and has a comprehensive test suite.

## 9. Implementation Steps (Component Audit)

### A. Data Layer
* `No direct database changes in this phase`

### B. Controller / API Layer
* [NEW] `backend/app/services/validator.py`:
  - [ ] Write `validate_sql(sql: str) -> bool` parsing input with `sqlglot.parse_one`.
  - [ ] Traverse AST nodes and verify they only contain read nodes (e.g., `Select`, `With`). Raise custom ValueError on unsafe operations.
  - [ ] Check if multiple statements are passed (stacked queries) and raise exception.
* [NEW] `backend/app/services/translator.py`:
  - [ ] Initialize `google.generativeai` client.
  - [ ] Format database schema map into standard Markdown/SQL definitions context.
  - [ ] Construct system prompt explicitly enforcing SQL rules, schema, and read-only instructions.
  - [ ] Request completion from Gemini and strip markdown wrappers.
* [NEW] `backend/app/api/v1/endpoints/query.py`:
  - [ ] Add endpoint `POST /api/v1/query/generate` calling the translator and validator.
* [MODIFY] `backend/app/api/v1/router.py`:
  - [ ] Register query endpoint routes.

### C. Client / UI Layer
* `No UI changes in this phase`

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** LLM prompt injection bypassing security parsing.
  - *Mitigation:* The AST parser works on syntactic structures, so even if the prompt tricks the LLM to output a delete, the parser blocks it.
* **Operational Risks:** API rate limit exhaustion.
* **Rollback Approach:** Rollback routers and restore old validators.

## 11. Verification Protocol (Definition of Done)

### A. Automated Suite
* **Exact Command:** `poetry run pytest tests/test_security.py` (runs the safety validation harness).

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Happy Path | `POST /api/v1/query/generate` with "hotels in Lahore" | Returns valid SELECT query | 200 OK |
| Unsafe Translation | Mock LLM outputting `DROP TABLE bookings;` | Query is blocked, error returned | 400 Bad Request |
| Stacked Query | Validate `SELECT * FROM hotels; DROP TABLE bookings;` | Stacked query blocked, error returned | 400 Bad Request |
| API Rate Limited | Gemini returns rate limit exception | Returns API service currently busy message | 503 Service Unavailable |

### C. Evidence To Capture
- Output of `pytest tests/test_security.py` showing all safety cases passing.
- Example logs showing the exact prompt passed to Gemini and the returned SQL.

## 12. Execution Notes
* **Status:** Completed
* **Started At:** 2026-06-28
* **Completed At:** 2026-06-29
* **Blockers Encountered:** None.
* **Notes:** All 23 tests, Ruff, and Mypy passed successfully.
