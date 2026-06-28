# Phase 03: SQL Preview Console & Centralized Status Console

## 1. Phase Purpose
This document controls execution for rendering generated SQL queries in a terminal code preview block, and implementing the centralized status warning bar (No Inline Errors Policy).

## 2. Feature Objective
* **Phase Goal:** Render generated SQL inside a dark code editor preview box with an execution trigger button, and route all load states, warnings, and safety errors to a unified console status bar.
* **User Or System Outcome:** The user gets transparency by seeing the generated SQL first, can click a glowing "Execute Query" button, and sees all safety block warnings in a clean, central console without UI layout shifting.
* **In Scope:** `src/components/SQLPreview.tsx` (SQL block terminal), Centralized Status Bar container, API client generation call (`POST /api/v1/query/generate`), and state machines in `App.tsx`.
* **Out Of Scope:** Tabular results rendering, AI explanation parsing.

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** [Phase 02 - Schema Tree & Chat Console UI](./phase-02-schema-chat-console.md) -> Must be marked [x] in the Local Tracker.
* **Downstream Tasks (Unlocks):** [Phase 04 - Results Spreadsheet Grid & AI Explanation Card](./phase-04-results-explanation.md)
* **Target Git Commit Prefix:** `feat(web-sql-preview): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** [YYYY-MM-DD to YYYY-MM-DD]
* **Related PRD Section:** Story 2 (SQL Transparency), Feature 3 (SQL Generation), Feature 4 (SQL Validation), and Section 10 (Acceptance Criteria)
* **Related Build Plan Section:** Section 7 (Error Handling) and Section 11 (No Inline Errors)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** None required.
* **Database/Index Changes:** Requires the backend `POST /api/v1/query/generate` endpoint to be active.
* **Feature Flags / Config Switches:** None.
* **Required Reusable Utilities:**
  - Import `fetchSchema` and API hooks.

## 6. API & Data Contract Specifications
* **Endpoint:** `POST /api/v1/query/generate`
* **Response payload mapping:**
  ```typescript
  interface SQLResponse {
    sql: string;
  }
  ```

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:**
  - Below the text area, a terminal-like container displays generated SQL (e.g. green courier font on charcoal background) and a green "Run Query" button.
  - A central status console box lights up with status text (e.g., "AI is generating SQL...", "Safety check passed", "Blocked: Unsafe query detected" in glowing red).
* **System Behavior Change:** Frontend calls the SQL generator on question submission, pipes response to the preview block, and intercepts errors to display them exclusively in the central status bar.

## 8. Acceptance Criteria
- SQL code preview renders within a terminal-like block. No inline styles are used.
- "Run Query" button triggers query execution.
- No error messages are displayed inline below the textarea or SQL preview; all errors (network, validation, API) are captured and displayed exclusively inside the Centralized Status Bar.
- Typing in the input field or submitting clears the previous status and resets the error states.
- Codebase contains zero `// @ts-ignore` flags.

## 9. Implementation Steps (Component Audit)

### A. Data Layer
* [MODIFY] `frontend/src/utils/api.ts`:
  - [ ] Write `generateSQL(question: string): Promise<SQLResponse>` fetch call.

### B. Controller / API Layer
* `No backend routes in this phase`

### C. Client / UI Layer
* [NEW] `frontend/src/components/SQLPreview.tsx`:
  - [ ] Render a dark code terminal card.
  - [ ] Format the SQL statement in a code block with line breaks.
  - [ ] Add the execution control button ("Run Query") which triggers the execute callback.
* [NEW] `frontend/src/components/StatusConsole.tsx` (Centralized Status Bar):
  - [ ] Create a widget that renders status labels, warning icons, and error texts.
  - [ ] Style success states (green), pending states (pulse yellow), and error states (glowing red border/text).
* [MODIFY] `frontend/src/App.tsx`:
  - [ ] Add state variables: `generatedSql`, `statusMessage`, `isError`, `loadingState`.
  - [ ] Connect `generateSQL` trigger on submit.
  - [ ] Integrate `StatusConsole` at the center of the console layout and conditionally render `SQLPreview` when SQL is generated.

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** Prompt injection attacks trying to display bad formatting on SQL.
* **Operational Risks:** Empty SQL returns or layout jumps.
* **Rollback Approach:** Hide SQL preview and show error banners.

## 11. Verification Protocol (Definition of Done)

### A. Automated Suite
* **Exact Command:** `npm run typecheck && npm run lint`

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Happy Path Gen | Submit question "hotels in Lahore" | Terminal displays generated SQL, status shows "Check Passed" | 200 OK |
| Safety Block Path | Submit "delete bookings" | Central status bar turns red showing "Safety Violation: blocked" | 400 Bad Request |
| Loading Path | Click Submit | Central bar pulses "Generating query..." and locks inputs | N/A |

### C. Evidence To Capture
- Screenshot of generated SQL query shown in the terminal console card.
- Screenshot of safety warning banner displayed in red inside the central StatusConsole.

## 12. Execution Notes
* **Status:** Planned
* **Started At:** [YYYY-MM-DD]
* **Completed At:** [YYYY-MM-DD]
* **Blockers Encountered:** None.
* **Notes:** None.
