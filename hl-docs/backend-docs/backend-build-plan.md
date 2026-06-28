# Backend Build Plan & Architecture (FastAPI)

This document is the technical source of truth for the Backend API layer of the AI SQL Assistant (`sql-assistant`). It records server-side responsibilities, clean directory layers, lifecycle management, data validation, database isolation, and security rules.

---

## 1. Platform Summary
* **Platform Name:** Backend API Service
* **Primary Responsibility:** Enforce security policies, read database metadata, translate natural language requests to SQL queries, validate SQL queries using AST analysis, execute queries against a read-only PostgreSQL instance, and summarize results.
* **Key Interfaces:** React Web Client, PostgreSQL Database (Neon), Google Gemini API (via `google-generativeai` SDK).
* **Primary Risks:** SQL Injection, database performance exhaustion (long-running queries), LLM hallucinations (referencing invalid columns/tables), bypass of SQL validator.

---

## 2. Core Technology Stack And Dependencies
* **Language & Runtime:** Python 3.11+
* **Primary Framework:** FastAPI (asynchronous API framework)
* **Web Server:** Uvicorn (ASGI web server)
* **SQL Parsing & Validation:** SQLGlot (for parsing and inspecting SQL ASTs)
* **Database Client:** SQLAlchemy (with `asyncpg` for asynchronous PostgreSQL access)
* **Data Validation & Settings:** Pydantic v2 & `pydantic-settings`
* **LLM SDK:** `google-generativeai` (Gemini API SDK)
* **Testing Stack:** Pytest, pytest-asyncio, HTTPX (for client testing)

---

## 3. System Boundaries And Responsibilities

### This Platform Owns
- Extracting database schemas (tables, columns, types) dynamically from PostgreSQL.
- Constructing prompts containing schemas and querying the LLM for translation.
- Strict parsing and AST checking of generated/incoming queries to prevent DDL (Data Definition) or DML (Data Modification) statements.
- Direct read-only database query execution with transaction timeouts.
- Wrapping query results in structured, JSON-serializable payloads.

### This Platform Does Not Own
- Rendering user interface components or client routing.
- Maintaining permanent user session states (stateless API model for MVP).

---

## 4. Directory Structure And Module Layout

