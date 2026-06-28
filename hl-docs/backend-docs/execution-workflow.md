# Backend Execution Workflow

## 1. Document Purpose
This document is the delivery source of truth for the Backend layer. It tracks implementation order, execution status, dependencies, blockers, and completion evidence for backend-specific work.

## 2. Linked Source Documents
* **Product Source:** [queri-ai-prd.md](../queri-ai-prd.md)
* **Platform Build Plan:** [backend-build-plan.md](./backend-build-plan.md)
* **Phase Template Source:** [../templates/phase-template.md](../templates/phase-template.md)

## 3. Platform Baseline
* **Platform Name:** Backend
* **Primary Runtime:** FastAPI (Python 3.11+)
* **Target Environments:** local, staging, production
* **Deployment Target:** container (e.g. Render, Fly.io, or AWS)
* **Branch Strategy:** feature branches merged into a main integration branch
* **Required Verification Commands:**
  - `poetry run ruff check .`
  - `poetry run mypy app/`
  - `poetry run pytest`
* **Release Gates:**
  - Database connection verified
  - SQL AST validation logic fully tested for safety
  - API schemas and response structures validated

## 4. Status Definitions
- **Planned:** Identified but not ready to start.
- **Ready:** Fully scoped and unblocked.
- **In Progress:** Actively being implemented.
- **Blocked:** Cannot proceed due to a dependency or unresolved issue.
- **Completed:** Implemented and verified.
- **Cancelled:** Intentionally dropped from scope.

## 5. Platform Definition Of Done
Every completed phase must satisfy all of the following:
1. Scope matches the linked phase document.
2. Build, compile, or bundle succeeds for the target platform.
3. Required tests, lint checks, and type checks pass.
4. Functional verification has been performed and recorded.
5. Any required docs, configs, or environment changes are updated.
6. Evidence is logged in the linked phase file.

## 6. Current Active Phase
* **Current Phase:** Phase 04 - Safe Query Execution & AI Explanation
* **Status:** In Progress
* **Owner:** Abdul Rahman
* **Linked Phase Doc:** [phase-04-safe-execution.md](./phase-04-safe-execution.md)
* **Immediate Goal:** Execute validated SQL queries inside a read-only transaction with a 5-second timeout and 100-row limit, and explain results via Gemini.
* **Current Blockers:** None
* **Next:** None (Backend MVP Complete)

## 7. Ready Queue
- None

## 8. Phase Register
| Phase | Name | Status | Priority | Owner | Depends On | Linked File | Target Window |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | Scaffolding & Core Configuration | Completed | High | Abdul Rahman | None | [phase-01-scaffolding.md](./phase-01-scaffolding.md) | 2026-06-28 |
| 02 | Database Connection & Schema Reader | Completed | High | Abdul Rahman | Phase 01 | [phase-02-database-schema.md](./phase-02-database-schema.md) | 2026-06-28 |
| 03 | SQL Generation & AST Validation Service | Completed | High | Abdul Rahman | Phase 02 | [phase-03-sql-generation.md](./phase-03-sql-generation.md) | 2026-06-29 |
| 04 | Safe Query Execution & AI Explanation | In Progress | High | Abdul Rahman | Phase 03 | [phase-04-safe-execution.md](./phase-04-safe-execution.md) | 2026-06-29 |

## 9. Blockers And Risks

### Active Blockers
- None

### Execution Risks
- Schema structure changes dynamically or is modified in production
- LLM API changes or rate limits disrupt automated queries

## 10. Decision Log
Record execution-relevant decisions here when they affect sequencing, scope, or approach.
| Date | Decision | Reason | Impact |
| :--- | :--- | :--- | :--- |
| 2026-06-28 | Use FastAPI + Python Stack | Async native performance and excellent Python AI/DB ecosystem (SQLGlot, Pydantic) | Lean and lightweight API runtime |

## 11. Execution Log
Use this section to track material execution updates, not every minor edit.
| Date | Phase / Name | Status Change | Summary | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| 2026-06-28 | Phase 01 / Scaffolding & Core Configuration | Planned -> Ready | Scoping and configurations finalized; document created and verified. | Phase 01 document loaded. |
| 2026-06-28 | Phase 01 / Scaffolding & Core Configuration | Ready -> Completed | Poetry env, Pydantic Settings, structured logger, health endpoint, pre-commit hooks, and tests implemented. ruff, mypy, pytest all pass. | [Evidence](#11-execution-log) |
| 2026-06-28 | Phase 02 / Database & Schema Reader | Planned -> Completed | Async engine, session dependency, metadata reader with caching, schema endpoint, and tests implemented. ruff, mypy, pytest all pass. | [Evidence](#11-execution-log) |
| 2026-06-29 | Phase 03 / SQL Generation & AST Validation Service | Planned -> Completed | Translator with Gemini API, validator with SQLGlot safety rule analysis, generate endpoint, and tests implemented. ruff, mypy, pytest all pass. | [Evidence](#11-execution-log) |
| 2026-06-29 | Phase 04 / Safe Query Execution & AI Explanation | Planned -> In Progress | Scoped implementation plan, setup tasks, and initiated development. | Phase 04 plan approved. |

## 12. Workflow Rules
- Every phase listed in the phase register must have a real linked file.
- If a phase becomes too large, split it into sub-phases such as `phase-02a-*` and `phase-02b-*`.
- Move a phase to `Ready` only when prerequisites, scope, and verification expectations are clear.
- Move a phase to `Completed` only after verification evidence exists in the linked phase document.
- Update this file during execution, not only at the end of work.
