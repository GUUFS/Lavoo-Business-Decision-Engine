# Decision Engine Optimization + Creator Marketplace Listing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut decision engine latency (parallel LLM calls, dual-model split, BackgroundTask for enrichment, uvloop) and add user-created listings to the marketplace (DB model, CRUD API, seeded data, frontend modal + parallel fetch).

**Architecture:** Part A refactors `AgenticAnalyzer` to use an async `_llm()` wrapper with `run_in_executor`, parallelises Stage 3 toolkit calls with `asyncio.gather`, and offloads Stage 3B (LLM stack enrichment) to a FastAPI `BackgroundTask`. Part B adds a `CreatorListing` model and CRUD endpoints, then wires a Create Listing modal + merged grid into the marketplace frontend page.

**Tech Stack:** FastAPI BackgroundTasks, asyncio.gather, run_in_executor, uvloop, xAI Grok dual-model, SQLAlchemy, Alembic, Next.js 16 / React 19, Tailwind CSS, shadcn Dialog.

---

## Part A — Decision Engine Optimization

### Task 1: Add uvloop

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml` (via `uv add`)
- Modify: `api/main.py`

- [ ] **Step 1: Add uvloop to requirements.txt**

Open `requirements.txt` and append:
```
uvloop>=0.21.0
```

- [ ] **Step 2: Add uvloop to pyproject.toml via uv add**

Run from project root:
```bash
uv add uvloop
```
Expected: `pyproject.toml` dependencies now includes `uvloop>=0.21.0` (or similar).

- [ ] **Step 3: Install the dependency**

```bash
uv pip install uvloop
```
Expected: Installs successfully. If on Windows/PyPy, uvloop is unsupported — skip this task and move on (Linux only).

- [ ] **Step 4: Add uvloop.install() to api/main.py**

In `api/main.py`, find line 1 (top of file, before any imports are executed) and add this block **before** the existing `import asyncio` line:

```python
try:
    import uvloop
    uvloop.install()
except ImportError:
    pass  # uvloop not available (Windows/PyPy), fall back to default event loop
```

- [ ] **Step 5: Verify server starts**

```bash
PYTHONPATH=. uv run uvicorn api.main:app --reload --port 8000
```
Expected: Server starts without errors, logs do not show uvloop import errors.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pyproject.toml api/main.py
git commit -m "perf: add uvloop for faster asyncio event loop"
```

---

### Task 2: Add fast_model attribute and _llm() async helper

**Files:**
- Modify: `decision_engine/agentic_analyzer.py`

- [ ] **Step 1: Add fast_model to __init__**

In `decision_engine/agentic_analyzer.py`, find the `__init__` method. After `self.reasoning_model = "grok-4-1-fast-reasoning"`, add:

```python
self.fast_model = "grok-4-1-fast-non-reasoning"
```

- [ ] **Step 2: Add _llm() async helper method**

Add this method to `AgenticAnalyzer` immediately after `__init__`, before `_search_ai_tools`:

```python
async def _llm(self, **kwargs):
    """Run a blocking OpenAI chat completion in a thread so the event loop stays free."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: self.client.chat.completions.create(**kwargs))
```

- [ ] **Step 3: Verify no import errors**

```bash
PYTHONPATH=. uv run python -c "from decision_engine.agentic_analyzer import AgenticAnalyzer; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add decision_engine/agentic_analyzer.py
git commit -m "perf: add fast_model and _llm() async wrapper to AgenticAnalyzer"
```

---

### Task 3: Refactor Stages 1, 2, and 4 to use await self._llm()

**Files:**
- Modify: `decision_engine/agentic_analyzer.py`

- [ ] **Step 1: Refactor Stage 1 (_stage1_primary_bottleneck)**

Replace the blocking call in `_stage1_primary_bottleneck` (currently line ~217):
```python
# OLD:
response = self.client.chat.completions.create(
    model=self.model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    max_tokens=800,
)
```
with:
```python
# NEW:
response = await self._llm(
    model=self.model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    max_tokens=800,
)
```

- [ ] **Step 2: Refactor Stage 2 (_stage2_secondary_constraints) — switch to fast_model**

Replace the blocking call in `_stage2_secondary_constraints` (currently line ~287):
```python
# OLD:
response = self.client.chat.completions.create(
    model=self.reasoning_model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.6,
    max_tokens=600,
)
```
with:
```python
# NEW (fast_model — secondary constraints don't need deep reasoning):
response = await self._llm(
    model=self.fast_model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.6,
    max_tokens=600,
)
```

- [ ] **Step 3: Refactor Stage 4 (_stage4_roadmap_and_motivation) — switch to fast_model**

Replace the blocking call in `_stage4_roadmap_and_motivation` (currently line ~695):
```python
# OLD:
response = self.client.chat.completions.create(
    model=self.reasoning_model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.8,
    max_tokens=800,
)
```
with:
```python
# NEW (fast_model — roadmap summarisation, not deep reasoning):
response = await self._llm(
    model=self.fast_model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.8,
    max_tokens=800,
)
```

- [ ] **Step 4: Verify import still works**