To enforce modular separation of concerns, the backend is organized into layers:

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── schema.py       # Exposes schema inspection endpoints
│   │       │   ├── query.py        # Exposes query generation, execution & explanation
│   │       │   └── health.py       # Simple health check endpoint
│   │       └── router.py           # Assembler routing v1 endpoints
│   ├── core/
│   │   ├── config.py               # Settings validation (Pydantic BaseSettings)
│   │   └── logger.py               # Structured log config
│   ├── db/
│   │   ├── session.py              # Engine configuration & connection pooling
│   │   └── reader.py               # Metadata reader (extracts tables/columns)
│   ├── schemas/
│   │   ├── request.py              # Pydantic input validation models
│   │   └── response.py             # Pydantic response filtration models
│   ├── services/
│   │   ├── translator.py           # LLM interaction & prompt building logic
│   │   └── validator.py            # SQLGlot AST validation rules
│   └── main.py                     # App lifespan, middleware setup, CORS, and root app instantiation
├── tests/
│   ├── conftest.py                 # Pytest setup and mock dependencies
│   ├── test_routes.py              # Integration tests for routers
│   └── test_security.py            # AST validation safety harness checks
├── pyproject.toml                  # Dependencies and tool configurations (Poetry, Ruff, Mypy)
├── poetry.lock                     # Locked dependency resolution log
└── .env                            # Secret configurations (not committed)
```

### Module Rules
1. **Routes are thin:** Files in `api/` must only handle request binding, calling services, and returning responses. They must contain no raw business logic or raw SQL validation rules.
2. **Services are pure:** Code in `services/` contains business logic and is completely independent of the HTTP request context, making it easily testable.
3. **Pydantic Model Separation:** Request models (`schemas/request.py`) are strictly separated from Response models (`schemas/response.py`) to prevent internal database columns or fields from leaking.

---

## 5. Lifespan and Connection Management
* **Lifespan Manager:** The application uses FastAPI's `lifespan` context manager. On startup, it establishes the database engine connection pool and caches the database metadata. On shutdown, it closes all active pools to avoid connection leaks.
* **Dependency Injection:** Database sessions are fetched per request using a dependency helper injected into routers:
  ```python
  async def get_db():
      async with AsyncSessionLocal() as session:
          yield session
  ```
  This guarantees that all sessions are automatically closed, and any pending transactions are rolled back if an unhandled error occurs.

---

## 6. Data Flow And State Strategy
* **Primary Data Retrieval Model:** Asynchronous request-driven database queries.
* **Schema Reader Strategy:** Schema is queried from the PostgreSQL `information_schema` catalogs at startup and cached in-memory.
* **SQL Generation Flow:**
  1. Frontend submits a question to `POST /api/v1/query/generate`.
  2. Router calls `translator.py` service.
  3. Service reads schema, constructs prompt, calls Gemini API, and passes query through `validator.py`.
  4. If validation passes, return SQL.
* **Query Execution Flow:**
  1. Frontend submits SQL query to `POST /api/v1/query/execute`.
  2. Router calls the execution handler.
  3. Router runs `validator.py` AST analysis (defense-in-depth recheck).
  4. Query is executed within a read-only transaction capped at 100 rows and a 5-second timeout.

---

## 7. Error Handling And Reliability
* **Validation Failures:** If a query contains blocked statements, raise a custom exception that is caught by a global exception handler, returning an HTTP `400 Bad Request` with `{"detail": "Blocked: unsafe query detected"}`.
* **Database Timeouts:** Catch transaction timeouts and return an HTTP `408 Request Timeout` response.

---

## 8. Security And Access Control
* **Database Read-Only Enclosure:** The database user credential configured in `.env` must only have `SELECT` permissions.
* **AST Validation Rules:**
  * Parse SQL into a SQLGlot AST: `expression = sqlglot.parse_one(sql)`.
  * Traverse AST nodes and verify they only consist of `Select` or `With` command nodes.
  * Block statements containing syntax errors or multiple execution statements separated by semicolons (to block stacked query injection).
* **Transaction Isolation:** Prepend `SET TRANSACTION READ ONLY` or run statements under a read-only connection cursor context.

---

## 9. Observability And Operational Expectations
* **Structured Logging:** Configured in `core/logger.py`. Outputs logs in a consistent, structured format (JSON format in production).
* **Log Auditing:** Log every translation duration, database query execution latency, row counts, and flag all SQL validation violations as security warnings.

---

## 10. Performance And Scalability Expectations
* **Timeout Limits:** Capped database execution at 5.0 seconds.
* **Memory Limits:** Fetch queries with a maximum limit of 100 rows to prevent high memory usage on the backend server.
* **Concurrency:** FastAPI's async runtime handles multiple simultaneous network IO requests (like waiting for the Gemini API or Postgres read-only queries) efficiently.

---

## 11. Code Quality And Environment Tooling
* **Dependency & Env Management:** Poetry is used to manage dependencies, package environments, and build rules. High-level package requirements are specified in `pyproject.toml`, and exact pinned dependency resolution is tracked in `poetry.lock`.
* **Linting & Formatting (Ruff):** Configured in `[tool.ruff]` inside `pyproject.toml`. Enforces standard styles (pyflakes, pycodestyle, Bugbear, isort import orders) and handles auto-formatting dynamically.
* **Type Checking (Mypy):** Configured in `[tool.mypy]` inside `pyproject.toml` with strict typing enabled (`strict = true`). Statically analyzes typing before builds.
* **Advanced Code Quality Practices:**
  - **End-to-End Type Safety Generation:** Leverage the automatic `/openapi.json` schema generated by FastAPI to run a codegen script on the frontend (such as `openapi-typescript` or `Hey API`). This generates typed API fetch clients directly from the Pydantic backend models, eliminating type drift.
  - **Global Exception Shielding:** Enforce global exception middleware handlers in `app/main.py`. These catch all unhandled exceptions, log the stack trace internally, and return sanitized JSON responses to clients to prevent exposing database internals or tracebacks.
  - **Configuration Validation:** Configure custom field validators in Pydantic Settings (`core/config.py`) to verify `DATABASE_URL` format during startup (e.g. checking for `postgresql+asyncpg://`), failing fast if configs are incorrect.
  - **Git Pre-commit Hooks for Python:** Configure a `.pre-commit-config.yaml` file so git automatically runs `poetry run ruff check` and `poetry run mypy` on staged Python files before allowing commits, mirroring the frontend's Husky hooks.

## 12. Testing And Verification Strategy
* **Pytest Suite:**
  * **Harness tests (`tests/test_security.py`):** Run the validator service against a checklist of 50+ sql injection vectors, stacked queries, DDL, and DML keywords.
  * **Integration tests (`tests/test_routes.py`):** Test routes with mocked DB engine connections and mocked LLM API call responses to keep tests fast, deterministic, and cost-free.
* **Verification Commands:**
  - Env Installation: `poetry install`
  - Style & Format Check: `poetry run ruff check .` and `poetry run ruff format --check .`
  - Type Verification: `poetry run mypy app/`
  - Test Suite execution: `poetry run pytest`
