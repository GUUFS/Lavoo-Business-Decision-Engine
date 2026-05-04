# Decision Engine Latency Optimization — Design Spec
**Date:** 2026-05-04  
**Status:** Approved

---

## Problem

The `/api/decision-engine/analyze` endpoint takes ~178s end-to-end. The root cause is sequential, synchronous LLM calls — every stage blocks the next, and the slowest reasoning model is used for everything including simple tasks.

---

## Architecture

Four stages run today, all sequentially and synchronously:

| Stage | Task | Blocking? |
|-------|------|-----------|
| 1 | Bottleneck identification | Yes — Grok reasoning call |
| 2 | Action plan generation | Yes — Grok reasoning call |
| 3A | Semantic tool selection (per-plan) | Yes — CPU-bound embedding + SQL per plan |
| 3B | LLM stack enrichment (per-stack) | Yes — Grok call per stack |
| 4 | Roadmap + summary | Yes — Grok call |

After optimization:

- Stage 1 + Stage 2: Keep reasoning model (`grok-4-1-fast-reasoning`) — these require deep analysis
- Stage 3A: Parallelise across action plans with `asyncio.gather` + `run_in_executor`
- Stage 3B: Move to FastAPI `BackgroundTask`; client gets the response without waiting for enrichment
- Stage 4: Switch to non-reasoning model (`grok-4-1-fast-non-reasoning`) — summarisation, not reasoning
- All LLM calls: Wrap in `run_in_executor` so the async event loop is never blocked

---

## Components

### 1. Dual-model split

```python
self.model = "grok-4-1-fast-reasoning"           # Stage 1, Stage 2
self.fast_model = "grok-4-1-fast-non-reasoning"  # Stage 3A selection, Stage 3B enrichment, Stage 4
```

### 2. `_llm()` async helper

Single helper wraps any blocking `client.chat.completions.create()` call in `run_in_executor` so the event loop stays free:

```python
async def _llm(self, **kwargs) -> ChatCompletion:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: self.client.chat.completions.create(**kwargs))
```

All stage methods call `await self._llm(...)` instead of the sync client directly.

### 3. Parallel Stage 3A (tool selection)

Replace the for-loop over action plans with:

```python
results = await asyncio.gather(*[
    self._select_tools_for_plan(plan, query) for plan in action_plans
])
```

Each `_select_tools_for_plan` generates an embedding + runs a pgvector query + calls `_llm` for filtering — all three happen concurrently across plans.

### 4. Stage 3B as BackgroundTask

The LLM stack-enrichment pass is slow but non-critical for the API response. Move it out of the request path:

- `analyze()` route adds a `BackgroundTasks` parameter
- After Stage 3A returns candidate stacks, the route schedules `_enrich_stacks_with_llm` as a background task
- The response returns immediately with the unenriched (algorithmic) stacks in `recommended_tool_stacks`
- Enriched stacks are written to the `analyses` row by the background task
- Frontend polls or fetches enriched stacks separately (future: websocket push)

### 5. uvloop

Replaces the default asyncio event loop with a faster libuv-backed implementation:

```python
# api/main.py — before app = FastAPI(...)
import uvloop
uvloop.install()
```

Add `uvloop` to `requirements.txt` and run `uv add uvloop` for `pyproject.toml`.

### 6. Fix N+1 in `admin_list_requests`

Current: `for r in requests: db.query(User).filter(User.id == r.user_id).first()` — one query per row.

Fix: join users at query time using SQLAlchemy `joinedload` or an explicit JOIN, so a single query returns all requests with their users.

---

## Data Flow (After)

```
POST /api/decision-engine/analyze
│
├── Stage 1: bottleneck  ─── await _llm(model=reasoning)
├── Stage 2: action plans ── await _llm(model=reasoning)
│
├── Stage 3A: tool selection (all plans in parallel)
│   └── asyncio.gather([_select_tools_for_plan(p) for p in plans])
│       each: run_in_executor(embed) → pgvector SQL → _llm(model=fast, filter)
│
├── Stage 4: roadmap/summary ── await _llm(model=fast)
│
└── Response returned ← background task scheduled
    │
    └── [BackgroundTask] Stage 3B: enrich stacks
        └── asyncio.gather([_enrich_one_stack(s) for s in stacks])
            each: _llm(model=fast, enrich)
        └── db.execute(UPDATE analyses SET recommended_tool_stacks = ...)
```

---

## Error Handling

- If `_llm()` raises, the stage catches and returns a degraded result (empty stacks / generic summary) rather than failing the whole request.
- Background task failures are logged via Sentry but do not affect the HTTP response.
- N+1 fix uses `.options(joinedload(...))` — safe, no behaviour change.

---

## Testing

1. Run `PYTHONPATH=. uv run python decision_engine/test_automation_stacks.py` — verify 3 demo scenarios complete faster than before.
2. Manual curl to `/api/decision-engine/analyze` — measure wall time before and after.
3. Confirm background task writes `recommended_tool_stacks` to DB within 30s of response.

---

## Out of Scope

- Websocket push for enriched stacks (future)
- Persistent embedding cache for user queries (future)
- pgvector HNSW migration for `ai_tools.embedding` column (future)
