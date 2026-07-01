# Phase 08: Query History Memory & RBAC Masking

## 1. Phase Purpose
This document controls execution for Phase 08, focusing on adding session conversation memory for follow-up questions and masking schemas depending on user roles.

## 2. Feature Objective
* **Phase Goal:** Track historical query threads (Conversational Memory) and restrict schema elements based on user role headers.
* **User Or System Outcome:** Enables interactive conversational querying and prevents schema exposure or query writing targeting unauthorized database fields.
* **In Scope:** Session history adapters, role-based table filters, and header parser middlewares.
* **Out Of Scope:** Persistent authentication servers (stateless session scope only).

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** [Phase 07 - Few-Shot SQL Retrieval & Business Rules](./phase-07-fewshot-rules.md)
* **Downstream Tasks (Unlocks):** None (Backend MVP Complete).
* **Target Git Commit Prefix:** `feat(backend-memory-rbac): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** 2026-06-30
* **Related PRD Section:** Section 7 (Role-Based Schema Masking) and Section 16 (Sensitive Data Handling)
* **Related Build Plan Section:** Section 6 (Data Flow) and Section 8 (Security)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `DATABASE_URL`, `GEMINI_API_KEY`.
* **Database/Index Changes:** Role mapping configs.

## 6. API & Data Contract Specifications
* **Endpoints:**
  - `POST /api/v1/query/generate` with headers: `X-User-Role: Staff` or `X-User-Role: Admin`.
  - Input body: `{"question": "Only confirmed ones", "session_id": "session-123"}`

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** Enables conversational follow-ups.
* **System Behavior Change:** Restricts query execution and SQL generation dynamically if a user role lacks permissions on requested fields.

## 8. Acceptance Criteria
- Conversational follow-ups retrieve previous query mappings.
- Role-based schema masking blocks sensitive tables (e.g. `salaries`) from being referenced in prompt schemas.

## 9. Implementation Steps (Component Audit)
### A. Service Layer
* [NEW] `backend/app/services/history.py`:
  - Create session history registry tracking question-SQL pairs.
* [MODIFY] `backend/app/services/context.py`:
  - Intercept role headers and filter output schema metadata before vector searching or prompt building.

### B. Controller / API Layer
* [MODIFY] `backend/app/api/v1/endpoints/query.py`:
  - Read role headers and support session identifiers in payloads.

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** Session history leakages or memory blowups.
* **Rollback Approach:** Disable role checks and conversational sessions, falling back to stateless queries.

## 11. Verification Protocol (Definition of Done)
### A. Automated Suite
* **Exact Command:** `poetry run pytest tests/`
### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| RBAC Masking | User role: `Staff` query table `salaries` | Blocked during context assembly | 400 Bad Request |

## 12. Execution Notes
* **Status:** Planned
* **Started At:** 2026-07-01
* **Completed At:** 2026-07-01
