# Phase 07b: Few-Shot Retrieval & Prompt Integration

## 1. Phase Purpose
This document controls execution for Phase 07b, the second half of the few-shot and business-rules feature. With Phase 07 having established the database tables and seeded data, this phase wires the retrieval logic into the service layer and injects the results into Gemini prompts.

## 2. Feature Objective
* **Phase Goal:** Add `get_few_shot_examples()` and `get_business_rules()` to `context.py`, extend `translate()` in `translator.py` to accept and inject few-shot examples and business rules into the prompt, and update `query.py` to fetch and pass this context on every generation request.
* **User Or System Outcome:** Every SQL generation prompt sent to Gemini will now include up to 2 semantically matched example query pairs and all active business rules — making translations more accurate and domain-aware without any user-visible change.
* **In Scope:** `services/context.py` (new retrieval functions), `services/translator.py` (prompt extension), `api/v1/endpoints/query.py` (wiring), `tests/test_fewshot.py`.
* **Out Of Scope:** Admin UI, adding new examples/rules via API, changing the embeddings provider architecture.

## 3. Project Topology & Dependencies
* **Local Tracker:** [Execution Workflow Log](./execution-workflow.md)
* **Prerequisites (Blocked By):** [Phase 07 - ORM Models, DB Tables & Startup Seeder](./phase-07-fewshot-rules.md)
* **Downstream Tasks (Unlocks):** [Phase 08 - Query History Memory & RBAC Masking](./phase-08-memory-rbac.md)
* **Target Git Commit Prefix:** `feat(backend-fewshot-integration): ...`

## 4. Ownership And Delivery Notes
* **Owner:** Abdul Rahman
* **Priority:** High
* **Target Window:** 2026-07-01
* **Related PRD Section:** Section 7 (SQL Few-Shot Example RAG, Business Rules Registry) and Section 10 (Acceptance Criteria)
* **Related Build Plan Section:** Section 3 (System Boundaries) and Section 6 (Data Flow — steps 3 and 4)

## 5. Infrastructure & Environment Requirements
* **Environment Variables:** `DATABASE_URL`, `GEMINI_API_KEY`, `EMBEDDING_PROVIDER`.
* **Database/Index Changes:** None — tables are created and seeded in Phase 07.
* **No new dependencies required.**

## 6. API & Data Contract Specifications
* **No new endpoints.** `POST /api/v1/query/generate` behaviour changes internally only.
* **Extended `translate()` internal signature:**
  ```python
  async def translate(
      question: str,
      schema: list[dict[str, Any]],
      previous_sql: str | None = None,
      error_message: str | None = None,
      few_shot_examples: list[dict[str, str]] | None = None,
      business_rules: list[str] | None = None,
  ) -> dict[str, Any]: ...
  ```
* **Few-shot prompt injection format:**
  ```
  ## Similar Query Examples
  Q: Which hotel has the most bookings?
  SQL: SELECT hotel_id, COUNT(*) AS total FROM bookings GROUP BY hotel_id ORDER BY total DESC LIMIT 1

  Q: Show all confirmed bookings
  SQL: SELECT * FROM bookings WHERE status = 1
  ```
* **Business rules prompt injection format:**
  ```
  ## Business Rules
  - 1=confirmed, 2=pending, 3=cancelled, 4=completed
  - Use is_active = TRUE or status NOT IN (3)
  ```

---

## 7. UX / Behavioral Expectations
* **User-Facing Change:** None directly visible.
* **System Behavior Change:**
  - Every call to `POST /api/v1/query/generate` now fetches few-shot examples and business rules from the DB before calling Gemini.
  - The generation prompt is larger (by the injected few-shot and rules sections) but produces more accurate SQL.
  - If DB fetch fails for any reason, the system falls back to empty lists — same defensive pattern as `prune_schema()` fallback.
  - Log statement added: `"Fetched N few-shot examples and M business rules for question: ..."`.

