# Phase 06: Context Builder & Semantic Schema Pruning (RAG)

## 1. Phase Purpose
This document controls execution for Phase 06, focusing on implementing a modular local/cloud embeddings engine and custom cosine similarity calculations to prune table schemas using adaptive score-based thresholds.

## 2. Feature Objective
* **Phase Goal:** Define a plug-and-play `EmbeddingsProvider` interface, implement `LocalEmbeddings` (using a 45MB CPU ONNX model via `fastembed`), implement `GeminiEmbeddings` (using the Gemini API), write a custom cosine similarity matcher, and prune table schemas using an adaptive score-based threshold (score >= 0.35, with a top-3 fallback).
* **User Or System Outcome:** Showcase advanced token optimization capabilities by dynamically shrinking/expanding the prompt schema context based on mathematical relevance scores, preserving Free Tier API quota.
* **In Scope:** `EmbeddingsProvider` interface, `LocalEmbeddings` implementation, custom cosine similarity calculations, adaptive score pruning, and `context.py` schema builder.
* **Out Of Scope:** SQL translation or execution logic edits.

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** [Phase 05 - Structured JSON Output & Self-Correction](./phase-05-structured-correction.md)
* **Downstream Tasks (Unlocks):** [Phase 07 - Few-Shot SQL Retrieval & Business Rules](./phase-07-fewshot-rules.md)
* **Target Git Commit Prefix:** `feat(backend-pruning): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** 2026-06-30
* **Related PRD Section:** Section 7 (Context Builder Service) and Section 10 (Acceptance Criteria)
* **Related Build Plan Section:** Section 6 (Data Flow) and Section 8 (Security)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `DATABASE_URL`, `GEMINI_API_KEY`, `EMBEDDING_PROVIDER` (defaults to "local").
* **Database/Index Changes:** Embeddings index configuration in memory.

## 6. API & Data Contract Specifications
* **Schema Pruning Input:** Natural language question string.
* **Schema Pruning Output:** List of top-N relevant table schema dicts.

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** None.
* **System Behavior Change:** Generation prompt uses only semantically relevant tables, resulting in faster and cheaper API calls. The system logs the exact table count and prompt character size for every translation to verify pruning.

## 8. Acceptance Criteria
- Code defines a modular, interchangeable `EmbeddingsProvider` abstract interface.
- Local provider generates embeddings using a fast CPU-based ONNX model (`fastembed`) without making network calls.
- Cosine similarity is calculated in-house using basic math/numpy.
- Generation prompt context is dynamically limited using adaptive score thresholds (similarity_score >= 0.35, falling back to top-3 if no table crosses the limit).
- Every translation call outputs a clear log statement indicating the table count and prompt length.

## 9. Implementation Steps (Component Audit)
### A. Service Layer
* [NEW] `backend/app/services/embeddings.py`:
  - [x] Create the `EmbeddingsProvider` base interface class.
  - [x] Implement `LocalEmbeddings` using `fastembed` library.
  - [x] Implement `GeminiEmbeddings` calling the Gemini text embeddings API.
* [NEW] `backend/app/services/context.py`:
  - [x] Build context assembler that generates question embeddings, calculates cosine similarity against stored table/column description vectors, and filters tables crossing the 0.35 threshold (with top-3 fallback).

### B. Controller / API Layer
* [MODIFY] `backend/app/api/v1/endpoints/query.py`:
  - [x] Integrate `context.py` schema builder into the generation flow.

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** Incorrectly filtering out a table that was actually needed for a join.
* **Rollback Approach:** Bypass dynamic context builder and send the complete schema catalog.

## 11. Verification Protocol (Definition of Done)
### A. Automated Suite
* **Exact Command:** `poetry run pytest tests/`
### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Schema Pruned | Question: "Show hotels in Lahore" | Only the `hotels` table schema is injected into prompt context | 200 OK |

## 12. Execution Notes
* **Status:** Completed
* **Started At:** 2026-06-29
* **Completed At:** 2026-06-29
