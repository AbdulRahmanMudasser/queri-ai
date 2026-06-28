# Phase 01: Vite Scaffolding & Styling System Setup

## 1. Phase Purpose
This document controls execution for the initial scaffolding of the React + Vite frontend application, strict compiler rules, ESLint settings, Husky hooks, and custom HSL design system.

## 2. Feature Objective
* **Phase Goal:** Scaffold the React SPA with Vite and TypeScript, configure strict compiler parameters, set up ESLint and Husky, and implement the custom dark-mode HSL design tokens.
* **User Or System Outcome:** The frontend application has a stable build pipeline, is locked against lint and type errors during git commits, and renders a clean grid structure with HSL styles.
* **In Scope:** `package.json`, `tsconfig.json` strict configs, ESLint rules, Husky hooks (`.husky/pre-commit`), `index.html` loading fonts, `index.css` (custom variables, glassmorphic layout wrappers), and `App.tsx` grid layout tree.
* **Out Of Scope:** API fetch layers, individual interactive panels, SQL rendering.

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** None -> Marked [x] in the Local Tracker.
* **Downstream Tasks (Unlocks):** [Phase 02 - Schema Tree & Chat Console UI](./phase-02-schema-chat-console.md)
* **Target Git Commit Prefix:** `feat(web-scaffold): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** [YYYY-MM-DD to YYYY-MM-DD]
* **Related PRD Section:** Section 8 (Platform Scope) and Section 10 (Acceptance Criteria)
* **Related Build Plan Section:** Section 4 (Directory Structure) and Section 9 (Design System)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** None required.
* **Database/Index Changes:** None.
* **Feature Flags / Config Switches:** None.
* **Seed / Fixture Requirements:** None.
* **Required Reusable Utilities:** None.

## 6. API & Data Contract Specifications
* **Endpoint:** none required for this phase.
* **Request Schema:** None.
* **Response Schema:** None.

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** A blank, responsive dashboard page loading Outfit or Inter font, showing a glassmorphic sidebar layout and main work area in deep slate dark-mode.
* **System Behavior Change:** Frontend compiles static assets. Dev server hot-reloads instantly. Lint and type-checking run before allowing commits.
* **Error States To Support:** Build compile-time warnings and styling overrides.

## 8. Acceptance Criteria
- React + Vite + TypeScript application builds successfully (`npm run build`).
- TypeScript compiler configurations enforce strict compilation (`"strict": true`, `"noImplicitAny": true`).
- ESLint configuration flags unused variables, React hook violations, and styling issues.
- Husky pre-commit hooks successfully trigger `npm run typecheck && npm run lint` on commit.
- Custom HSL variables in `index.css` implement deep dark themes, glassmorphism boundaries, and transitions.
- Global layout in `App.tsx` splits into responsive Sidebar and Main console containers.

## 9. Implementation Steps (Component Audit)

### A. Data Layer
* [NEW] `frontend/package.json`:
  - [ ] Add packages: `react`, `react-dom`, `lucide-react`. DevDependencies: `typescript`, `eslint`, `husky`, `vite`.
* [NEW] `frontend/tsconfig.json`:
  - [ ] Set strict compiler parameters: `"strict": true`, `"noImplicitAny": true`, `"noUnusedLocals": true`.
* [NEW] `frontend/.husky/pre-commit`:
  - [ ] Setup script running `npm run typecheck && npm run lint`.

### B. Controller / API Layer
* `No API routes in this phase`

### C. Client / UI Layer
* [NEW] `frontend/index.html`:
  - [ ] Load Google Fonts (Outfit or Inter) and set app mount entrypoint.
* [NEW] `frontend/src/index.css`:
  - [ ] Define HSL custom color tokens: background, surface, border, primary, accent.
  - [ ] Add responsive grid/flexbox wrappers for sidebar panels and console workspace.
  - [ ] Add custom CSS definitions for glassmorphic cards and hover transitions.
* [NEW] `frontend/src/App.tsx`:
  - [ ] Setup core application layout: sidebar placeholder container, query workspace panel, and results grid container.
* [NEW] `frontend/src/main.tsx`:
  - [ ] Mount React application tree inside index.html anchor.

---

## 10. Risks And Rollback Notes
* **Implementation Risks:** TypeScript configuration conflicts on legacy node resolutions.
* **Operational Risks:** Pre-commit hooks blocking hotfixes in emergency cycles.
  - *Mitigation:* Developers can run `git commit --no-verify` if forced.
* **Rollback Approach:** Revert files to default Vite React scaffold templates.

## 11. Verification Protocol (Definition of Done)

### A. Automated Suite
* **Exact Commands:**
  - `npm run typecheck` (runs `tsc --noEmit`)
  - `npm run lint` (runs `eslint`)
  - `npm run build` (compiles production bundle)

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Response Code |
| :--- | :--- | :--- | :--- |
| Local Build | Run `npm run build` | Compiles into static files in `dist/` | 0 |
| Strict TS check | Write bad type in `App.tsx` and run type check | Build fails and outputs error log | Compile error |
| Pre-commit Hook check | Attempt git commit | Automatically triggers script and passes checks | Git commit allowed |

### C. Evidence To Capture
- Screen screenshot of scaffolded dashboard layout on desktop and mobile size.
- Terminal output logs showing successful build compilation.

## 12. Execution Notes
* **Status:** Ready
* **Started At:** [YYYY-MM-DD]
* **Completed At:** [YYYY-MM-DD]
* **Blockers Encountered:** None.
* **Notes:** None.
