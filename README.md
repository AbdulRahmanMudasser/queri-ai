# Queri.ai

Queri.ai is a backend API designed to translate natural language questions into safe, read-only PostgreSQL queries. It utilizes Google Gemini for LLM translation, FastEmbed for local RAG-based schema pruning, and SQLGlot for strict AST-level query validation.

---

## Key Features

* **Natural Language to SQL:** Generates PostgreSQL queries from natural English questions using `gemini-2.5-flash-lite`.
* **Schema Pruning via RAG:** Uses local CPU embeddings (`fastembed`) to prune the database schema context based on cosine similarity, passing only relevant tables to the LLM. Vector embeddings are globally cached in **Redis** with math computations heavily offloaded asynchronously.
* **Few-Shot Examples & Business Rules:** Retrieves similar past query examples using `pgvector` and injects them alongside static business rules into the LLM context to improve accuracy.
* **AST Safety Validation:** Walks the SQL Abstract Syntax Tree (AST) using `SQLGlot` to aggressively block unsafe DML/DDL operations (e.g., `INSERT`, `DROP`, `DELETE`, `UPDATE`, `ALTER`) and validates all table/column names against the actual database schema.
* **Query Limit Enforcement:** Automatically parses and overrides the `LIMIT` clause to a maximum of 100 rows to prevent massive data pulls.
* **Single-Attempt Self-Correction:** Detects database syntax or validation errors and automatically prompts the LLM once with the error message to attempt a self-correction.
* **AI Results Explanation:** Translates the raw tabular SQL execution results back into concise conversational English.
* **Conversational Memory:** Maintains an asynchronous **distributed Redis cache** of session history to allow users to ask follow-up questions contextually, reclaiming memory cleanly via strict TTLS.
* **Role-Based Access Control (RBAC):** Employs strict physical schema masking based on `X-User-Role` headers, completely blocking generation and execution against unauthorized tables.

---

## Technology Stack

* **Backend Framework:** FastAPI (Asynchronous Python 3.11+)
* **Database & ORM:** SQLAlchemy 2.0 + `asyncpg` (PostgreSQL)
* **Distributed Cache:** Redis (Asyncio)
* **Vector Extension:** `pgvector`
* **SQL Parsing & Validation:** SQLGlot
* **Vector Embeddings (RAG):** FastEmbed (Local ONNX CPU)
* **LLM Engine:** Google Generative AI SDK
* **Prompt Templating:** Jinja2
* **Dependency Manager:** Poetry
* **Migrations:** Alembic
* **Infrastructure:** Docker Compose
