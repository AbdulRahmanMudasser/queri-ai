# Backend Build Plan & Architecture (FastAPI)

This document is the technical source of truth for the Backend API layer of Queri.ai (`queri-ai`). It records server-side responsibilities, clean directory layers, lifecycle management, data validation, database isolation, and security rules.

---

## 1. Platform Summary
* **Platform Name:** Backend API Service
* **Primary Responsibility:** Enforce security policies, read database metadata, prune schema context using a modular local/cloud semantic embeddings engine and custom cosine similarity matching, translate queries to SQL under a structured JSON model, validate SQL syntax and columns via AST analysis, execute queries against a read-only PostgreSQL instance, implement automated self-correction query retries, and summarize results.
* **Key Interfaces:** React Web Client, PostgreSQL Database (Neon), Google Gemini API (via `google-generativeai` SDK).
* **Primary Risks:** SQL Injection, database performance exhaustion (long-running queries), LLM hallucinations (referencing invalid columns/tables), bypass of SQL validator, high API token usage.

---

## 2. Core Technology Stack And Dependencies
* **Language & Runtime:** Python 3.11+
* **Primary Framework:** FastAPI (asynchronous API framework)
* **Web Server:** Uvicorn (ASGI web server)
* **SQL Parsing & Validation:** SQLGlot (for parsing and inspecting SQL ASTs)
* **Database Client:** SQLAlchemy (with `asyncpg` for asynchronous PostgreSQL access)
* **Vector Database:** `pgvector` (for vector embeddings storage in PostgreSQL)
* **Data Validation & Settings:** Pydantic v2 & `pydantic-settings`
* **Caching & State:** Redis (for distributed schema and context caching)
* **Templating:** Jinja2 (for prompt construction)
* **Semantic Embeddings:** `fastembed` (for local, CPU-bound ONNX embedding generation)
* **LLM SDK:** `google-generativeai` (Gemini API SDK for translation and embeddings)
* **Dependency Manager:** Poetry
* **Infrastructure:** Docker Compose (for local `pgvector` database provisioning)
* **Testing Stack:** Pytest, pytest-asyncio, HTTPX (for client testing)

---

## 3. System Boundaries And Responsibilities

### This Platform Owns
- Extracting database schemas (tables, columns, types) dynamically from PostgreSQL.
- Abstracting embeddings generation under a plug-and-play `EmbeddingsProvider` interface supporting both `LocalEmbeddings` (fastembed) and `GeminiEmbeddings` (Gemini API).
- Implementing an in-memory vector database matching system utilizing Cosine Similarity math.
- Storing few-shot SQL examples and business rules in database tables, dynamically seeded on startup.
- Dynamically retrieving query-relevant schemas using adaptive cosine similarity score thresholds (score >= 0.35, with a top-3 fallback) to construct minimized prompts.
- Forcing structured JSON schema output from Gemini to prevent parsing issues.
- Parsing SQL strings into ASTs to check command allowlists, stacked queries, and verify column/table names against cached catalogs.
- Managing Role-Based Access Control (RBAC) by physically masking database tables from AST catalogs and prompt builders for unauthorized roles.
- Managing conversational session memory via an LRU-bounded state cache to allow for contextual follow-up questions.
- Running a single-attempt self-correction query retry if execution throws errors.
- Enforcing read-only transactions with timeouts and row limits.
- Wrapping query results in structured, JSON-serializable payloads.

### This Platform Does Not Own
- Rendering user interface components or client routing.
- Maintaining permanent database state changes (read-only architecture).

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
│   │   ├── translator.py           # LLM translation & result explanation (JSON mode)
│   │   ├── validator.py            # SQLGlot AST validation rules & column catalog verification
│   │   ├── context.py              # Schema context builder, pruning, and business rules registry
│   │   ├── embeddings.py           # Abstract EmbeddingsProvider (Local CPU ONNX / Gemini Cloud API)
│   │   └── history.py              # Conversation query memory manager
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

## 4.5. Environment Configuration

To run the Queri.ai backend, a `.env` file must be present in the `backend/` directory with the following variables:

