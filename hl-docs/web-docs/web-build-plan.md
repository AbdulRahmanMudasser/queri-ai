# Web Build Plan & Architecture (React + Vite)

This document is the technical source of truth for the Web Client layer of the AI SQL Assistant (`sql-assistant`). It records the browser-based architecture, directory conventions, UI design rules, and integration boundaries.

---

## 1. Platform Summary
* **Platform Name:** Web Frontend Client
* **Primary Responsibility:** Deliver a responsive browser-based dashboard. This includes letting users inspect the active database schema, input queries, preview generated SQL, run execution, and read AI explanations.
* **Key Interfaces:** FastAPI Backend Services (`/api/schema`, `/api/generate-sql`, `/api/execute-query`, `/api/explain-results`).
* **Primary Risks:** Slow rendering of large result sets, layout breakage on mobile/tablet screens, inconsistent loading states.

---

## 2. Core Technology Stack And Dependencies
* **Build Tool & Bundler:** Vite (fast development server and production builds)
* **Framework:** React with TypeScript
* **Styling Engine:** Vanilla CSS (CSS variables, custom grid/flexbox layouts, responsive design, custom animations). Tailwind CSS is avoided to guarantee custom designs.
* **Icons:** `lucide-react`
* **API Client:** Fetch API (standard native client)
* **Testing & Quality:** ESLint, TypeScript compiler checks

---

## 3. System Boundaries And Responsibilities

### This Platform Owns
- Layout rendering, responsive sidebars, and user interface panels.
- Managing user input state, submission loading spinners, and validation warnings.
- SQL syntax highlighting visualization (using CSS blocks or minimal wrappers).
- Client-side history storage (using browser `localStorage` to persist past runs).
- Displaying tabular data in a scrollable, aligned table.

### This Platform Does Not Own
- Generating SQL queries (delegated to FastAPI).
- Parsing or validating SQL syntax/security (delegated to FastAPI).
- Running queries on the database (delegated to FastAPI).

---

## 4. Directory Structure And Module Layout

```text
frontend/
├── src/
│   ├── components/       # Reusable dashboard panels and widgets
│   │   ├── SchemaViewer.tsx  # Sidebar tree view of tables and columns
│   │   ├── QueryInput.tsx    # Chat console area for natural language input
│   │   ├── SQLPreview.tsx    # Terminal-like view of generated SQL with run controls
│   │   ├── ResultsTable.tsx  # Dynamic spreadsheet-style database grid
│   │   └── Explanation.tsx   # AI-generated natural language insights card
│   ├── utils/            # Api client wrappers and history helpers
│   │   └── api.ts            # Typed fetch wrappers calling FastAPI
│   ├── App.tsx           # Layout assembler (Grid layout, panels, global state)
│   ├── index.css         # Styling system (design tokens, layout sheets, animations)
│   ├── main.tsx          # React application root attachment
│   └── vite-env.d.ts     # Vite environment typings
├── index.html            # Core index file loading fonts (Inter/Outfit)
├── vite.config.ts        # Vite configuration (includes proxy rules for local API testing)
├── tsconfig.json         # TypeScript configuration rules
└── package.json          # Node dependencies
```

### Module Rules
1. All styling must reside in `index.css` or component-specific stylesheets using CSS custom properties.
2. API requests must go through `src/utils/api.ts` to ensure type-safe request/response handling.
3. Keep components small, functional, and strictly typed with TypeScript interfaces.

---

## 5. Data Flow And State Strategy
* **Local State Model:** React `useState` and `useContext` for state management (schema data, history array, active selected query, loading state, results grid, error states).
* **Data Retrieval Flow:**
  - **On Mount:** Load database schema from `GET /api/schema` to populate the sidebar tree view. Load history from `localStorage`.
  - **On Question Submit:** Call `POST /api/generate-sql` -> set returned SQL to state -> scroll SQL preview panel into view.
  - **On Execute Query:** Call `POST /api/execute-query` -> set columns/rows to state -> immediately call `POST /api/explain-results` -> set explanation text.
