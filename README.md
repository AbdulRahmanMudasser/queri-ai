# Queri.ai

Queri.ai is an intelligent, secure, and cost-optimized natural language to SQL translation and execution engine. By combining the power of Google Gemini with local semantic schema pruning (RAG), AST-based security gates, and transaction-safe database dry-runs, Queri.ai allows users to query databases in plain English without risking schema modifications or API quota exhaustion.

---

## Key Features

* **Natural Language to SQL:** Generates PostgreSQL queries from natural English questions using `gemini-2.5-flash-lite`.
* **Cost-Optimized Schema Pruning (RAG):** Uses local CPU-based embeddings (`fastembed` with ONNX models) or Gemini embeddings to prune the database schema context, sending only mathematically relevant tables to the LLM.
* **AST Safety & Security Validation:** Walks the SQL Abstract Syntax Tree (AST) using `SQLGlot` to detect and block unsafe DML/DDL operations (e.g. `DROP`, `DELETE`, `UPDATE`, `ALTER`) before execution.
* **Safe Dry-Run Execution:** Runs an `EXPLAIN` query inside a strict read-only transaction with a 2-second statement timeout to verify syntax and catalog safety.
* **AI Results Explanation:** Translates raw tabular rows and columns back into clear, concise conversational English summaries.
* **Single-Attempt Self-Correction:** Automatically catches database syntax or AST validation failures and triggers a single feedback-driven self-correction loop to repair the query on the fly.

---

## Technology Stack

* **Backend Framework:** FastAPI (Asynchronous Python 3.12+)
* **Database Driver:** SQLAlchemy 2.0 + `asyncpg` (PostgreSQL)
* **SQL Parsing & Transpilation:** SQLGlot
* **Vector Embeddings (RAG):** FastEmbed (Local ONNX CPU) / Gemini Embeddings
* **LLM Engine:** Google Generative AI SDK (Gemini Pro / Flash)
* **Dependency Manager:** Poetry
