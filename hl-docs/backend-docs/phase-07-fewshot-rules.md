# Phase 07: ORM Models, DB Tables & Startup Seeder

## 1. Phase Purpose
This document controls execution for Phase 07, focusing exclusively on the **data layer**: defining SQLAlchemy ORM models for `business_rules` and `few_shot_examples`, creating those tables in the database at startup via `Base.metadata.create_all()`, and writing a startup seeder that populates default rows (with pre-computed embedding vectors) if the tables are empty.

> **Scope note:** The service-layer retrieval logic (cosine similarity on few-shot examples, prompt injection, API wiring) is handled separately in [Phase 07b](./phase-07b-fewshot-integration.md) to keep each phase focused and verifiable independently.

## 2. Feature Objective
* **Phase Goal:** Introduce `DeclarativeBase`, define `BusinessRule` and `FewShotExample` ORM models, create the tables at lifespan startup, and seed defaults (hotel/booking domain: status codes + example queries) with pre-computed question embedding vectors.
* **User Or System Outcome:** On every cold-start, the database is guaranteed to have the required tables and at least one set of default rules and examples. This is the foundational data contract that Phase 07b's retrieval layer depends on.
* **In Scope:** `db/models.py`, `db/seeder.py`, lifespan wiring in `main.py`, `tests/test_seeder.py`.
* **Out Of Scope:** Alembic migrations (project uses zero-migration `create_all` pattern), retrieval logic, prompt injection, service/API changes (all in Phase 07b).

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** [Phase 06 - Context Builder & Semantic Pruning (RAG)](./phase-06-schema-pruning.md)
* **Downstream Tasks (Unlocks):** [Phase 07b - Few-Shot Retrieval & Prompt Integration](./phase-07b-fewshot-integration.md)
* **Target Git Commit Prefix:** `feat(backend-rules-db): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** 2026-07-01
* **Related PRD Section:** Section 7 (SQL Few-Shot Example RAG, Business Rules Registry) and Section 10 (Acceptance Criteria)
* **Related Build Plan Section:** Section 3 (System Boundaries) and Section 6 (Data Flow)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `DATABASE_URL`, `GEMINI_API_KEY`, `EMBEDDING_PROVIDER`.
* **Database/Index Changes:**
  - Create table `business_rules` with columns: `id` (PK), `rule_name` (str), `rule_description` (str), `rule_value` (str).
  - Create table `few_shot_examples` with columns: `id` (PK), `question` (str), `sql_query` (str), `question_vector` (PostgreSQL `ARRAY(Float)`).
  - Tables are created via `Base.metadata.create_all()` in the FastAPI lifespan — not Alembic.
* **No new dependencies required:** SQLAlchemy 2.x `Mapped`/`mapped_column` ORM and `postgresql.ARRAY` are already available via the existing `sqlalchemy = "^2.0.0"` and `asyncpg = "^0.30.0"` dependencies.

## 6. API & Data Contract Specifications
* No new API endpoints in this phase.
* **Seeded BusinessRule row shape:**
  ```
  rule_name        | rule_description                    | rule_value
  booking_statuses | Booking status code to label mapping | 1=confirmed, 2=pending, 3=cancelled, 4=completed
  active_record    | Filter for active/live records      | Use is_active = TRUE or status NOT IN (3)
  ```
* **Seeded FewShotExample row shape:**
  ```
  question                          | sql_query                                                                 | question_vector
  Which hotel has the most bookings | SELECT hotel_id, COUNT(*) AS total FROM bookings GROUP BY hotel_id ...    | [0.12, -0.04, ...]
  Show all confirmed bookings       | SELECT * FROM bookings WHERE status = 1                                   | [...]
  List hotels in a specific city    | SELECT id, name, city FROM hotels WHERE city = 'Lahore'                  | [...]
  ```

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** None.
* **System Behavior Change:**
  - On startup, two new tables are created (if they don't exist).
  - Each table is checked **independently**: if `business_rules` is empty it is seeded; if `few_shot_examples` is empty it is seeded. A non-empty table is never touched.
  - Seeder is idempotent: each table seeds exactly once and never inserts duplicates.
  - Startup log emits per-table: `"Seeded N business rules."` / `"Business rules already seeded (N rows), skipping."` (same pattern for few-shot examples).

## 8. Acceptance Criteria
- `db/models.py` defines `Base`, `BusinessRule`, and `FewShotExample` using SQLAlchemy 2.x `Mapped`/`mapped_column` API.
- `db/seeder.py` implements `seed_database(db, provider)` that is idempotent and logs its outcome.
- `main.py` lifespan calls `create_all` → `seed_database` → `load_schema` in that order.
- All existing tests continue to pass (no regression from introducing ORM Base).
- `test_seeder.py` covers: seeder skips when tables are non-empty, seeder inserts rows when tables are empty.
- `poetry run ruff check .`, `poetry run mypy app/`, `poetry run pytest` all pass.

## 9. Implementation Steps (Component Audit)

### A. Data Layer
* [NEW] `backend/app/db/models.py`:
  - [ ] Define `Base = DeclarativeBase()`.
  - [ ] Define `BusinessRule(Base)` model with `Mapped` typed columns: `id` (Integer PK autoincrement), `rule_name` (String), `rule_description` (String), `rule_value` (String).
  - [ ] Define `FewShotExample(Base)` model: `id` (Integer PK autoincrement), `question` (String), `sql_query` (String), `question_vector` must use an **explicit** `mapped_column(ARRAY(Float), nullable=False)` — do NOT rely on type inference. SQLAlchemy 2.x cannot infer `ARRAY(Float)` from `Mapped[list[float]]` automatically and mypy strict will reject it without the explicit annotation.
  - [ ] Example:
    ```python
    from sqlalchemy.dialects.postgresql import ARRAY
    from sqlalchemy import Float
    question_vector: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    ```

* [NEW] `backend/app/db/seeder.py`:
  - [ ] Define `DEFAULT_BUSINESS_RULES: list[dict[str, str]]` — hotel/booking domain rule set.
  - [ ] Define `DEFAULT_FEW_SHOT_QUESTIONS: list[dict[str, str]]` — hotel/booking domain question→SQL pairs.
  - [ ] Implement `async def seed_database(db: AsyncSession, provider: EmbeddingsProvider) -> None`.
  - [ ] **Check each table independently using `db.scalar()`** (NOT raw `text("SELECT COUNT(*)")`):
    ```python
    from sqlalchemy import func, select
    rules_count = await db.scalar(select(func.count()).select_from(BusinessRule))
    examples_count = await db.scalar(select(func.count()).select_from(FewShotExample))
    ```
  - [ ] If `rules_count == 0`: insert default `BusinessRule` rows via `db.add()`, call `await db.commit()`.
  - [ ] If `examples_count == 0`: generate embedding per question via `provider.get_embedding()`, insert `FewShotExample` rows via `db.add()`, call `await db.commit()`.
  - [ ] Each table is seeded independently — a non-empty table is **never touched** regardless of the other table's state.
  - [ ] Wrap entire body in `try/except Exception`: on failure, call `await db.rollback()`, log a warning, and return — seeding failure must never block server startup.

### B. Lifespan Wiring
* [MODIFY] `backend/app/main.py`:
  - [ ] Add imports: `Base` from `app.db.models`, `seed_database` from `app.db.seeder`, `get_embeddings_provider` from `app.services.embeddings`.
  - [ ] Also import `engine` from `app.db.session` (currently only `AsyncSessionLocal` is imported from there).
  - [ ] **Table creation — CRITICAL:** `engine` is an `AsyncEngine`. It does NOT have a `run_sync()` method. The correct call uses an `AsyncConnection`:
    ```python
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    ```
    This must run **before** the `AsyncSessionLocal()` session block because it uses a raw connection, not a session.
  - [ ] After table creation, open `AsyncSessionLocal()` session and call `await seed_database(db, provider)` then `await load_schema(db)`.
  - [ ] Full lifespan order: `engine.begin() + create_all` → `AsyncSessionLocal() + seed_database` → `load_schema` (all inside their own `try/except` blocks following the existing pattern).

### C. Tests
* [NEW] `backend/tests/test_seeder.py`:
  - [ ] **Do NOT use the `mock_db_session` conftest fixture** — seeder tests call `seed_database(db, provider)` directly with a plain `AsyncMock()`. The conftest fixture patches `AsyncSessionLocal` which is irrelevant here.
  - [ ] **Do NOT rely on the `mock_embeddings_provider` autouse fixture** — it patches `app.api.v1.endpoints.query.get_embeddings_provider`, which is irrelevant for seeder tests. Pass a `DummyProvider` directly as a parameter.
  - [ ] **Mock `db.scalar` not `db.execute`** — the seeder uses `db.scalar(select(func.count())...)` not raw `db.execute(text(...))`. Use `db.scalar.side_effect = [N, M]` where N = rules count, M = examples count.
  - [ ] `test_seed_skips_business_rules_when_non_empty`: `db.scalar.side_effect = [5, 0]` — assert no `BusinessRule` added.
  - [ ] `test_seed_skips_examples_when_non_empty`: `db.scalar.side_effect = [0, 3]` — assert no `FewShotExample` added.
  - [ ] `test_seed_populates_business_rules_when_empty`: `db.scalar.side_effect = [0, 5]` — assert `db.add` called with `BusinessRule` instances only.
  - [ ] `test_seed_populates_examples_when_empty`: `db.scalar.side_effect = [5, 0]` — assert `db.add` called with `FewShotExample` instances, each having non-empty `question_vector`.
  - [ ] `test_seed_handles_exception_gracefully`: make `db.scalar` raise; assert `db.rollback` called, no exception propagates.

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** `create_all` on a Neon serverless connection could fail if the connection pool is cold during startup — mitigated by the existing `try/except` pattern in the lifespan.
* **Seeder embedding generation risk:** If the embeddings provider fails during seeding, seeding fails silently but does not block startup (wrapped in try/except with a warning log).
* **Rollback Approach:** Delete the two new tables manually. Revert `main.py` and remove `models.py` and `seeder.py`.

## 11. Verification Protocol (Definition of Done)
### A. Automated Suite
* **Exact Commands:**
  - `poetry run ruff check .`
  - `poetry run ruff format --check .`
  - `poetry run mypy app/`
  - `poetry run pytest tests/ -v`

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Status |
| :--- | :--- | :--- | :--- |
| First cold start | Start server against empty DB | Tables created, default rows seeded, startup log confirms | — |
| Second start (already seeded) | Restart server | Seeder detects non-empty tables, skips, logs skip message | — |
| Test suite | `poetry run pytest` | All tests pass including `test_seeder.py` | — |

### C. Evidence To Capture
- Startup log output showing table creation and seeding confirmation.
- `poetry run pytest` output showing all tests pass.

## 12. Execution Notes
* **Status:** Completed
* **Started At:** 2026-07-01
* **Completed At:** 2026-07-01
* **Blockers Encountered:** None
* **Notes:** Phase split from original single Phase 07 into 07 (data layer) and 07b (service/API layer) for cleaner verification gates.
