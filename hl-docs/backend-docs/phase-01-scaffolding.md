# Phase 01: Project Scaffolding & Core Configuration

## 1. Phase Purpose
This document controls execution for the initial scaffolding of the FastAPI backend, configuration management, logging, and static code quality pipeline.

## 2. Feature Objective
* **Phase Goal:** Scaffold the backend environment with Poetry, load Pydantic Settings, configure structured logging, and test the health check endpoint.
* **User Or System Outcome:** Developers have a clean, type-safe, and formatted environment that validates secrets at startup and automatically checks code safety on commit.
* **In Scope:** `pyproject.toml` config (Poetry, Ruff, Mypy), Pydantic settings loading, structured log configuration, health endpoint `/api/v1/health`, pre-commit hooks.
* **Out Of Scope:** Database connections, SQL generation, AI interactions.

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** None -> Marked [x] in the Local Tracker.
* **Downstream Tasks (Unlocks):** [Phase 02 - Database Connection & Schema Reader](./phase-02-database-schema.md)
* **Target Git Commit Prefix:** `feat(backend-scaffold): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** June - July 2026
* **Related PRD Section:** Section 8 (Platform Scope) and Section 10 (Acceptance Criteria)
* **Related Build Plan Section:** Section 4 (Directory Structure) and Section 11 (Code Quality)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `DATABASE_URL` (Postgres DSN), `GEMINI_API_KEY` (AI Key), `ENV` (default: "development").
* **Database/Index Changes:** None in this phase.
* **Feature Flags / Config Switches:** None.
* **Seed / Fixture Requirements:** None.
* **Required Reusable Utilities:** None.

## 6. API & Data Contract Specifications
* **Endpoint:** `GET /api/v1/health`
* **Request Schema:** None.
* **Response Schema (JSON):**
  ```json
  {
    "status": "healthy",
    "environment": "development"
  }
  ```

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** None directly.
* **System Behavior Change:** FastAPI server starts up, checks environment variables, configures log output, and responds to health pings.
* **Error States To Support:** 
  - Fail-fast on startup if `DATABASE_URL` or `GEMINI_API_KEY` is missing or in an invalid format.

## 8. Acceptance Criteria
- Poetry environment initialized with all dependencies listed in the build plan.
- Pydantic Settings verifies environment variables and enforces the `postgresql+asyncpg://` protocol for `DATABASE_URL`.
- Structured logging configuration writes request boundaries and boot logs.
- Pre-commit hook configurations validate Mypy and Ruff successfully.
- Root endpoint `/api/v1/health` returns HTTP 200 with status "healthy".

## 9. Implementation Steps (Component Audit)

### A. Data Layer
* [NEW] `backend/pyproject.toml`:
  - **Target Anchor:** File creation
  - [x] Add poetry dependencies: `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `sqlglot`, `sqlalchemy`, `asyncpg`, `google-generativeai`.
  - [x] Add `[tool.ruff]` and `[tool.mypy]` config sections with strict rules.
* [NEW] `backend/.pre-commit-config.yaml`:
  - [x] Add hooks for `ruff` formatting/linting and `mypy` strict type checking.

### B. Controller / API Layer
* [NEW] `backend/app/core/config.py`:
  - [x] Define `Settings(BaseSettings)` class. Add a field validator for `DATABASE_URL` format.
* [NEW] `backend/app/core/logger.py`:
  - [x] Set up structured logger using standard library dictionary configuration.
* [NEW] `backend/app/api/v1/endpoints/health.py`:
  - [x] Define the health route returning status and environment.
* [NEW] `backend/app/api/v1/router.py`:
  - [x] Create and export the APIRouter assembling all v1 endpoints.
* [NEW] `backend/app/main.py`:
  - [x] Instantiate `FastAPI` with lifespan event handlers. Connect CORS middleware and APIRouter.

### C. Client / UI Layer
* `No UI changes in this phase`

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** Python package dependency version conflicts.
* **Operational Risks:** Missing credentials during CI/CD checks causing build crashes.
* **Rollback Approach:** Revert to default scaffolding files.

## 11. Verification Protocol (Definition of Done)

### A. Automated Suite
* **Exact Commands:**
  - `poetry run ruff check .`
  - `poetry run mypy app/`
  - `poetry run pytest`

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Happy Path | `GET /api/v1/health` | `{"status": "healthy", ...}` | 200 OK |
| Config Error (Missing Env) | Boot server with empty `GEMINI_API_KEY` | Server fails to start, throwing validation error | Startup crash |
| Code Lint Check | Run `poetry run ruff check .` | No style violations or formatting errors | 0 |
| Strict Type Check | Run `poetry run mypy app/` | Mypy reports "Success: no issues found" | 0 |

### C. Evidence To Capture
- Terminal logs showing successful Poetry installation.
- Server startup log output with structured format.
- Output from health check curl query.

## 12. Execution Notes
* **Status:** Completed
* **Started At:** 2026-06-28
* **Completed At:** 2026-06-28
* **Blockers Encountered:** None.
* **Notes:**
  - `poetry install` resolved all dependencies successfully (69 packages).
  - `ruff check .` — All checks passed.
  - `mypy app/` — Success: no issues found in 10 source files.
  - `pytest -v` — 1 passed (health check endpoint).
  - Pre-commit config includes hooks for ruff (lint + format) and mypy (strict).