## 8. Acceptance Criteria
- `context.py` has `get_few_shot_examples(question, db, provider, top_k=2)` and `get_business_rules(db)` implemented.
- `get_few_shot_examples` uses the existing `cosine_similarity()` function (already in `context.py`) against in-process fetched vectors — no new libraries.
- `translator.py`'s `_build_prompt()` and `_build_correction_prompt()` inject few-shot and rules sections when non-empty.
- `query.py` passes `few_shot_examples` and `business_rules` to `translate()` on the initial call and the self-correction retry.
- Fallback: if `get_few_shot_examples` or `get_business_rules` raises, the endpoint catches and proceeds with empty lists (not a 500).
- `test_fewshot.py` covers all retrieval and prompt injection behaviours.
- `poetry run ruff check .`, `poetry run mypy app/`, `poetry run pytest` all pass.

## 9. Implementation Steps (Component Audit)

### A. Service Layer
* [MODIFY] `backend/app/services/context.py`:
  - [ ] Add imports at function level (lazy, inside the function body) to avoid circular import risk: `from sqlalchemy import select`, `from sqlalchemy.ext.asyncio import AsyncSession`, `from app.db.models import FewShotExample, BusinessRule`.
  - [ ] Implement `async def get_few_shot_examples(question: str, db: AsyncSession, provider: EmbeddingsProvider, top_k: int = 2) -> list[dict[str, str]]`:
    - Fetch all rows: `result = await db.execute(select(FewShotExample))` then `rows = result.scalars().all()` — **`.scalars().all()` is required**. `db.execute()` returns a `CursorResult`, not a list. Iterating the `CursorResult` directly is a runtime error.
    - If no rows: return `[]`.
    - Generate question embedding via `provider.get_embedding(question)`.
    - For each row: call `cosine_similarity(question_emb, list(row.question_vector))` — wrap in try/except `ValueError` to skip rows with mismatched vector dimensions.
    - Sort descending by score, return top-k as `[{"question": row.question, "sql": row.sql_query}]`.
  - [ ] Implement `async def get_business_rules(db: AsyncSession) -> list[str]`:
    - `result = await db.execute(select(BusinessRule))` then `rows = result.scalars().all()`.
    - Return `[row.rule_value for row in rows]`.

* [MODIFY] `backend/app/services/translator.py`:
  - [ ] Extend `_build_prompt()` signature: `_build_prompt(question, schema_md, few_shot_examples=None, business_rules=None)`.
  - [ ] **Prompt section injection order matters for LLM attention.** Inject in this order inside the prompt:
    1. Database schema (existing)
    2. `## Business Rules` block (if `business_rules` non-empty)
    3. `## Similar Query Examples` block (if `few_shot_examples` non-empty)
    4. Rules list (existing — the numbered SQL safety rules)
    5. User question (existing)
  - [ ] Apply same injection to `_build_correction_prompt()` with the same new parameters.
  - [ ] Extend `translate()` public signature with `few_shot_examples: list[dict[str, str]] | None = None` and `business_rules: list[str] | None = None`.
  - [ ] Inside `translate()`, pass the new params to whichever `_build_*` function is called (both the normal and correction branch).
  - [ ] **Fully backwards-compatible**: all new params default to `None` — existing callers and tests require zero changes.

### B. Controller / API Layer
* [MODIFY] `backend/app/api/v1/endpoints/query.py`:
  - [ ] Add imports: `get_few_shot_examples`, `get_business_rules` from `app.services.context`.
  - [ ] **Move `provider = get_embeddings_provider()` BEFORE the pruning `try/except` block.** Currently `provider` is assigned inside the try block — if `get_embeddings_provider()` raises, `provider` is unbound and any later reference to it (including `get_few_shot_examples`) will crash with `UnboundLocalError`.
  - [ ] After schema pruning, add a dedicated few-shot/rules fetch block:
    ```python
    try:
        few_shot = await get_few_shot_examples(body.question, db, provider)
        rules = await get_business_rules(db)
        logger.info(
            "Fetched %d few-shot examples and %d business rules for question: %s",
            len(few_shot), len(rules), body.question[:80],
        )
    except Exception as exc:
        logger.warning("Few-shot/rules fetch failed, proceeding with empty context: %s", exc)
        few_shot, rules = [], []
    ```
  - [ ] This block must run **before** any `db.begin()` call to avoid transaction state conflicts.
  - [ ] Pass `few_shot_examples=few_shot, business_rules=rules` to the **initial** `translate()` call.
  - [ ] Pass `few_shot_examples=few_shot, business_rules=rules` to the **self-correction retry** `translate()` call as well. Both `few_shot` and `rules` are in scope at that point since they are defined before the outer try block.

