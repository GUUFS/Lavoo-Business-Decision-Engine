"""
Ad checkup addresses (logic in decision_engine/guest_checkup.py).

  POST /api/public/checkup/stream   no login: run a check-up, streamed like the
                                    normal one; starts with {token}, ends with
                                    {token, teaser}. Keeps running if the page
                                    disconnects.
  GET  /api/public/checkup/{token}  no login: where it is up to (running /
                                    completed / failed) and the teaser
  POST /api/public/checkup/claim    login: become the owner, get the analysis id
  POST /api/public/checkup/failure  no login: the page reports a check-up that
                                    failed in the browser (logged, may alert)
  POST /api/public/checkup/track    no login: the page's Meta Pixel events, sent
                                    on to Meta from the server too

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
from services import meta_capi

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public/checkup", tags=["public-checkup"])


class GuestCheckupRequest(BaseModel):
    """What the checkup page sends."""
    business_goal: str = Field(..., max_length=4000)
    visitor_id: str | None = Field(None, max_length=64)   # random id the browser keeps
    utm_source: str | None = Field(None, max_length=100)
    utm_campaign: str | None = Field(None, max_length=150)
    # For the Meta server event (the same ids the browser Pixel used).
    event_id: str | None = Field(None, max_length=100)
    fbp: str | None = Field(None, max_length=200)
    fbc: str | None = Field(None, max_length=300)
    page_url: str | None = Field(None, max_length=1000)


class ClaimRequest(BaseModel):
    """The secret code the browser kept through signup."""
    token: str = Field(..., min_length=10, max_length=64)
    # For the Meta CompleteRegistration event.
    event_id: str | None = Field(None, max_length=100)
    fbp: str | None = Field(None, max_length=200)
    fbc: str | None = Field(None, max_length=300)


class FailureReport(BaseModel):
    """A check-up that failed in the browser (e.g. the connection dropped)."""
    reason: str = Field(..., min_length=1, max_length=500)
    visitor_id: str | None = Field(None, max_length=64)


class TrackRequest(BaseModel):
    """One Meta Pixel event the page fired, to send from the server too."""
    event: str = Field(..., max_length=40)
    event_id: str = Field(..., max_length=100)
    page_url: str | None = Field(None, max_length=1000)
    visitor_id: str | None = Field(None, max_length=64)
    fbp: str | None = Field(None, max_length=200)
    fbc: str | None = Field(None, max_length=300)


def _client_ip(request: Request) -> str | None:
    """The visitor's address (behind Railway's proxy: the first X-Forwarded-For entry)."""
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else None)


def _sse(event: str, data: dict) -> str:
    """One server-sent event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# Check-ups still running after their page disconnected. Kept here so Python
# doesn't throw the unfinished task away; each removes itself when done.
_running: set[asyncio.Task] = set()


def _task_session() -> Session:
    """The analysis's own database session. The request's session closes when
    the page disconnects, but the analysis keeps going, so it needs its own.
    (Tests swap this for their session.)"""
    from database.pg_connections import SessionLocal
    return SessionLocal()


def _keep_running(coro) -> asyncio.Task:
    """Start a task that outlives the request, holding a reference until it ends."""
    task = asyncio.create_task(coro)
    _running.add(task)
    task.add_done_callback(_running.discard)
    return task


