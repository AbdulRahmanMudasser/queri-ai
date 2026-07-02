# Queri.ai API Collection

This directory contains the `queri-ai.json` Postman Collection, which serves as the official API contract and documentation for the Queri.ai backend.

Whether you are a new frontend developer exploring the available endpoints, or a backend engineer testing new routes, this collection is your starting point.

## Quick Start for Developers

To interact with the API, you need to import the collection and configure your environment variables.

### 1. Import the Collection
* Download and open Postman.
* Click **Import** (top left).
* Select `queri-ai.json` from this folder.

### 2. Configure Your Environment
The collection uses a variable for the base URL. There is **no authentication** required to hit these APIs locally.

| Variable Name | Description | Example (Local) |
|---|---|---|
| `baseUrl` | The root URL of the backend API router. | `http://localhost:8000/api/v1` |

*(Note: The collection already defaults `baseUrl` to `http://localhost:8000/api/v1` so you might not even need an explicit environment for local testing).*

### 3. API Endpoints Overview
The Queri.ai backend is an asynchronous FastAPI application that provides the following endpoints:

* **GET `/health`**: Check the status of the API and environment.
* **GET `/schema`**: Retrieves the cached database schema (tables and definitions) used for schema pruning and RAG.
* **POST `/query/generate`**: Takes a natural language `question` and translates it into PostgreSQL using Gemini, returning both the `sql` and `reasoning`. Accepts an optional `session_id` in the payload for conversational memory, and an `X-User-Role` header for RBAC masking.
* **POST `/query/execute`**: Takes a validated `sql` query, executes it safely (in a read-only transaction, limited to 100 rows, with a 5s statement timeout), and returns the `columns` and `rows`. Accepts an `X-User-Role` header to enforce schema masking prior to execution.
* **POST `/query/explain`**: Takes the `question`, `sql`, `columns`, and `rows` and generates a concise, conversational English explanation of the SQL results.

## For Backend Engineers (Maintaining the API)

* **Keep it Synced:** If you add a new route to the FastAPI router (e.g. in `app/api/v1/endpoints/`), change a Pydantic payload schema, or update a header requirement, you **must** update the `queri-ai.json` collection to reflect the change.
* **Save Examples:** When creating a new request in the collection, always hit "Save Response" for both a successful `200 OK` and expected error states (e.g. `400 Bad Request`, `408 Request Timeout`, or `503 Service Unavailable`). This provides mock data for the frontend team.
* **Use Variables:** Do not hardcode `http://localhost:8000/api/v1` into request URLs. Always use `{{baseUrl}}` so the collection works seamlessly across different deployments.
