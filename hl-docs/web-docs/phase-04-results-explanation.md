# Phase 04: Results Spreadsheet Grid & AI Explanation Card

## 1. Phase Purpose
This document controls execution for displaying database execution results in a spreadsheet-like grid, rendering AI-generated textual summaries, and maintaining client-side query history.

## 2. Feature Objective
* **Phase Goal:** Render query columns and rows in an interactive table, display natural language summaries in a card, and maintain past query actions in a local storage sidebar panel.
* **User Or System Outcome:** The user gets immediate insight into their data via a formatted table, reads the AI-generated text summary, and can recall past queries from their history stack.
* **In Scope:** `src/components/ResultsTable.tsx` (data grid), `src/components/Explanation.tsx` (AI card), `src/components/HistoryPanel.tsx` (history sidebar), API client execution calls, and `localStorage` caching logic.
* **Out Of Scope:** Exporting CSV (deferred to V2), rendering graphical charts (deferred to V2).

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** [Phase 03 - SQL Preview Console & Centralized Status Console](./phase-03-sql-preview-status.md) -> Must be marked [x] in the Local Tracker.
* **Downstream Tasks (Unlocks):** None (Web Frontend MVP Complete).
* **Target Git Commit Prefix:** `feat(web-results-history): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** [YYYY-MM-DD to YYYY-MM-DD]
* **Related PRD Section:** Feature 5 (Query Execution), Feature 6 (Result Visualization), Feature 7 (AI Explanation), and Section 10 (Acceptance Criteria)
* **Related Build Plan Section:** Section 5 (Data Flow) and Section 6 (Domain Models)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** None required.
* **Database/Index Changes:** Requires the backend `POST /api/v1/query/execute` and `POST /api/v1/query/explain` endpoints to be active.
* **Feature Flags / Config Switches:** None.
* **Required Reusable Utilities:**
  - Import `fetchSchema` and API client wrappers.

## 6. API & Data Contract Specifications

### A. Execution Client Contract
* **Payload mapping:**
  ```typescript
  interface ExecutionResponse {
    columns: string[];
    rows: any[][];
  }
  ```

### B. Explanation Client Contract
* **Payload mapping:**
  ```typescript
  interface ExplanationResponse {
    explanation: string;
  }
  ```

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:**
  - A scrollable spreadsheet grid shows database records below the code terminal block.
  - A card displaying a light-violet glow shows an AI summary of findings (e.g., "Marriott had 521 bookings...").
  - Left sidebar has a toggleable log showing past queries (e.g., "Show hotels booked last month - 2 mins ago"). Clicking one reloads the SQL and results.
* **System Behavior Change:** Executing a query triggers backend runner, renders the grid, runs the AI describer, and stores query parameters inside `localStorage`.

## 8. Acceptance Criteria
- Result table displays headers and rows aligned in a clean, scrollable box with border layouts.
- Empty states (zero rows returned) render a clean "No records found" label.
- AI Explanation card displays text summary. Card is hidden while executing and displays a pulsing loading state when explaining.
- Clicking history records reloads the query states (loading prompts, SQL, and grid data).
- The "No Inline Errors Policy" is maintained: any execution timeout or database error routes to the central StatusConsole.
- Code compiles without warnings or errors.

## 9. Implementation Steps (Component Audit)

### A. Data Layer
* [MODIFY] `frontend/src/utils/api.ts`:
  - [ ] Write `executeSQL(sql: str): Promise<ExecutionResponse>` API fetch call.
  - [ ] Write `explainResults(question: str, sql: str, data: ExecutionResponse): Promise<ExplanationResponse>` API fetch call.

### B. Controller / API Layer
* `No backend routes in this phase`

### C. Client / UI Layer
* [NEW] `frontend/src/components/ResultsTable.tsx`:
  - [ ] Render standard HTML `<table>` styled with border collapse, cell borders, and sticky header positioning.
  - [ ] Set up scroll wrappers to handle table width overflow without layout breakage.
  - [ ] Render empty state if rows are empty.
* [NEW] `frontend/src/components/Explanation.tsx`:
  - [ ] Render glassmorphic card with a subtle glow containing the explanation markdown text.
* [NEW] `frontend/src/components/HistoryPanel.tsx`:
  - [ ] Render sidebar container displaying list of past queries.
  - [ ] Read and write query actions to `localStorage`.
  - [ ] Add click handlers to trigger state reload on click.
* [MODIFY] `frontend/src/App.tsx`:
  - [ ] Add state variables: `columns`, `rows`, `explanation`, `historyList`.
  - [ ] Integrate execution callback. On run success, trigger explanation API.
  - [ ] Place `HistoryPanel` inside sidebar workspace and integrate `ResultsTable` and `Explanation` cards.

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** Performance degradation on the browser if result sets are large (mitigated by backend capping results at 100).
* **Operational Risks:** `localStorage` quota exceeded error.
* **Rollback Approach:** Remove history sidebar and restore simple grid containers.

## 11. Verification Protocol (Definition of Done)

### A. Automated Suite
* **Exact Command:** `npm run build`

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Happy Path Run | Click "Run Query" on valid SELECT | Displays table grid and AI explanation summary | 200 OK |
| Empty Data Path | Execute query with zero matches | Displays "No records found" state, hides explanation card | 200 OK |
| Query History Save | Execute a query | Adds record to local storage history list | N/A |
| Recall History | Click History item | Instantly updates dashboard to past states | N/A |

### C. Evidence To Capture
- Screen screenshot showing results grid and AI insights card filled.
- Screenshot of the sidebar history list populated with multiple queries.

## 12. Execution Notes
* **Status:** Planned
* **Started At:** [YYYY-MM-DD]
* **Completed At:** [YYYY-MM-DD]
* **Blockers Encountered:** None.
* **Notes:** None.
