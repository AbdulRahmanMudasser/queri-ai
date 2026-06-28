# Web Execution Workflow

## 1. Document Purpose
This document is the delivery source of truth for the Web layer. It tracks implementation order, execution status, dependencies, blockers, and completion evidence for web-specific work.

## 2. Linked Source Documents
* **Product Source:** [sql-assistant-prd.md](../sql-assistant-prd.md)
* **Platform Build Plan:** [web-build-plan.md](./web-build-plan.md)
* **Phase Template Source:** [../templates/phase-template.md](../templates/phase-template.md)

## 3. Platform Baseline
* **Platform Name:** Web
* **Primary Runtime:** React + Vite (SPA)
* **Target Environments:** local, preview, production
* **Deployment Target:** Static web hosting (Vercel, Netlify, Cloudflare Pages, S3, or direct FastAPI serving)
* **Branch Strategy:** feature branches merged into a main integration branch
* **Required Verification Commands:**
  - `npm run typecheck`
  - `npm run lint`
  - `npm run build`
* **Release Gates:**
  - Responsive layout verified on desktop and mobile viewports
  - API connection to FastAPI backend validated

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
* **Current Phase:** Phase 01 - Vite Scaffolding & Styling System Setup
* **Status:** Ready
* **Owner:** Abdul Rahman
* **Linked Phase Doc:** [phase-01-scaffolding-theme.md](./phase-01-scaffolding-theme.md)
* **Immediate Goal:** Set up the React + Vite + TypeScript project structure, configure ESLint and Husky, and define the custom CSS HSL theme.
* **Current Blockers:** None

## 7. Ready Queue
- [Phase 02 - Schema Tree & Chat Console UI](./phase-02-schema-chat-console.md)
- [Phase 03 - SQL Preview Console & Centralized Status Console](./phase-03-sql-preview-status.md)
- [Phase 04 - Results Spreadsheet Grid & AI Explanation Card](./phase-04-results-explanation.md)

## 8. Phase Register
| Phase | Name | Status | Priority | Owner | Depends On | Linked File | Target Window |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | Vite Scaffolding & Styling System Setup | Ready | High | Abdul Rahman | None | [phase-01-scaffolding-theme.md](./phase-01-scaffolding-theme.md) | [YYYY-MM-DD to YYYY-MM-DD] |
| 02 | Schema Tree & Chat Console UI | Planned | High | Abdul Rahman | Phase 01 | [phase-02-schema-chat-console.md](./phase-02-schema-chat-console.md) | [YYYY-MM-DD to YYYY-MM-DD] |
| 03 | SQL Preview Console & Centralized Status Console | Planned | High | Abdul Rahman | Phase 02 | [phase-03-sql-preview-status.md](./phase-03-sql-preview-status.md) | [YYYY-MM-DD to YYYY-MM-DD] |
| 04 | Results Spreadsheet Grid & AI Explanation Card | Planned | High | Abdul Rahman | Phase 03 | [phase-04-results-explanation.md](./phase-04-results-explanation.md) | [YYYY-MM-DD to YYYY-MM-DD] |

## 9. Blockers And Risks

### Active Blockers
- None

### Execution Risks
- CORS policy issues between web port and backend port during local development
- Handling very wide query results without causing layout clipping or stretching

## 10. Decision Log
Record execution-relevant decisions here when they affect sequencing, scope, or approach.
| Date | Decision | Reason | Impact |
| :--- | :--- | :--- | :--- |
| 2026-06-28 | Use React + Vite (SPA) | Simpler hosting, fast compilation, and zero redundant server runtimes when paired with FastAPI | Frontend is a pure static asset folder |

## 11. Execution Log
Use this section to track material execution updates, not every minor edit.
| Date | Phase / Name | Status Change | Summary | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| 2026-06-28 | Phase 01 / Vite Scaffolding & Styling Setup | Planned -> Ready | Scoping and stylesheets initialized; document created and verified. | Phase 01 document loaded. |

## 12. Workflow Rules
- Every phase listed in the phase register must have a real linked file.
- If a phase becomes too large, split it into sub-phases such as `phase-02a-*` and `phase-02b-*`.
- Move a phase to `Ready` only when prerequisites, scope, and verification expectations are clear.
- Move a phase to `Completed` only after verification evidence exists in the linked phase document.
- Update this file during execution, not only at the end of work.
