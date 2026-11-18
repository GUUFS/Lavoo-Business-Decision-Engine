"""
Ad checkup addresses (logic in decision_engine/guest_checkup.py).

  POST /api/public/checkup/stream   no login: run a checkup, streamed like the
                                    normal one; ends with {token, teaser}
  GET  /api/public/checkup/{token}  no login: the teaser again (page reload)
  POST /api/public/checkup/claim    login: become the owner, get the analysis id

The streamed result carries only the teaser, never the full plan, so the
full plan can't be read before signup.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.routes.auth.login import get_current_user
from database.pg_connections import get_db
from database.pg_models import BusinessAnalysis
from decision_engine import guest_checkup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public/checkup", tags=["public-checkup"])


class GuestCheckupRequest(BaseModel):
    """What the checkup page sends."""
    business_goal: str = Field(..., max_length=4000)
    visitor_id: str | None = Field(None, max_length=64)   # random id the browser keeps
    utm_source: str | None = Field(None, max_length=100)
    utm_campaign: str | None = Field(None, max_length=150)


class ClaimRequest(BaseModel):
    """The secret code the browser kept through signup."""
    token: str = Field(..., min_length=10, max_length=64)


def _client_ip(request: Request) -> str | None:
    """The visitor's address (behind Railway's proxy: the first X-Forwarded-For entry)."""
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else None)


def _sse(event: str, data: dict) -> str:
    """One server-sent event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
async def run_guest_checkup(body: GuestCheckupRequest, request: Request, background_tasks: BackgroundTasks,
                            db: Session = Depends(get_db)):
    """Run a checkup for a visitor with no account. Same events as the normal
    checkup (progress, error, unsafe), but `result` is {token, teaser}."""
    from api.routes.decision_engine.analyzer import _enrich_stacks_background
    from decision_engine.agentic_analyzer import create_analyzer
    from decision_engine.tool_discovery import discover_tools_for_analysis

    # 1. Check the text and the free limits, then record the checkup (429 = sign up instead).
    goal = guest_checkup.clean_goal(body.business_goal)
    row = guest_checkup.start(db, goal, body.visitor_id, guest_checkup.hash_ip(_client_ip(request)),
                              body.utm_source, body.utm_campaign)
    # Read these now, while the session still holds the row: once the answer
    # starts streaming, the row object can no longer be read or saved.
    checkup_id, token = row.id, row.token
    queue: asyncio.Queue = asyncio.Queue()

    async def progress(pct: int, msg: str):
        """Pass the analyzer's progress to the page."""
        await queue.put(("progress", {"pct": pct, "msg": msg}))

    async def run():
        """2. The normal analysis, saved with no owner (no clarifying questions for guests)."""
        try:
            result = await create_analyzer(db).analyze(user_query=goal, user_id=None, progress_callback=progress)
            analysis_id = result["data"].get("analysis_id")
            guest_checkup.finish(db, checkup_id, analysis_id=analysis_id)
            # 3. The same follow-up work as a normal checkup (better tool stacks, tool discovery).
            stacks = result["data"].get("recommended_tool_stacks") or []
            if stacks:
                background_tasks.add_task(
                    _enrich_stacks_background, analysis_id=analysis_id, raw_stacks=stacks, user_query=goal,
                    bottleneck_title=(result["data"].get("primary_bottleneck") or {}).get("title", ""))
            background_tasks.add_task(discover_tools_for_analysis, analysis_id, result["data"])
            # 4. Only the teaser goes back to the page.
            analysis = db.get(BusinessAnalysis, analysis_id)
            await queue.put(("result", {"token": token, "teaser": guest_checkup.teaser(analysis)}))
        except asyncio.CancelledError:
            guest_checkup.finish(db, checkup_id, error="The visitor left before it finished")
            raise
        except Exception as exc:
            logger.error(f"[guest-checkup] failed: {exc}", exc_info=True)
            guest_checkup.finish(db, checkup_id, error=str(exc))
            text = str(exc)
            if text.startswith("UNSAFE_QUERY::"):
                parts = text.split("::", 2)
                await queue.put(("unsafe", {"reason": parts[1] if len(parts) > 1 else "This can't be processed."}))
            else:
                await queue.put(("error", {"message": "The checkup couldn't finish. Please try again."}))
        finally:
            await queue.put(None)

    async def stream():
        """5. Send events as they come, with a keep-alive every 4 seconds."""
        task = asyncio.create_task(run())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=4.0)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if item is None:
                    break
                yield _sse(*item)
        finally:
            task.cancel()

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/{token}")
def get_teaser(token: str, db: Session = Depends(get_db)):
    """The teaser for a finished guest checkup (e.g. after a page reload)."""
    row = guest_checkup.find(db, token)
    if not row or not row.analysis_id or row.status not in ("completed", "claimed"):
        raise HTTPException(status_code=404, detail="This checkup can't be found. Run a new one.")
    analysis = db.get(BusinessAnalysis, row.analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="This checkup can't be found. Run a new one.")
    return {"success": True, "data": {"token": token, "claimed": row.status == "claimed",
                                      "teaser": guest_checkup.teaser(analysis)}}


@router.post("/claim")
def claim_checkup(body: ClaimRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """After signup/login: the user becomes the owner and gets the analysis id to open."""
    return {"success": True, "data": {"analysis_id": guest_checkup.claim(db, body.token, current_user)}}
