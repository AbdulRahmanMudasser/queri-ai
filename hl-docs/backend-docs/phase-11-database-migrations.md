  # Phase 11: Database Migrations Management

<!---
DOCUMENTATION RULES:
1. File naming:
   - Standard: phase-11-database-migrations.md
2. Workflow Tracker Link:
   - Local Platform Tracker: [execution-workflow.md](./execution-workflow.md)
3. High-Level PRD Link:
   - Project PRD: [backend-build-plan.md](./backend-build-plan.md)
--->

## 1. Phase Purpose
This document controls execution for Phase 11: Database Migrations Management. It outlines the transition from a naive `create_all` startup script to an industry-standard Alembic migrations strategy, fully supporting asynchronous execution and `pgvector` models. 

Use this file for:
- exact phase scope (Adding Alembic, removing `create_all`)
- prerequisites and dependencies (SQLAlchemy, asyncpg, pgvector)
- affected files and systems (`main.py`, `pyproject.toml`, `alembic/`)
- implementation notes
- acceptance and verification
- execution evidence

## 2. Feature Objective
* **Phase Goal:** Introduce Alembic to track and safely apply asynchronous database schema changes across environments.
* **User Or System Outcome:** The database schema can be upgraded safely in production via CLI/CI-CD without data loss, replacing the `create_all` strategy.
* **In Scope:** Adding Alembic via Poetry, initializing async template, configuring `env.py` for async and `pgvector`, creating a baseline migration, and updating `main.py`.
* **Out Of Scope:** Automated migration execution on application startup (migrations must be triggered manually or via deployment pipelines).

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** Phase 02 (Database Schema) -> Must be marked [x] in the Local Tracker.
* **Downstream Tasks (Unlocks):** Future schema modifications (e.g., Phase 08 Memory/RBAC tables).
* **Target Git Commit Prefix:** `build(backend-db): add alembic async migrations`

## 4. Ownership And Delivery Notes
* **Owner:** Backend Engineering
* **Priority:** High
* **Target Window:** TBD
* **Related PRD Section:** Database Infrastructure
* **Related Build Plan Section:** Database Setup

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `DATABASE_URL` (used by Alembic to connect).
* **Database/Index Changes:** Addition of the `alembic_version` table.
* **Feature Flags / Config Switches:** N/A
* **Seed / Fixture Requirements:** N/A
* **Required Reusable Utilities:**
  - Import `Base` from `app.db.models` for target metadata.
  - Import `pgvector.sqlalchemy` in `env.py` to properly recognize Vector columns.

## 6. API & Data Contract Specifications
* **Endpoint:** N/A (CLI Driven)
* **Request Schema (Zod/JSON):** N/A
* **Response Schema (JSON):** N/A

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** None.
* **System Behavior Change:** FastAPI no longer creates tables on startup. Migrations must be executed via `alembic upgrade head`.
* **Error States To Support:** Database errors on application boot if migrations haven't been applied.
* **Accessibility / Platform Constraints:** N/A

## 8. Acceptance Criteria
- [x] `alembic` is added to `pyproject.toml` dependencies.
- [x] `alembic/env.py` is configured for async operations using `app.core.config.settings.DATABASE_URL`.
- [x] `alembic/env.py` imports `pgvector` to prevent accidental column drops during autogeneration.
- [x] `main.py` is stripped of ALL database creation logic (both `create_all` and `CREATE EXTENSION`).
- [x] Initial migration script is generated and manually patched to include `CREATE EXTENSION vector`.

## 9. Implementation Steps (Component Audit)

### A. Data Layer / Config
* [MODIFY] `pyproject.toml`:
  - **Target Anchor:** Insert under `[tool.poetry.dependencies]`
  - [x] Add `alembic`
* [NEW] `alembic.ini` & `alembic/env.py`:
  - **Target Anchor:** Root backend folder via `poetry run alembic init -t async alembic`
  - [x] Configure `target_metadata = Base.metadata`
  - [x] Import `pgvector.sqlalchemy`
  - [x] Import `app.core.config.settings` and override `sqlalchemy.url` directly, bypassing `alembic.ini`.
* [NEW] Baseline Migration Script:
  - **Target Anchor:** Top of the `upgrade()` function
  - [x] Manually insert `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` before tables are created.

### B. Controller / API Layer (App Lifespan)
* [MODIFY] `app/main.py`:
  - **Target Anchor:** Inside `lifespan` context manager.
  - [x] Remove `await conn.run_sync(Base.metadata.create_all)` entirely.
  - [x] Remove `CREATE EXTENSION IF NOT EXISTS vector` entirely.

### C. Client / UI Layer
* N/A

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** If `pgvector` is not imported in `env.py`, Alembic will fail to recognize the column type and generate drop/recreate statements.
* **Operational Risks:** Forgetting to run migrations in CI/CD will result in missing tables/columns, crashing the app at runtime.
* **Rollback Approach:** Run `alembic downgrade -1` to safely undo a specific migration. Re-add `create_all` to `main.py` if reverting entirely to prototyping mode.

## 11. Verification Protocol (Definition of Done)

### A. Automated Suite
* **Exact Command:** `poetry run alembic upgrade head`

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Happy Path | Run `alembic upgrade head` | Tables `alembic_version`, `business_rules`, `few_shot_examples` created | N/A |
| Generation | Run autogenerate | Migration script created with correct up/down steps | N/A |

### C. Evidence To Capture
- [x] Terminal output of `alembic revision --autogenerate -m "Baseline"`
- [x] Terminal output of `alembic upgrade head`

## 12. Execution Notes
* **Status:** Completed
* **Started At:** 2026-07-02
* **Completed At:** 2026-07-02
* **Blockers Encountered:** Missing pgvector on Windows; resolved by moving database infrastructure to a Docker container via `docker-compose.yml`.
* **Notes:** Strict industry standard implemented: no automatic migrations on startup.