### C. Tests
* [NEW] `backend/tests/test_fewshot.py`:
  - [ ] **ORM mock chain pattern** — `db.execute()` returns a `CursorResult`. To mock ORM fetches correctly use:
    ```python
    from unittest.mock import AsyncMock, MagicMock
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row1, row2, row3]
    db.execute.return_value = mock_result
    ```
    For multiple sequential calls (few_shot fetch then rules fetch), use `db.execute.side_effect = [fewshot_result, rules_result]`.
  - [ ] `test_get_few_shot_examples_returns_top_k`: mock DB returning 3 `FewShotExample` instances with fixed `question_vector` values; assert only top-2 returned (sorted by cosine similarity).
  - [ ] `test_get_few_shot_examples_empty_db`: mock DB returning `[]`; assert return value is `[]`.
  - [ ] `test_get_business_rules_returns_all_values`: mock DB returning 2 `BusinessRule` instances; assert both `rule_value` strings in output.
  - [ ] `test_get_business_rules_empty_db`: mock DB returning `[]`; assert return value is `[]`.
  - [ ] `test_build_prompt_includes_few_shot_section`: import `_build_prompt` directly from `app.services.translator`; call with `few_shot_examples=[{"question": "Q", "sql": "SELECT 1"}]`; assert `"Similar Query Examples"` in output.
  - [ ] `test_build_prompt_includes_business_rules_section`: call with `business_rules=["rule1"]`; assert `"Business Rules"` in output.
  - [ ] `test_build_prompt_skips_sections_when_empty`: call with `few_shot_examples=None, business_rules=None`; assert neither section header appears in output.
  - [ ] `test_generate_endpoint_passes_fewshot_to_translate`: integration test — mock `get_cached_schema`, `get_few_shot_examples`, `get_business_rules`, and `translate`; call `POST /api/v1/query/generate`; assert `translate` was called with `few_shot_examples` and `business_rules` kwargs.
  - [ ] `test_generate_endpoint_fallback_on_fetch_error`: patch `get_few_shot_examples` to raise `RuntimeError`; assert endpoint still returns 200 (fallback to empty lists).

---

## 10. Risks And Rollback Notes
* **Implementation Risks:**
  - Fetching all `FewShotExample` rows on every request — acceptable for a small fixed seed set (~10-20 rows), but would need caching if the table grows large. Out of scope for now.
  - Extending `translate()` signature — backwards compatible by design (all new params default to `None`).
* **Rollback Approach:** Remove the three new imports and the `get_few_shot_examples`/`get_business_rules` call block from `query.py`. The rest of the codebase is untouched.

## 11. Verification Protocol (Definition of Done)
### A. Automated Suite
* **Exact Commands:**
  - `poetry run ruff check .`
  - `poetry run ruff format --check .`
  - `poetry run mypy app/`
  - `poetry run pytest tests/ -v`

### B. Functional Verification Matrix
| State | Trigger Action | Expected Result | Status |
| :--- | :--- | :--- | :--- |
| Few-shot retrieved | `POST /api/v1/query/generate` with seeded DB | Log shows "Fetched N few-shot examples" | — |
| Prompt injected | Check translator logs for prompt length | Prompt is longer than before injection | — |
| Empty DB fallback | Remove all rows from both tables, hit generate | Returns 200, no few-shot or rules in prompt | — |
| DB error fallback | Mock DB to raise on fetch | Endpoint returns 200 with valid SQL (empty context fallback) | — |

### C. Evidence To Capture
- `poetry run pytest` output showing all tests pass.
- Log snippet showing few-shot and rules fetched for a sample question.

## 12. Execution Notes
* **Status:** Completed
* **Started At:** 2026-07-01
* **Completed At:** 2026-07-01
* **Blockers Encountered:** None
* **Notes:** Depends on Phase 07 tables and seeded data being present.