```bash
PYTHONPATH=. uv run python -c "from decision_engine.agentic_analyzer import AgenticAnalyzer; print('ok')"
```
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add decision_engine/agentic_analyzer.py
git commit -m "perf: refactor stages 1/2/4 to use async _llm(); fast_model for stages 2+4"
```

---

### Task 4: Parallelize Stage 3 toolkit calls with asyncio.gather

**Files:**
- Modify: `decision_engine/agentic_analyzer.py`

The current `_stage3_action_plans` has a sequential `for plan in action_plans` loop that calls `self.client.chat.completions.create` (now `_llm`) one at a time. Extract per-plan toolkit logic into `_attach_toolkit()` and run all plans in parallel.

- [ ] **Step 1: Add _attach_toolkit() method**

Add this method to `AgenticAnalyzer` directly before `_stage3_action_plans`:

```python
async def _attach_toolkit(self, plan: dict, user_query: str) -> dict:
    """Fetch and attach the best AI tool for a single action plan (async, runs in parallel)."""
    if not plan.get("needs_ai_tool", False):
        plan["toolkit"] = None
        plan.pop("needs_ai_tool", None)
        return plan

    tools = await self._search_ai_tools(
        user_query=user_query,
        action_description=f"{plan['title']} - {plan.get('what_to_do', '')}",
        top_k=3,
    )

    if not tools:
        plan["toolkit"] = None
        plan.pop("needs_ai_tool", None)
        return plan

    tool_names = [f"{t['tool_name']}: {t['description'][:100]}" for t in tools]
    prompt_tool_selection = f"""You are selecting the best AI tool for a specific action.

ACTION: {plan['title']}
WHAT TO DO: {plan.get('what_to_do', '')}

AVAILABLE TOOLS (from semantic search):
{chr(10).join([f"{i+1}. {t}" for i, t in enumerate(tool_names)])}

Your task: Pick the BEST tool for this action, or return null if none are good fits.

OUTPUT FORMAT (JSON):
{{
    "selected_tool_index": 0 or null,
    "toolkit": {{
        "tool_name": "Selected tool name",
        "what_it_helps": "What it specifically helps with for this action (1 sentence)",
        "why_this_tool": "Why this tool is best for this action (1 sentence)"
    }} or null
}}

Only recommend if it genuinely adds value."""

    try:
        tool_response = await self._llm(
            model=self.fast_model,
            messages=[{"role": "user", "content": prompt_tool_selection}],
            temperature=0.6,
            max_tokens=300,
        )
        tool_text = tool_response.choices[0].message.content.strip()
        if "```json" in tool_text:
            tool_text = tool_text.split("```json")[1].split("```")[0].strip()
        elif "```" in tool_text:
            tool_text = tool_text.split("```")[1].split("```")[0].strip()
        tool_selection = json.loads(tool_text)
        plan["toolkit"] = tool_selection.get("toolkit")
    except Exception as e:
        logger.warning(f"Toolkit selection failed for plan '{plan['title']}': {e}")
        plan["toolkit"] = None

    plan.pop("needs_ai_tool", None)
    return plan
```

- [ ] **Step 2: Replace the sequential loop in _stage3_action_plans**

In `_stage3_action_plans`, find the entire `for plan in action_plans:` block (roughly lines 392–447) and replace it with:

```python
# Attach toolkits to all plans in parallel
action_plans_with_toolkits = await asyncio.gather(*[
    self._attach_toolkit(plan, user_query) for plan in action_plans
])
result["action_plans"] = list(action_plans_with_toolkits)
```

Also ensure `import asyncio` is at the top of the file (it already is since `agentic_analyzer.py` has `from datetime import datetime` but check for asyncio).

- [ ] **Step 3: Add asyncio import if missing**

At the top of `decision_engine/agentic_analyzer.py`, ensure this import exists (add it if not present):
```python
import asyncio
```

- [ ] **Step 4: Replace the first Stage 3 LLM call to use await _llm**

In `_stage3_action_plans`, the initial call that generates action plans (roughly line ~376) should also be changed:
```python
# OLD:
response = self.client.chat.completions.create(
    model=self.model,
    messages=[{"role": "user", "content": prompt_actions}],
    temperature=0.7,
    max_tokens=1500,
)
```
```python
# NEW (keep reasoning model for action plan generation):
response = await self._llm(
    model=self.model,
    messages=[{"role": "user", "content": prompt_actions}],
    temperature=0.7,
    max_tokens=1500,
)
```

- [ ] **Step 5: Verify syntax**

```bash
PYTHONPATH=. uv run python -c "from decision_engine.agentic_analyzer import AgenticAnalyzer; print('ok')"
```
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add decision_engine/agentic_analyzer.py
git commit -m "perf: parallelize Stage 3 toolkit selection with asyncio.gather"
```

---

### Task 5: Parallelize Stage 3B enrichment

**Files:**
- Modify: `decision_engine/agentic_analyzer.py`

Currently `_enrich_stacks_with_llm` processes stacks sequentially. Extract per-stack logic and use `asyncio.gather`.

- [ ] **Step 1: Add _enrich_single_stack() method**

Add this method to `AgenticAnalyzer` directly before `_enrich_stacks_with_llm`:

```python
async def _enrich_single_stack(
    self, stack: dict, user_query: str, primary_bottleneck: str
) -> dict:
    """LLM-enrich a single stack. Returns the stack (modified in place)."""
    tools = stack.get("tools", [])
    if not tools:
        return stack

    allowed_tool_names = [t.get("tool_name", "") for t in tools if t.get("tool_name")]

    tool_context_parts = []
    for tool in tools:
        name = tool.get("tool_name", "")
        desc = (tool.get("description") or "")[:200]
        features_raw = tool.get("key_features") or ""
        integrations_raw = tool.get("compatibility_integration") or ""
        features = features_raw[:200].replace('["', "").replace('"]', "").replace('",', ",")
        integrations = integrations_raw[:200].replace('["', "").replace('"]', "").replace('",', ",")
        tool_context_parts.append(
            f"- {name}: {desc}\n"
            f"  Key Features: {features}\n"
            f"  Integrations: {integrations}"
        )

    tool_context = "\n".join(tool_context_parts)
    allowed_names_str = ", ".join(f'"{n}"' for n in allowed_tool_names)

    prompt = f"""You are an automation workflow expert. A semantic search engine selected these tools from a live database to match a user's business problem. Explain HOW they work together as a workflow.

STRICT RULE: You MUST ONLY reference these exact tool names from the database: {allowed_names_str}
Do NOT mention, suggest, or invent any other tools.

USER QUERY: "{user_query}"
PRIMARY BOTTLENECK: "{primary_bottleneck}"

TOOLS SELECTED FROM DATABASE:
{tool_context}

Explain how these {len(tools)} tool(s) form an automation workflow for this user.

OUTPUT FORMAT (JSON only, no markdown fences):
{{
  "stack_name": "Short descriptive name showing the flow (e.g., Tool A → Tool B)",
  "workflow_summary": "2 sentences: what this stack does and why it solves the user's problem",
  "automation_logic": "Step-by-step: how data or tasks flow between the tools (2-3 sentences)",
  "tool_roles": [
    {{
      "tool_name": "exact name from the list above",
      "role": "What this specific tool does in this workflow (1 sentence)",
      "hands_off_to": "What output it passes to the next tool, or 'delivers final output' if last"
    }}
  ],
  "setup_order": [
    {{
      "position": 1,
      "tool_name": "exact name from the list above",
      "why": "Why set this up first / at this step (1 sentence)"
    }}
  ]
}}"""

    try:
        response = await self._llm(
            model=self.fast_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=700,
        )
        result_text = response.choices[0].message.content.strip()
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        llm_data = json.loads(result_text)

        validated_tool_roles = [
            tr for tr in llm_data.get("tool_roles", [])
            if tr.get("tool_name") in allowed_tool_names
        ]
        validated_setup_order = [
            so for so in llm_data.get("setup_order", [])
            if so.get("tool_name") in allowed_tool_names
        ]

        stack["stack_name"] = llm_data.get("stack_name", stack.get("stack_name", ""))
        stack["workflow_summary"] = llm_data.get("workflow_summary", stack.get("summary", ""))
        stack["automation_logic"] = llm_data.get("automation_logic", stack.get("automation_logic", ""))
        if validated_tool_roles:
            stack["tool_roles"] = validated_tool_roles
        if validated_setup_order:
            stack["setup_order"] = validated_setup_order

        logger.info(f"LLM enriched stack: {stack.get('stack_name', '?')}")
    except Exception as e:
        logger.warning(f"LLM enrichment failed for stack, keeping base values: {e}")

    return stack
```