* **Persistence Strategy:** Save successful query actions (question, generated SQL, datetime) to `localStorage` so users can reload past inputs without re-querying the generator.

---

## 6. Domain Models And Contracts
* All data model types must mirror the FastAPI Pydantic responses:
  * `SchemaResponse`: `{ tables: Array<{ name: string, columns: Array<{ name: string, type: string }> }> }`
  * `SQLResponse`: `{ sql: string }`
  * `ExecutionResponse`: `{ columns: string[], rows: any[][] }`
  * `ExplanationResponse`: `{ explanation: string }`

---

## 7. Error Handling And Reliability
* **Inbound API Errors:** Capture non-200 responses. Display detailed security blocking warnings (e.g. "Dangerous SQL Blocked") or timeout errors in a prominent warning banner inside the console.
* **Loading Boundaries:** Disable all action buttons while an API request is in-flight. Show skeleton loaders or glowing pulsing animations during generation, execution, and explanation calls.

---

## 8. Security And Access Control
* **Input Restrictions:** Cap the question text box to a maximum of 250 characters.
* **Input Sanitization:** Avoid placing direct client-edited SQL input fields inside the app to prevent users from bypassing generation (users can execute the generated SQL, but cannot write arbitrary SQL).

---

## 9. Design System & Aesthetics (Vanilla CSS)
* **Theme:** Dark mode by default using rich HSL color variables:
  * `--background`: Deep dark slate/charcoal (`hsl(222, 19%, 8%)`)
  * `--surface`: Glassmorphic panel background (`hsla(222, 19%, 12%, 0.7)`)
  * `--border`: Subtly illuminated border (`hsla(210, 40%, 96%, 0.1)`)
  * `--primary`: Glowing neon violet (`hsl(263, 90%, 65%)`) for buttons
  * `--accent`: Bright cyan (`hsl(190, 95%, 50%)`) for validation states
* **Typography:** Modern Sans-Serif font (e.g. `Outfit` or `Inter` imported from Google Fonts).
* **Glassmorphism:** Apply `backdrop-filter: blur(10px)` and soft inner shadows to dashboards.
* **Animations:** Subtle hover transitions (`0.2s ease`), glowing borders on input focus, and pulse animations for pending tasks.

---

## 10. Performance And Scalability Expectations
* **Render Optimization:** Virtualize or add scroll indicators to the result table.
* **Bundle Size:** Vite production builds compile the assets into a single static build folder (`dist/`) containing lightweight JS and CSS files with zero overhead.

---

## 11. Code Quality And Tooling
* **TypeScript Compiler (`tsconfig.json`):** Strict compilation is enforced by enabling flags such as `"strict": true`, `"noImplicitAny": true`, `"noUnusedLocals": true`, and `"noUnusedParameters": true`. This blocks builds if there are unresolved type mismatches.
* **Linting & Code Styles (ESLint):** Standardizes JSX syntax, catches unused imports, checks React Hooks dependency requirements, and prevents dead code.
* **Pre-commit Hooks (Husky):** Runs `lint-staged` on git commit, which automatically executes `tsc --noEmit` and `eslint` on staged files. Commits are blocked if type checks or linter checks fail.
* **No Inline Errors Policy:** 
  - **No Inline Styles:** All styling must be classes in CSS stylesheets using variables; inline JSX `style={...}` attributes are prohibited.
  - **No Type Silencing:** Inline compiler ignore overrides (`// @ts-ignore` or `// @ts-expect-error`) are forbidden.
  - **No Inline UI Error Labels:** Validation and runtime errors must not render as inline text below inputs (preventing layout shifts). All errors must route to the centralized status console or a global toast overlay.

## 12. Testing And Verification Strategy
* Run standard static verification checks during local development and pre-commit hooks.
* **Verification Commands:**
  - Env Setup: `npm install`
  - Type Check: `npm run typecheck` (executes `tsc --noEmit`)
  - Linter Check: `npm run lint` (executes `eslint`)
  - Production Build: `npm run build` (compiles and bundles web assets into `dist/`)