| Variable | Description | Requirement | Example |
|---|---|---|---|
| `DATABASE_URL` | PostgreSQL Async connection string | **Required** | `postgresql+asyncpg://user:pass@localhost:5432/db` |
| `GEMINI_API_KEY` | Google AI Studio Key | **Required** | `AIzaSy...` |
| `REDIS_URL` | Distributed cache for history/RAG | **Required** | `redis://localhost:6379` |
| `ENV` | Environment mode | Optional | `development` |
| `EMBEDDING_PROVIDER` | `local` or `gemini` | Optional | `local` |
| `LLM_MODEL_NAME` | Configurable model string | Optional | `models/gemini-2.5-flash-lite` |
| `SIMILARITY_THRESHOLD`| Cosine distance cutoff | Optional | `0.35` |
| `MAX_ROW_LIMIT` | Hard limits applied via SQL AST | Optional | `100` |
| `STATEMENT_TIMEOUT_MS`| Server-side query abortion timeout | Optional | `5000` |

---

## 5. Lifespan and Connection Management
* **Lifespan Manager:** The application uses FastAPI's `lifespan` context manager. On startup, it establishes the database engine connection pool and caches the database metadata in Redis. **Fail-Fast Policy:** If the database is unreachable or schema loading fails, the application will intentionally crash during startup to allow orchestration layers to restart it, preventing zombie states. On shutdown, it closes all active pools to avoid connection leaks.
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
* **Schema Reader Strategy:** Schema is queried from the PostgreSQL `information_schema` catalogs at startup and cached in a distributed **Redis** cache. Context like Few-Shot examples and Business Rules are also cached in Redis with a TTL to prevent redundant database queries.
* **SQL Generation Flow:**
  1. Frontend submits a question to `POST /api/v1/query/generate` along with optional role headers.
  2. Router calls `context.py` to retrieve relevant context.
  3. The `context.py` service runs semantic similarity search (using a local ONNX model or Gemini Cloud API via `embeddings.py` and custom cosine similarity math) on table/column definitions and prunes the schema context.
  4. The service fetches the 2 closest few-shot query examples and retrieves any matching business rules.
  5. The consolidated context is sent to `translator.py`, which prompts Gemini under a structured JSON response schema (`reasoning`, `sql`, `tables_used`).
  6. The generated SQL is validated through `validator.py`. If validation passes, the SQL and reasoning are returned.
* **Query Execution Flow:**
  1. Frontend submits SQL query to `POST /api/v1/query/execute`.
  2. Router calls the execution handler in `query.py`.
  3. The execution handler runs `validator.py` AST validation to block write/modify operations and ensure that all table and column names match the cached schema catalog.
  4. If a mismatch is detected, or if database execution returns a syntax/execution error, the execution handler intercepts the exception and invokes a single-attempt retry loop, requesting Gemini to correct the SQL based on the error output.
  5. The validated (or corrected) query is executed within a read-only transaction capped at 100 rows and a 5-second timeout.

---

## 7. Error Handling And Reliability
* **Validation Failures:** If a query contains blocked statements or invalid columns, raise a custom exception that is caught by a global exception handler, returning an HTTP `400 Bad Request`.
* **Database Timeouts:** Catch transaction timeouts and return an HTTP `408 Request Timeout` response.

---

## 8. Security And Access Control
* **Database Read-Only Enclosure:** The database user credential configured in `.env` must only have `SELECT` permissions.
* **AST Validation Rules:**
  * Parse SQL into a SQLGlot AST: `expression = sqlglot.parse_one(sql)`.
  * Traverse AST nodes and verify they only consist of `Select` or `With` command nodes.
  * Block statements containing syntax errors or multiple execution statements separated by semicolons (to block stacked query injection).
  * **AST Column and Table Verification:** Verify that every table and column node present in the AST matches our cached schema catalog. Any reference to unmapped database elements throws a validation exception.
* **Role-Based Schema Masking:** Mask sensitive tables and columns from the schema context and similarity indexes depending on the user's role headers before passing them to the translation layer. Furthermore, the `/query/execute` endpoint aggressively intercepts this header to validate manual queries against the strictly masked schema.
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
  - Local Infrastructure: `docker compose up -d`
  - Env Installation: `poetry install`
  - Database Migrations: `poetry run alembic upgrade head`
  - Style & Format Check: `poetry run ruff check .` and `poetry run ruff format --check .`
  - Type Verification: `poetry run mypy app/`
  - Test Suite execution: `poetry run pytest`