- [ ] **Step 2: Replace _enrich_stacks_with_llm body to use asyncio.gather**

Replace the entire body of `_enrich_stacks_with_llm` with:

```python
async def _enrich_stacks_with_llm(
    self,
    stacks: List[Dict],
    user_query: str,
    primary_bottleneck: str,
) -> List[Dict]:
    """LLM agent pass: reason about HOW selected DB tools work together. Runs all stacks in parallel."""
    if not stacks:
        return stacks
    results = await asyncio.gather(*[
        self._enrich_single_stack(stack, user_query, primary_bottleneck)
        for stack in stacks
    ])
    return list(results)
```

- [ ] **Step 3: Verify syntax**

```bash
PYTHONPATH=. uv run python -c "from decision_engine.agentic_analyzer import AgenticAnalyzer; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add decision_engine/agentic_analyzer.py
git commit -m "perf: parallelize Stage 3B stack enrichment with asyncio.gather"
```

---

### Task 6: Move Stage 3B to BackgroundTask

Stage 3B (LLM enrichment) is the most expensive step. Move it out of the request path: return unenriched stacks immediately, then update the DB row after the response is sent.

**Files:**
- Modify: `decision_engine/agentic_analyzer.py` (strip enrichment from `_stage3_automation_stacks`)
- Modify: `api/routes/decision_engine/analyzer.py` (add BackgroundTasks, enrich function)

- [ ] **Step 1: Rename _stage3_automation_stacks to return raw stacks only**

In `_stage3_automation_stacks`, remove the `_enrich_stacks_with_llm` call. Replace the method body with:

```python
async def _stage3_automation_stacks(
    self,
    user_query: str,
    action_plans_result: Dict[str, Any],
    primary_result: Dict[str, Any],
    secondary_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Stage 3B: Compose up to 3 automation stacks (algorithmic only).
    LLM enrichment is deferred to a BackgroundTask in the route layer.
    """
    try:
        action_plans = action_plans_result.get("action_plans", []) or []
        stacks = recommend_automation_stacks(
            user_query=user_query,
            action_plans=action_plans,
            top_k_stacks=3,
            max_tools_per_stack=4,
            db_session=self.db,
        )

        constraints = secondary_result.get("secondary_constraints", []) or []
        constraint_titles = [
            str(item.get("title", "")).strip()
            for item in constraints
            if item.get("title")
        ]

        valid_stacks = []
        for stack in stacks:
            if not stack.get("tools"):
                continue
            if constraint_titles:
                stack["solves"] = f"Helps reduce: {', '.join(constraint_titles[:3])}."
            valid_stacks.append(stack)

        logger.info(f"Built {len(valid_stacks)} raw automation stacks (enrichment deferred)")
        return {"recommended_tool_stacks": valid_stacks}

    except Exception as e:
        logger.error(f"Stage 3B failed: {e}", exc_info=True)
        return {"recommended_tool_stacks": []}
```

- [ ] **Step 2: Add background enrichment function to the route file**

In `api/routes/decision_engine/analyzer.py`, add these imports at the top if not already present:
```python
import json
from fastapi import BackgroundTasks
from sqlalchemy import text
```

Then add this standalone coroutine function before the `router` definition (or before `@router.post("/analyze")`):

```python
async def _enrich_stacks_background(
    analysis_id: int,
    raw_stacks: list,
    user_query: str,
    bottleneck_title: str,
) -> None:
    """
    BackgroundTask: LLM-enrich automation stacks after the response is sent,
    then persist the enriched stacks back to the analysis row.
    """
    from database.pg_connections import SessionLocal
    from decision_engine.agentic_analyzer import create_analyzer

    db = SessionLocal()
    try:
        analyzer = create_analyzer(db)
        enriched = await analyzer._enrich_stacks_with_llm(
            stacks=raw_stacks,
            user_query=user_query,
            primary_bottleneck=bottleneck_title,
        )
        db.execute(
            text("UPDATE business_analyses SET recommended_tool_stacks = :stacks WHERE id = :id"),
            {"stacks": json.dumps(enriched), "id": analysis_id},
        )
        db.commit()
        logger.info(f"Background stack enrichment saved for analysis {analysis_id}")
    except Exception as exc:
        logger.error(
            f"Background stack enrichment failed for analysis {analysis_id}: {exc}",
            exc_info=True,
        )
    finally:
        db.close()
```

- [ ] **Step 3: Add BackgroundTasks param to the route handler**

In `api/routes/decision_engine/analyzer.py`, update the `analyze_business_goal` function signature:

```python
# OLD:
async def analyze_business_goal(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):

# NEW:
async def analyze_business_goal(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
```

- [ ] **Step 4: Schedule the background task after analysis**

In `analyze_business_goal`, find the line:
```python
result = await analyzer.analyze(
    user_query=business_goal,
    user_id=user_id
)
```

Add these lines immediately after it (before the `return`):
```python
# Schedule background enrichment of automation stacks
_raw_stacks = result["data"].get("recommended_tool_stacks", [])
_bottleneck_title = result["data"].get("primary_bottleneck", {}).get("title", "")
if _raw_stacks:
    background_tasks.add_task(
        _enrich_stacks_background,
        analysis_id=result["data"]["analysis_id"],
        raw_stacks=_raw_stacks,
        user_query=business_goal,
        bottleneck_title=_bottleneck_title,
    )
```

- [ ] **Step 5: Verify syntax**

```bash
PYTHONPATH=. uv run python -c "
from api.routes.decision_engine.analyzer import router, _enrich_stacks_background
print('ok')
"
```
Expected: `ok`

- [ ] **Step 6: Smoke test the analysis endpoint**

Start the server:
```bash
PYTHONPATH=. uv run uvicorn api.main:app --reload --port 8000
```

In a second terminal, send a test request (replace TOKEN with a valid JWT):
```bash
curl -s -X POST http://localhost:8000/api/business/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"business_goal": "I run a freelance video editing business and spend too much time on invoicing and proposals"}' \
  | python -m json.tool | head -50
```
Expected: JSON response with `success: true` in under 60 seconds. Background task should log enrichment completion ~30s later.

- [ ] **Step 7: Commit**

```bash
git add decision_engine/agentic_analyzer.py api/routes/decision_engine/analyzer.py
git commit -m "perf: move Stage 3B LLM enrichment to FastAPI BackgroundTask"
```

---

### Task 7: Fix N+1 in admin_list_requests

**Files:**
- Modify: `api/routes/marketplace/marketplace.py`

- [ ] **Step 1: Add joinedload import**

At the top of `api/routes/marketplace/marketplace.py`, add `joinedload` to the sqlalchemy.orm import:

```python
# OLD:
from sqlalchemy.orm import Session

# NEW:
from sqlalchemy.orm import Session, joinedload
```

- [ ] **Step 2: Replace the N+1 query in admin_list_requests**

Find the `admin_list_requests` function. Replace:
```python
requests = q.order_by(MarketplaceRequest.created_at.desc()).all()
result = []
for r in requests:
    user = db.query(User).filter(User.id == r.user_id).first()
    result.append({
        "id": r.id, "title": r.title, "description": r.description,
        "budget": r.budget, "timeline": r.timeline, "status": r.status,
        "user_name": user.name if user else "Unknown",
        "user_email": user.email if user else "",
        "created_at": r.created_at.isoformat() if r.created_at else None,
    })
```
with:
```python
requests = (
    q.options(joinedload(MarketplaceRequest.user))
    .order_by(MarketplaceRequest.created_at.desc())
    .all()
)
result = [
    {
        "id": r.id, "title": r.title, "description": r.description,
        "budget": r.budget, "timeline": r.timeline, "status": r.status,
        "user_name": r.user.name if r.user else "Unknown",
        "user_email": r.user.email if r.user else "",
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
    for r in requests
]
```

- [ ] **Step 3: Verify syntax**

```bash
PYTHONPATH=. uv run python -c "from api.routes.marketplace.marketplace import router; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add api/routes/marketplace/marketplace.py
git commit -m "perf: fix N+1 query in admin_list_requests with joinedload"
```

---

## Part B — Creator Marketplace Listing

### Task 8: Add CreatorListing model to pg_models.py

**Files:**
- Modify: `database/pg_models.py`

- [ ] **Step 1: Add CreatorListing class**

In `database/pg_models.py`, find the line `class MvpFeature(Base):` (around line 1750). Insert the following block **before** it, after the existing `MarketplaceRequest` class:

```python
class CreatorListing(Base):
    __tablename__ = "creator_listings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    full_description = Column(Text, nullable=True)
    listing_type = Column(String(50), nullable=False)  # Template|Playbook|Service|Tool|Course|Automation|Consulting|Strategy
    category = Column(String(100), nullable=False)
    price = Column(Float, default=0.0)
    tags = Column(JSON, nullable=True)
    features = Column(JSON, nullable=True)
    icon_name = Column(String(50), nullable=False, default="Cpu")
    color_theme = Column(String(30), nullable=False, default="orange")
    purchase_url = Column(String(500), nullable=True)
    sales_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User")
```

- [ ] **Step 2: Verify the model is importable**

```bash
PYTHONPATH=. uv run python -c "from database.pg_models import CreatorListing; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add database/pg_models.py
git commit -m "feat: add CreatorListing SQLAlchemy model"
```

---

### Task 9: Create and run Alembic migration

**Files:**
- Create: `database/alembic/versions/<hash>_add_creator_listings_table.py` (auto-generated)

- [ ] **Step 1: Generate migration**

```bash
PYTHONPATH=. uv run alembic revision --autogenerate -m "add creator_listings table"
```
Expected: New file created under `database/alembic/versions/`.

- [ ] **Step 2: Inspect the generated migration**

Open the generated file and verify it contains an `op.create_table("creator_listings", ...)` call with all the expected columns. If Alembic missed any column, add it manually.

- [ ] **Step 3: Apply migration**

```bash
PYTHONPATH=. uv run alembic upgrade head
```
Expected: Migration runs without error. Output includes `Running upgrade ... -> <hash>`.

- [ ] **Step 4: Verify table exists**

```bash
PYTHONPATH=. uv run python -c "
from database.pg_connections import SessionLocal
from sqlalchemy import text
db = SessionLocal()
result = db.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='creator_listings' ORDER BY ordinal_position\"))
for row in result:
    print(row[0])
db.close()
"
```
Expected: Prints all column names: `id`, `user_id`, `title`, `description`, `full_description`, `listing_type`, `category`, `price`, `tags`, `features`, `icon_name`, `color_theme`, `purchase_url`, `sales_count`, `rating`, `review_count`, `is_active`, `created_at`.

