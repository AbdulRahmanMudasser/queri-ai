# Phase 02: Schema Tree & Chat Console UI

## 1. Phase Purpose
This document controls execution for building the database schema inspector sidebar tree and the natural language chat input area.

## 2. Feature Objective
* **Phase Goal:** Implement the collapsible database tree sidebar showing tables, columns, and types, and create the natural language text box workspace console.
* **User Or System Outcome:** The user can visually inspect tables and column schemas to understand what they can query, write questions inside a capped text console, and submit them.
* **In Scope:** `src/utils/api.ts` (API client), `src/components/SchemaViewer.tsx` (sidebar tree component), `src/components/QueryInput.tsx` (text workspace input), and state management in `App.tsx` to handle loading/fetching.
* **Out Of Scope:** SQL previews, running SQL queries, showing table results.

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** [Phase 01 - Vite Scaffolding & Styling System Setup](./phase-01-scaffolding-theme.md) -> Must be marked [x] in the Local Tracker.
* **Downstream Tasks (Unlocks):** [Phase 03 - SQL Preview Console & Centralized Status Console](./phase-03-sql-preview-status.md)
* **Target Git Commit Prefix:** `feat(web-schema-input): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** [YYYY-MM-DD to YYYY-MM-DD]
* **Related PRD Section:** Feature 1 (Schema Reader) and Feature 2 (Natural Language Input)
* **Related Build Plan Section:** Section 4 (Directory Structure) and Section 5 (Data Flow)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** None required.
* **Database/Index Changes:** Requires the backend `GET /api/v1/schema` to be active for live schema tree render.
* **Feature Flags / Config Switches:** None.
* **Required Reusable Utilities:** 
  - Import custom layout containers from `App.tsx` and styling selectors.

## 6. API & Data Contract Specifications
* **Endpoint:** `GET /api/v1/schema`
* **Response payload mapping:**
  ```typescript
  interface TableColumn {
    name: string;
    type: string;
  }
  interface TableSchema {
    name: string;
    columns: TableColumn[];
  }
  interface SchemaResponse {
    tables: TableSchema[];
  }
  ```

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** 
  - Left Sidebar shows a hierarchical tree of tables (e.g., Folder icon bookings, File icons id, date). Clicking table folds/unfolds details.
  - Main area contains a text console with a 250 character counter and a violet submit button.
* **System Behavior Change:** Frontend queries `/api/v1/schema` on mount, displays loaded structure, and binds text area input to validation state.
* **Error States To Support:** 
  - Endpoint Unreachable: If backend fails, show a clean error notification in the status area (enforcing the No Inline Errors Policy).

## 8. Acceptance Criteria
- API client wrapper correctly handles Fetch calls and translates JSON responses type-safely.
- `SchemaViewer` component parses Table schemas and renders nested trees with folder/file icons.
- Clicking tables collapses/expands column rows with clean slide/transition animations.
- `QueryInput` limits input to 250 characters and shows a character countdown.
- Text console submit triggers API call, disabling buttons and showing pulse loading states.
- No inline style tags or inline text error fields are present in these components.

## 9. Implementation Steps (Component Audit)

### A. Data Layer
* [NEW] `frontend/src/utils/api.ts`:
  - [ ] Write `fetchSchema(): Promise<SchemaResponse>` call to backend API.
  - [ ] Implement generic error catcher converting network drops to clean validation objects.

### B. Controller / API Layer
* `No backend routes in this phase`

### C. Client / UI Layer
* [NEW] `frontend/src/components/SchemaViewer.tsx`:
  - [ ] Render tree nodes. Map tables to tree nodes containing columns list.
  - [ ] Use `lucide-react` icons (Database, Folder, FileKey, Terminal) for nodes.
  - [ ] Add click listeners to handle collapse states.
* [NEW] `frontend/src/components/QueryInput.tsx`:
  - [ ] Render textarea with placeholder text.
  - [ ] Implement input counter monitoring characters. Limit input string length to 250 characters.
  - [ ] Add violet glowing submit button.
* [MODIFY] `frontend/src/App.tsx`:
  - [ ] Call `fetchSchema` on mount, setting state array.
  - [ ] Integrate `SchemaViewer` in Sidebar panel and `QueryInput` in console panel.

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** Infinite state refetch loops if mount dependencies are configured incorrectly.
* **Operational Risks:** Empty schemas rendering as blank spaces.
* **Rollback Approach:** Revert sidebar components to placeholders.

## 11. Verification Protocol (Definition of Done)

### A. Automated Suite
* **Exact Command:** `npm run typecheck`

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Schema Load | Mount App | Sidebar fetches database schema and displays tree list | 200 OK |
| Toggle Nodes | Click Table item | Collapses/expands columns tree with smooth animation | N/A |
| Character Limit | Input 260 characters | Input blocks typing past 250, count shows 250/250 | N/A |
| Submit Question | Click Submit button | Triggers API call, button disables, spinner pulses | N/A |

### C. Evidence To Capture
- Screenshot showing SchemaViewer tree mapping database tables.
- Screenshot of QueryInput textarea rendering counts and button.

## 12. Execution Notes
* **Status:** Planned
* **Started At:** [YYYY-MM-DD]
* **Completed At:** [YYYY-MM-DD]
* **Blockers Encountered:** None.
* **Notes:** None.
