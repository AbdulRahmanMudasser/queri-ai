# Phase 10: System Resilience and Configuration Standardization

<!---
DOCUMENTATION RULES:
1. File naming:
   - Standard: phase-[00]-[name].md (e.g., phase-01-auth-setup.md)
   - Large/Sub-phase: phase-[00][a/b/c]-[name].md (e.g., phase-01a-jwt-logic.md)
2. Workflow Tracker Link:
   - Local Platform Tracker: [execution-workflow.md](./execution-workflow.md)
3. High-Level PRD Link:
   - Project PRD: [project-name-prd.md](../[project-name]-prd.md)
--->

## 1. Phase Purpose
This document controls execution for Phase 10. The goal is to harden the backend against silent infrastructure failures, centralize all application configuration, and eliminate brittle prompt construction logic.

## 2. Feature Objective
* **Phase Goal:** Fix zombie startup states, remove hardcoded limits, and migrate to Jinja2 prompts.
* **User Or System Outcome:** Immediate visibility into startup failures and easier configuration management.
* **In Scope:** `main.py` lifespan modifications, `config.py` centralization, Jinja2 templating.
* **Out Of Scope:** Any new API features.

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** Phase 09 -> Must be marked [x] in the Local Tracker.
* **Downstream Tasks (Unlocks):** Future feature work.
* **Target Git Commit Prefix:** `refactor(backend-resilience): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** July 2026
* **Related PRD Section:** N/A (Technical Debt Resolution)
* **Related Build Plan Section:** 11. Code Quality And Environment Tooling

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `LLM_MODEL_NAME`, `SIMILARITY_THRESHOLD`, `MAX_ROW_LIMIT`
* **Database/Index Changes:** None
* **Feature Flags / Config Switches:** None
* **Seed / Fixture Requirements:** None
* **Required Reusable Utilities:**
  - Import `jinja2` for prompt building.

## 6. API & Data Contract Specifications
* **Endpoint:** N/A
* **Request Schema (Zod/JSON):** N/A
* **Response Schema (JSON):** N/A

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** None natively visible to end-user, system will fail fast if DB is down.
* **System Behavior Change:** Application will crash at startup if DB connection fails, rather than running in zombie state.
* **Error States To Support:** Startup exceptions.
* **Accessibility / Platform Constraints:** None

## 8. Acceptance Criteria
- [ ] Application fails to start if database is unavailable.
- [ ] All magic numbers are moved to `core/config.py` and mapped to `.env`.
- [ ] `translator.py` uses Jinja2 templates instead of f-strings.

## 9. Implementation Steps (Component Audit)

### A. Data Layer
* [MODIFY] `app/main.py`:
  - **Target Anchor:** `lifespan` function
  - [ ] Remove `except Exception` swallowing for DB tables and schema loading. Raise error instead.

* [MODIFY] `app/core/config.py`:
  - **Target Anchor:** `Settings` class
  - [ ] Add properties for limits, model names, and timeouts with sensible defaults (e.g., `gemini-2.5-flash-lite`, `0.35`).
  - [ ] Add `REDIS_URL` and make it strictly required without a default.
* [NEW] `.env.example`:
  - [ ] Create file in the project root containing all required environment variables so new developers know what to provide.

### B. Controller / API Layer
* [NEW] `app/templates/prompts/`:
  - [ ] Create a dedicated directory to cleanly isolate and store all `.j2` prompt templates.
* [MODIFY] `app/services/translator.py`:
  - **Target Anchor:** `_build_prompt` functions
  - [ ] Replace with Jinja2 template rendering loading from `app/templates/prompts/`.

### C. Client / UI Layer
* N/A

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** Prompt structure might subtly change when migrating to Jinja2, affecting LLM outputs.
* **Operational Risks:** Deployment failures if DB isn't ready during server boot.
* **Rollback Approach:** Revert to f-strings or previous startup error-swallowing logic if necessary.

## 11. Verification Protocol (Definition of Done)

### A. Automated Suite
* **Exact Command:** `poetry run pytest`

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Bad DB Connection | Start FastAPI server | Server crashes immediately | N/A |
| Generate Query | Run standard translation | Generates valid SQL using Jinja2 prompt | 200 OK |

### C. Evidence To Capture
- [Terminal output of server crashing on bad DB]
- [Terminal output of pytest passing]

## 12. Execution Notes
* **Status:** Planned
* **Started At:** July 2026
* **Completed At:** July 2026
* **Blockers Encountered:** None
* **Notes:** None