- [ ] **Step 5: Commit the migration file**

```bash
git add database/alembic/versions/
git commit -m "feat: alembic migration — add creator_listings table"
```

---

### Task 10: Add listing CRUD endpoints to marketplace.py

**Files:**
- Modify: `api/routes/marketplace/marketplace.py`

- [ ] **Step 1: Add CreatorListing import**

In `api/routes/marketplace/marketplace.py`, update the pg_models import line:
```python
# OLD:
from database.pg_models import User, MarketplaceTool, MarketplacePurchase, MarketplaceRequest

# NEW:
from database.pg_models import User, MarketplaceTool, MarketplacePurchase, MarketplaceRequest, CreatorListing
```

- [ ] **Step 2: Add Pydantic models for listing**

After the existing `CustomRequest` Pydantic model, add:

```python
LISTING_TYPES = {"Template", "Playbook", "Service", "Tool", "Course", "Automation", "Consulting", "Strategy"}


class ListingCreate(BaseModel):
    title: str
    description: str
    full_description: Optional[str] = None
    listing_type: str
    category: str
    price: float = 0.0
    tags: Optional[list] = None
    features: Optional[list] = None
    icon_name: str = "Cpu"
    color_theme: str = "orange"
    purchase_url: Optional[str] = None


class ListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    full_description: Optional[str] = None
    listing_type: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    tags: Optional[list] = None
    features: Optional[list] = None
    icon_name: Optional[str] = None
    color_theme: Optional[str] = None
    purchase_url: Optional[str] = None
    is_active: Optional[bool] = None
```

- [ ] **Step 3: Add _listing_dict helper**

After the existing `_tool_dict` helper, add:

```python
def _listing_dict(listing: CreatorListing) -> dict:
    return {
        "id": listing.id,
        "name": listing.title,          # alias for frontend card compatibility
        "title": listing.title,
        "author": "",
        "description": listing.description,
        "full_description": listing.full_description,
        "listing_type": listing.listing_type,
        "category": listing.category,
        "price": listing.price,
        "tags": listing.tags or [],
        "features": listing.features or [],
        "icon_name": listing.icon_name,
        "color_theme": listing.color_theme,
        "purchase_url": listing.purchase_url,
        "sales_count": listing.sales_count,
        "rating": listing.rating,
        "review_count": listing.review_count,
        "is_active": listing.is_active,
        "created_at": listing.created_at.isoformat() if listing.created_at else None,
        "source": "user_listing",
    }
```

- [ ] **Step 4: Add listing endpoints**

After the `submit_custom_request` endpoint and before the admin endpoints section comment, add:

```python
# ─── Creator Listing endpoints ────────────────────────────────────────────────

@router.post("/listings")
async def create_listing(
    body: ListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new creator listing owned by the current user."""
    if body.listing_type not in LISTING_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"listing_type must be one of: {', '.join(sorted(LISTING_TYPES))}",
        )
    listing = CreatorListing(
        user_id=current_user.id,
        title=body.title,
        description=body.description,
        full_description=body.full_description,
        listing_type=body.listing_type,
        category=body.category,
        price=body.price,
        tags=body.tags or [],
        features=body.features or [],
        icon_name=body.icon_name,
        color_theme=body.color_theme,
        purchase_url=body.purchase_url,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    logger.info(f"User {current_user.id} created listing {listing.id}: {listing.title}")
    return _listing_dict(listing)


@router.get("/listings")
async def list_listings(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active creator listings."""
    q = db.query(CreatorListing).filter(CreatorListing.is_active == True)
    if category and category != "All":
        q = q.filter(CreatorListing.category == category)
    if search:
        like = f"%{search}%"
        q = q.filter(
            CreatorListing.title.ilike(like) | CreatorListing.description.ilike(like)
        )
    listings = q.order_by(CreatorListing.created_at.desc()).limit(limit).all()
    return {"listings": [_listing_dict(l) for l in listings]}


@router.get("/listings/{listing_id}")
async def get_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = db.query(CreatorListing).filter(
        CreatorListing.id == listing_id, CreatorListing.is_active == True
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_dict(listing)


@router.put("/listings/{listing_id}")
async def update_listing(
    listing_id: int,
    body: ListingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = db.query(CreatorListing).filter(CreatorListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your listing")
    if body.listing_type and body.listing_type not in LISTING_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"listing_type must be one of: {', '.join(sorted(LISTING_TYPES))}",
        )
    for field, value in body.dict(exclude_unset=True).items():
        setattr(listing, field, value)
    db.commit()
    db.refresh(listing)
    return _listing_dict(listing)


@router.delete("/listings/{listing_id}")
async def delete_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = db.query(CreatorListing).filter(CreatorListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your listing")
    listing.is_active = False
    db.commit()
    return {"status": "deleted"}
```

- [ ] **Step 5: Verify endpoints are importable**