@router.post("/stream")
async def run_guest_checkup(body: GuestCheckupRequest, request: Request, background_tasks: BackgroundTasks,
                            db: Session = Depends(get_db)):
    """Run a check-up for a visitor with no account.

    Events: `started` {token} first, then `progress`, then `result`
    {token, teaser} (or `error` / `unsafe`).

    If the connection drops (common on mobile data), the analysis KEEPS
    RUNNING and is saved. The page already has the token from `started`, so
    it asks GET /{token} until the result is ready. Nothing is lost."""
    from api.routes.decision_engine.analyzer import _enrich_stacks_background
    from decision_engine.agentic_analyzer import create_analyzer
    from decision_engine.tool_discovery import discover_tools_for_analysis

    # 1. Check the text and the free limits, then record the check-up (429 = sign up instead).
    goal = guest_checkup.clean_goal(body.business_goal)
    row = guest_checkup.start(db, goal, body.visitor_id, guest_checkup.hash_ip(_client_ip(request)),
                              body.utm_source, body.utm_campaign)
    # Read these now, while the session still holds the row: once the answer
    # starts streaming, the row object can no longer be read or saved.
    checkup_id, token = row.id, row.token
    # 2. Tell Meta from the server too that a check-up started (same id as the browser's).
    background_tasks.add_task(
        meta_capi.send_event, "StartCheckup", body.event_id, external_id=body.visitor_id,
        ip=_client_ip(request), user_agent=request.headers.get("user-agent"), fbp=body.fbp, fbc=body.fbc,
        source_url=body.page_url)
    queue: asyncio.Queue = asyncio.Queue()

    async def progress(pct: int, msg: str):
        """Pass the analyzer's progress to the page (if it is still there)."""
        await queue.put(("progress", {"pct": pct, "msg": msg}))

    async def run():
        """3. The normal analysis, saved with no owner, in its own session."""
        task_db = _task_session()
        try:
            result = await create_analyzer(task_db).analyze(user_query=goal, user_id=None,
                                                            progress_callback=progress)
            analysis_id = result["data"].get("analysis_id")
            guest_checkup.finish(task_db, checkup_id, analysis_id=analysis_id)
            # 3a. Only the teaser goes back to the page.
            analysis = task_db.get(BusinessAnalysis, analysis_id)
            await queue.put(("result", {"token": token, "teaser": guest_checkup.teaser(analysis)}))
            # 3b. The same follow-up work as a normal check-up (better tool
            #     stacks, tool discovery), started separately so the page isn't kept waiting.
            stacks = result["data"].get("recommended_tool_stacks") or []
            if stacks:
                _keep_running(_enrich_stacks_background(
                    analysis_id=analysis_id, raw_stacks=stacks, user_query=goal,
                    bottleneck_title=(result["data"].get("primary_bottleneck") or {}).get("title", "")))
            _keep_running(discover_tools_for_analysis(analysis_id, result["data"]))
        except Exception as exc:
            # 3c. Failed: saved as failed (the free slot is given back) and logged.
            logger.error(f"[guest-checkup] failed: {exc}", exc_info=True)
            guest_checkup.finish(task_db, checkup_id, error=str(exc))
            text = str(exc)
            if text.startswith("UNSAFE_QUERY::"):
                parts = text.split("::", 2)
                await queue.put(("unsafe", {"reason": parts[1] if len(parts) > 1 else "This can't be processed."}))
            else:
                await queue.put(("error", {"message": "The check-up couldn't finish. Please try again."}))
        finally:
            await queue.put(None)
            if task_db is not db:
                task_db.close()

    async def stream():
        """4. Send the token first, then events as they come, with a keep-alive
        every 4 seconds. If the page goes away, the analysis carries on."""
        _keep_running(run())
        yield _sse("started", {"token": token})
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=4.0)
            except TimeoutError:
                yield ": keepalive\n\n"
                continue
            if item is None:
                break
            yield _sse(*item)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/{token}")
def get_checkup(token: str, db: Session = Depends(get_db)):
    """Where a check-up is up to, for a page that lost its connection or was
    reloaded: status running | completed | claimed | failed, and the teaser
    once it is ready."""
    # 1. Unknown or deleted.
    row = guest_checkup.find(db, token)
    if not row:
        raise HTTPException(status_code=404, detail="This check-up can't be found. Run a new one.")
    # 2. Still running, or failed: no teaser yet.
    status = "running" if row.status == "started" else row.status
    data = {"token": token, "status": status, "claimed": row.status == "claimed", "teaser": None}
    if status in ("running", "failed"):
        return {"success": True, "data": data}
    # 3. Finished: the teaser (its analysis may have been deleted since).
    analysis = db.get(BusinessAnalysis, row.analysis_id) if row.analysis_id else None
    if analysis is None:
        raise HTTPException(status_code=404, detail="This check-up can't be found. Run a new one.")
    data["teaser"] = guest_checkup.teaser(analysis)
    return {"success": True, "data": data}


@router.post("/claim")
def claim_checkup(body: ClaimRequest, request: Request, background_tasks: BackgroundTasks,
                  current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """After signup/login: the user becomes the owner and gets the analysis id to open."""
    # 1. Hand the analysis over.
    analysis_id = guest_checkup.claim(db, body.token, current_user)
    # 2. Tell Meta from the server that an ad visitor created their account.
    background_tasks.add_task(
        meta_capi.send_event, "CompleteRegistration", body.event_id, email=current_user.email,
        external_id=current_user.id, ip=_client_ip(request), user_agent=request.headers.get("user-agent"),
        fbp=body.fbp, fbc=body.fbc, custom_data={"content_name": "check-up"})
    return {"success": True, "data": {"analysis_id": analysis_id}}


@router.post("/failure")
def report_failure(body: FailureReport, db: Session = Depends(get_db)):
    """The page lost a check-up (e.g. the connection dropped): log it with
    the reason. Several in an hour email the admin."""
    guest_checkup.record_failure(db, "browser", body.reason, visitor_id=body.visitor_id)
    return {"success": True}


@router.post("/track")
def track_event(body: TrackRequest, request: Request, background_tasks: BackgroundTasks):
    """Send one of the page's Meta Pixel events from the server as well, so
    ad blockers don't hide it. Only the ad page's events are accepted."""
    # 1. Only the known events (nobody can send made-up ones).
    if body.event not in meta_capi.BROWSER_EVENTS:
        raise HTTPException(status_code=400, detail="Unknown event.")
    # 2. Send it in the background (the page doesn't wait for Meta).
    background_tasks.add_task(
        meta_capi.send_event, body.event, body.event_id, external_id=body.visitor_id,
        ip=_client_ip(request), user_agent=request.headers.get("user-agent"), fbp=body.fbp, fbc=body.fbc,
        source_url=body.page_url)
    return {"success": True}
