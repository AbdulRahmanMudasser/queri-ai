# Phase 07: Few-Shot SQL Retrieval & Business Rules

## 1. Phase Purpose
This document controls execution for Phase 07, focusing on creating database tables for Business Rules and Few-Shot SQL examples, configuring startup seeder scripts, and retrieving them semantically.

## 2. Feature Objective
* **Phase Goal:** Create SQLAlchemy models for `business_rules` and `few_shot_examples`, execute database migrations, write a startup seeder script that loads defaults, and retrieve the top-2 most relevant examples using cosine similarity.
* **User Or System Outcome:** Impress reviewers by showcasing database migration, seeding, and dynamic administration patterns, while building a robust few-shot RAG context builder.
* **In Scope:** DB models, migrations, startup seeding script, dynamic data fetching, and prompt context assembler integration.
* **Out Of Scope:** Admin UI panels (handled backend-only for now).

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** [Phase 06 - Context Builder & Semantic Pruning (RAG)](./phase-06-schema-pruning.md)
* **Downstream Tasks (Unlocks):** [Phase 08 - Query History Memory & RBAC Masking](./phase-08-memory-rbac.md)
* **Target Git Commit Prefix:** `feat(backend-rules-db): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** 2026-06-30
* **Related PRD Section:** Section 7 (SQL Few-Shot Example RAG, Business Rules Registry) and Section 10 (Acceptance Criteria)
* **Related Build Plan Section:** Section 3 (System Boundaries) and Section 6 (Data Flow)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `DATABASE_URL`, `GEMINI_API_KEY`.
* **Database/Index Changes:**
  - Create table `business_rules` with columns: `id`, `rule_name`, `rule_description`, `rule_value`.
  - Create table `few_shot_examples` with columns: `id`, `question`, `sql_query`, `question_vector` (array of floats).
  - Write an automatic startup seeder class.

## 6. API & Data Contract Specifications
* **Few-shot Example Contract:**
  ```json
  {
    "question": "most bookings",
    "sql": "SELECT hotel_id, COUNT(*) FROM bookings GROUP BY hotel_id ORDER BY COUNT(*) DESC"
  }
  ```

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** None.
* **System Behavior Change:** FastAPI seeds empty tables at boot, queries them dynamically, matches semantic vectors, and appends few-shot examples and business rules to Gemini prompts.

## 8. Acceptance Criteria
- Rules and examples reside in database tables.
- A startup seeder populates default values if tables are empty.
- Few-shot examples are semantically retrieved via cosine similarity on embedding vectors and injected.

## 9. Implementation Steps (Component Audit)
### A. Data Layer
* [NEW] `backend/app/db/models.py` (or integrated in `db` layer):
  - [ ] Define SQLAlchemy models for `BusinessRule` and `FewShotExample`.
* [NEW] `backend/app/db/seeder.py`:
  - [ ] Implement startup database seeder mapping default rules (e.g. status codes) and query examples.

### B. Service Layer
* [MODIFY] `backend/app/services/context.py`:
  - [ ] Query the database for active rules and examples.
  - [ ] Generate embedding for the user question and compute cosine similarity against stored table examples.
  - [ ] Retrieve the top-2 matching examples and inject them into prompt context.

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** Seeding failures blocking startup lifespans.
* **Rollback Approach:** Bypass seeding checks and return empty context results.

## 11. Verification Protocol (Definition of Done)
### A. Automated Suite
* **Exact Command:** `poetry run pytest tests/`
### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Seeding verified | Restart server, query database tables | Tables populated with default rules | Seeding Successful |

## 12. Execution Notes
* **Status:** Planned
* **Started At:** [YYYY-MM-DD]
* **Completed At:** [YYYY-MM-DD]