```bash
PYTHONPATH=. uv run python -c "from api.routes.marketplace.marketplace import router; print('ok')"
```
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add api/routes/marketplace/marketplace.py
git commit -m "feat: add creator listing CRUD endpoints to marketplace router"
```

---

### Task 11: Create and run seed script

**Files:**
- Create: `scripts/seed_creator_listings.py`

- [ ] **Step 1: Create scripts/ directory if missing**

```bash
mkdir -p /home/tife/Lavoo-Business-Decision-Engine/scripts
```

- [ ] **Step 2: Write seed script**

Create `scripts/seed_creator_listings.py`:

```python
"""
Seed 2 creator listings from real users to verify all fields work.
Usage: PYTHONPATH=. uv run python scripts/seed_creator_listings.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv(".env.local")

from database.pg_connections import SessionLocal
from database.pg_models import CreatorListing, User

def main():
    db = SessionLocal()
    try:
        # Pick the first two users in the DB
        users = db.query(User).limit(2).all()
        if len(users) < 1:
            print("ERROR: No users found in database — create a user first.")
            sys.exit(1)

        user1 = users[0]
        user2 = users[1] if len(users) > 1 else users[0]

        listings_data = [
            {
                "user_id": user1.id,
                "title": "Social Media Content Automation Playbook",
                "description": "A step-by-step playbook for automating weekly social media content using AI tools. Covers scheduling, caption generation, and cross-platform posting.",
                "full_description": "This playbook walks you through setting up a fully automated social media pipeline. You'll learn how to connect AI writing tools for caption generation, schedule posts across Instagram, TikTok, and LinkedIn from one dashboard, and track performance metrics automatically. Includes templates, tool links, and a 7-day launch checklist.",
                "listing_type": "Playbook",
                "category": "Marketing",
                "price": 0.0,
                "tags": ["social media", "automation", "content", "AI", "scheduling"],
                "features": [
                    "7-day launch checklist",
                    "AI caption generation templates",
                    "Cross-platform scheduling guide",
                    "Performance tracking setup",
                    "Works with Buffer, Later, and Hootsuite",
                ],
                "icon_name": "Zap",
                "color_theme": "orange",
                "purchase_url": None,
            },
            {
                "user_id": user2.id,
                "title": "Freelance Invoice & Proposal Automation Kit",
                "description": "A ready-to-use template kit and workflow guide for automating client proposals, contracts, and invoice reminders as a freelancer.",
                "full_description": "Stop chasing clients manually. This kit includes proposal templates triggered by intake forms, contract auto-send workflows, invoice generation on project completion, and payment reminder sequences at 3-day and 7-day overdue intervals. Built for freelancers using tools like Dubsado, HoneyBook, or Bonsai.",
                "listing_type": "Template",
                "category": "Automation",
                "price": 29.0,
                "tags": ["freelance", "invoicing", "proposals", "contracts", "automation"],
                "features": [
                    "Proposal template triggered by intake form",
                    "Auto contract send on proposal acceptance",
                    "Invoice generation on project completion",
                    "Payment reminder sequences (3-day + 7-day)",
                    "Compatible with Dubsado, HoneyBook, Bonsai",
                ],
                "icon_name": "Package",
                "color_theme": "blue",
                "purchase_url": "https://example.com/freelance-kit",
            },
        ]

        for data in listings_data:
            # Avoid duplicate seeding
            existing = db.query(CreatorListing).filter_by(
                user_id=data["user_id"], title=data["title"]
            ).first()
            if existing:
                print(f"  SKIP (already exists): {data['title']}")
                continue

            listing = CreatorListing(**data)
            db.add(listing)
            db.flush()
            print(f"  CREATED id={listing.id}: [{data['listing_type']}] {data['title']} — user_id={data['user_id']}, price=${data['price']}")

        db.commit()
        print("\nSeed complete. Verifying all fields round-trip...")

        # Verify fields
        for data in listings_data:
            row = db.query(CreatorListing).filter_by(
                user_id=data["user_id"], title=data["title"]
            ).first()
            assert row is not None, f"Missing row for {data['title']}"
            assert row.listing_type == data["listing_type"]
            assert row.tags == data["tags"]
            assert row.features == data["features"]
            assert row.icon_name == data["icon_name"]
            assert row.color_theme == data["color_theme"]
            assert row.purchase_url == data["purchase_url"]
            print(f"  OK: {row.title} (id={row.id}, tags={row.tags[:2]}...)")

        print("\nAll fields verified successfully.")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the seed script**

```bash
PYTHONPATH=. uv run python scripts/seed_creator_listings.py
```
Expected output:
```
  CREATED id=1: [Playbook] Social Media Content Automation Playbook — user_id=..., price=$0.0
  CREATED id=2: [Template] Freelance Invoice & Proposal Automation Kit — user_id=..., price=$29.0

Seed complete. Verifying all fields round-trip...
  OK: Social Media Content Automation Playbook (id=1, tags=['social media', 'automation']...)
  OK: Freelance Invoice & Proposal Automation Kit (id=2, tags=['freelance', 'invoicing']...)

All fields verified successfully.
```

- [ ] **Step 4: Verify via the API**

Start the server if not running:
```bash
PYTHONPATH=. uv run uvicorn api.main:app --reload --port 8000
```

Fetch listings (replace TOKEN):
```bash
curl -s http://localhost:8000/api/marketplace/listings \
  -H "Authorization: Bearer TOKEN" | python -m json.tool
```
Expected: JSON with `listings` array containing 2 items, each with all fields present.

- [ ] **Step 5: Commit**

```bash
git add scripts/seed_creator_listings.py
git commit -m "feat: add seed script for creator listings, 2 seeded rows verified"
```

---

### Task 12: Frontend — Add CreateListingModal and parallel fetch

**Files:**
- Modify: `lavoo_main_app/app/(main)/dashboard/market-place/page.tsx`

- [ ] **Step 1: Add Plus import from lucide-react**

In `page.tsx`, add `Plus` to the lucide-react import line:
```typescript
// OLD:
import {
  Search, ShoppingBag, Zap, TrendingUp, ShieldCheck, Globe, Cpu, Star,
  X, Download, LayoutGrid, DollarSign, MousePointer2, Check, Package,
  BarChart3, Loader2, AlertCircle, CheckCircle2
} from 'lucide-react';

// NEW (add Plus):
import {
  Search, ShoppingBag, Zap, TrendingUp, ShieldCheck, Globe, Cpu, Star,
  X, Download, LayoutGrid, DollarSign, MousePointer2, Check, Package,
  BarChart3, Loader2, AlertCircle, CheckCircle2, Plus
} from 'lucide-react';
```

- [ ] **Step 2: Add CreatorListing interface**

After the existing `MarketplaceStats` interface, add:

```typescript
interface CreatorListing {
  id: number;
  name: string;
  title: string;
  author: string;
  description: string;
  full_description: string | null;
  listing_type: string;
  category: string;
  price: number;
  tags: string[];
  features: string[];
  icon_name: string;
  color_theme: string;
  purchase_url: string | null;
  sales_count: number;
  rating: number;
  review_count: number;
  is_active: boolean;
  created_at: string | null;
  source: 'user_listing';
}

type MarketplaceItem = MarketplaceTool | CreatorListing;

const LISTING_TYPES = ["Template", "Playbook", "Service", "Tool", "Course", "Automation", "Consulting", "Strategy"] as const;
const COLOR_THEMES = ["orange", "blue", "violet", "emerald", "pink", "indigo"] as const;
```

- [ ] **Step 3: Add CreateListingModal component**

Add this component after the `RequestModal` component (before `// ─── Page`):

```typescript
// ─── Create Listing Modal ───────────────────────────────────────────────────────

interface CreateListingModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (listing: CreatorListing) => void;
}

function CreateListingModal({ open, onClose, onCreated }: CreateListingModalProps) {
  const [form, setForm] = useState({
    title: '', description: '', full_description: '',
    listing_type: 'Template', category: 'Automation',
    price: '0', tags: '', features: '',
    icon_name: 'Cpu', color_theme: 'orange', purchase_url: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  function reset() {
    setForm({
      title: '', description: '', full_description: '',
      listing_type: 'Template', category: 'Automation',
      price: '0', tags: '', features: '',
      icon_name: 'Cpu', color_theme: 'orange', purchase_url: '',
    });
    setErrorMsg('');
  }

  function handleClose() { reset(); onClose(); }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim() || !form.description.trim()) return;
    setSubmitting(true);
    setErrorMsg('');
    try {
      const token = getAuthToken();
      const body = {
        title: form.title.trim(),
        description: form.description.trim(),
        full_description: form.full_description.trim() || null,
        listing_type: form.listing_type,
        category: form.category,
        price: parseFloat(form.price) || 0,
        tags: form.tags.split(',').map(s => s.trim()).filter(Boolean),
        features: form.features.split('\n').map(s => s.trim()).filter(Boolean),
        icon_name: form.icon_name,
        color_theme: form.color_theme,
        purchase_url: form.purchase_url.trim() || null,
      };
      const res = await fetch(`${API_BASE}/api/marketplace/listings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed to create listing' }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const created: CreatorListing = await res.json();
      onCreated(created);
      handleClose();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to create listing');
    } finally {
      setSubmitting(false);
    }
  }

  const f = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm(prev => ({ ...prev, [field]: e.target.value }));

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) handleClose(); }}>
      <DialogContent className="sm:max-w-[620px] p-0 overflow-hidden rounded-[2.5rem] border-none shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-10 space-y-6">
          <div className="flex justify-between items-start">
            <div className="space-y-1">
              <h2 className={`text-2xl font-black text-gray-900 ${montserrat.className}`}>Create a Listing</h2>
              <p className="text-gray-500 text-sm font-medium">Share your template, playbook, or service with the community.</p>
            </div>
            <DialogClose className="p-2 rounded-full bg-gray-100/50 hover:bg-gray-200 transition-colors">
              <X className="h-5 w-5 text-gray-500" />
            </DialogClose>
          </div>

          {errorMsg && (
            <div className="flex items-start gap-3 bg-red-50 border border-red-200 text-red-800 rounded-2xl px-5 py-4 text-sm font-medium">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5 text-red-500" />
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <label className="text-sm font-bold text-gray-700">Title <span className="text-red-500">*</span></label>
              <Input value={form.title} onChange={f('title')} placeholder="e.g. Social Media Content Playbook" className="rounded-2xl border-gray-200" required />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-bold text-gray-700">Type</label>
                <select value={form.listing_type} onChange={f('listing_type')} className="w-full rounded-2xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:border-brand-primary bg-white">
                  {LISTING_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-bold text-gray-700">Category</label>
                <select value={form.category} onChange={f('category')} className="w-full rounded-2xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:border-brand-primary bg-white">
                  {["Automation", "AI Tools", "Marketing", "Analytics", "CRM", "Security", "Other"].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-bold text-gray-700">Short Description <span className="text-red-500">*</span></label>
              <textarea value={form.description} onChange={f('description')} rows={2} placeholder="One or two sentences describing what this listing does..." className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:border-brand-primary resize-none" required />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-bold text-gray-700">Full Description</label>
              <textarea value={form.full_description} onChange={f('full_description')} rows={4} placeholder="Detailed overview shown in the listing detail view..." className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:border-brand-primary resize-none" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-bold text-gray-700">Price (USD)</label>
                <Input type="number" min="0" step="0.01" value={form.price} onChange={f('price')} placeholder="0 for free" className="rounded-2xl border-gray-200" />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-bold text-gray-700">Purchase URL</label>
                <Input value={form.purchase_url} onChange={f('purchase_url')} placeholder="https://..." className="rounded-2xl border-gray-200" />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-bold text-gray-700">Tags <span className="text-xs font-normal text-gray-400">(comma-separated)</span></label>
              <Input value={form.tags} onChange={f('tags')} placeholder="e.g. automation, social media, AI" className="rounded-2xl border-gray-200" />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-bold text-gray-700">Features <span className="text-xs font-normal text-gray-400">(one per line)</span></label>
              <textarea value={form.features} onChange={f('features')} rows={3} placeholder={"7-day launch checklist\nAI caption generation templates\nCross-platform scheduling guide"} className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:border-brand-primary resize-none" />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-bold text-gray-700">Colour Theme</label>
              <div className="flex gap-3">
                {COLOR_THEMES.map(c => (
                  <button key={c} type="button" onClick={() => setForm(p => ({ ...p, color_theme: c }))}
                    className={`w-8 h-8 rounded-full border-2 transition-all ${colorStyles[c]?.iconBg ?? 'bg-gray-100'} ${form.color_theme === c ? 'border-gray-700 scale-110' : 'border-transparent'}`}
                  />
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="ghost" onClick={handleClose} className="rounded-2xl px-6">Cancel</Button>
              <Button type="submit" disabled={submitting} className="rounded-2xl px-8 bg-brand-primary text-white hover:bg-brand-primary/90">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                {submitting ? 'Creating...' : 'Create Listing'}
              </Button>
            </div>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: Update page state**

In `MarketplacePage`, add new state variables after `const [requestOpen, setRequestOpen] = useState(false);`:

```typescript
const [listings, setListings] = useState<CreatorListing[]>([]);
const [listingOpen, setListingOpen] = useState(false);
```

- [ ] **Step 5: Replace single fetch with Promise.all**

Replace the entire `useEffect` / `fetchMarketplace` function (the one that fetches tools) with:

```typescript
useEffect(() => {
  async function fetchMarketplace() {
    setLoading(true);
    setFetchError(null);
    try {
      const token = getAuthToken();
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const [toolsRes, listingsRes] = await Promise.all([
        fetch(`${API_BASE}/api/marketplace/tools`, { headers }),
        fetch(`${API_BASE}/api/marketplace/listings`, { headers }),
      ]);
      if (!toolsRes.ok) throw new Error(`Tools fetch failed: HTTP ${toolsRes.status}`);
      const toolsData: MarketplaceResponse = await toolsRes.json();
      setTools(toolsData.tools ?? []);
      if (toolsData.stats) setStats(toolsData.stats);
      if (listingsRes.ok) {
        const listingsData = await listingsRes.json();
        setListings(listingsData.listings ?? []);
      }
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Failed to load marketplace');
    } finally {
      setLoading(false);
    }
  }
  fetchMarketplace();
}, []);
```

- [ ] **Step 6: Merge tools + listings in filter computation**

Replace:
```typescript
const filteredTools = tools.filter((tool) => {
  if (!tool.is_active) return false;
  const matchesTab = activeTab === "All" || tool.category === activeTab;
  const q = searchQuery.toLowerCase();
  const matchesSearch =
    tool.name.toLowerCase().includes(q) ||
    tool.description.toLowerCase().includes(q) ||
    tool.tags.some((tag) => tag.toLowerCase().includes(q));
  return matchesTab && matchesSearch;
});
```
with:
```typescript
const filteredItems: MarketplaceItem[] = [...tools, ...listings].filter((item) => {
  if (!item.is_active) return false;
  const matchesTab = activeTab === "All" || item.category === activeTab;
  const q = searchQuery.toLowerCase();
  const displayName = (item as CreatorListing).title ?? item.name;
  const matchesSearch =
    displayName.toLowerCase().includes(q) ||
    item.description.toLowerCase().includes(q) ||
    item.tags.some((tag) => tag.toLowerCase().includes(q));
  return matchesTab && matchesSearch;
});
```

- [ ] **Step 7: Add "Create Listing" button to the controls bar**

In the controls bar section, find the "Filters" button:
```tsx
<Button variant="outline" className="rounded-xl px-7 py-2 border-dashed border-gray-300 text-gray-400 hover:text-gray-600 font-bold ml-2">
  Filters
</Button>
```
Replace with:
```tsx
<div className="flex items-center gap-2 ml-2">
  <Button variant="outline" className="rounded-xl px-7 py-2 border-dashed border-gray-300 text-gray-400 hover:text-gray-600 font-bold">
    Filters
  </Button>
  <Button
    onClick={() => setListingOpen(true)}
    className="rounded-xl px-5 py-2 bg-brand-primary text-white hover:bg-brand-primary/90 font-bold flex items-center gap-2"
  >
    <Plus className="h-4 w-4" />
    Create Listing
  </Button>
</div>
```

- [ ] **Step 8: Update the grid to render filteredItems with listing badge**

Find `filteredTools.map((tool, index) => {` and replace with `filteredItems.map((item, index) => {`.

Update all `tool.` references inside the map to `item.`:
- `tool.id` → `item.id`
- `tool.color_theme` → `item.color_theme`
- `tool.icon_name` → `item.icon_name`
- `tool.price` → `item.price`
- `tool.sales_count` → `item.sales_count`
- `tool.name` → `(item as CreatorListing).title ?? item.name`
- `tool.tags` → `item.tags`
- `tool.description` → `item.description`

Also update the empty state check: `filteredTools.length > 0` → `filteredItems.length > 0`.

Add a listing type badge inside the card. After the opening card motion.div `<div className="relative z-10 flex flex-col h-full">`, add:
```tsx
{'source' in item && item.source === 'user_listing' && (
  <div className="absolute top-4 right-4 z-20">
    <Badge className="bg-brand-primary/10 text-brand-primary border-none text-xs font-bold px-2 py-0.5">
      {(item as CreatorListing).listing_type}
    </Badge>
  </div>
)}
```

- [ ] **Step 9: Mount CreateListingModal and wire onCreated**

Add to the JSX return (after `<RequestModal`):
```tsx
<CreateListingModal
  open={listingOpen}
  onClose={() => setListingOpen(false)}
  onCreated={(listing) => setListings(prev => [listing, ...prev])}
/>
```

- [ ] **Step 10: Verify frontend builds**

```bash
cd /home/tife/lavoo_main_app && npm run build
```
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 11: Smoke test in browser**

```bash
cd /home/tife/lavoo_main_app && npm run dev
```
Open `http://localhost:3000/dashboard/market-place`.
- Listings from seed should appear in the grid with a type badge.
- Clicking "Create Listing" opens the modal.
- Submitting a valid form creates a listing and it appears in the grid immediately.

- [ ] **Step 12: Commit**

```bash
cd /home/tife/lavoo_main_app
git add app/\(main\)/dashboard/market-place/page.tsx
git commit -m "feat: add CreateListingModal, parallel fetch, and merged grid to marketplace"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All items from both specs covered — uvloop, dual-model split, `_llm()` helper, parallel Stage 3A, parallel Stage 3B enrichment, BackgroundTask for Stage 3B, N+1 fix, `CreatorListing` model, Alembic migration, 5 CRUD endpoints, seed script, frontend modal + fetch + grid.
- [x] **Placeholder scan:** No TBDs or TODOs. All code blocks are complete.
- [x] **Type consistency:** `_enrich_single_stack` → called from `_enrich_stacks_with_llm` ✓. `_attach_toolkit` → called from `_stage3_action_plans` ✓. `_listing_dict` → used in all listing endpoints ✓. `CreatorListing` interface → used in `CreateListingModal`, `onCreated`, `listings` state ✓.
