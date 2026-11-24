"""
Application monitoring: what has gone wrong in the running server, so the
admin Engine Health page (decision_engine/health.py) can show it and the
admin is emailed when something breaks.

  1. Errors     - every ERROR log line anywhere in the app (a payment webhook
                  that failed, a job that crashed, an email that bounced, an
                  unhandled exception in a request) is kept in memory for 24
                  hours, with the area it came from (payments, email, ...).
  2. Requests   - every response with status 500 or above is counted.
  3. Jobs       - each background job is started through watch_job(); if one
                  stops (crashes or ends), that is recorded.
  4. Alerts     - run_health_alert_job() runs the health checks every 5
                  minutes and emails ADMIN_ALERT_EMAIL when a check starts
                  failing, and again when it recovers (one email per change).

All of this lives in the server's memory: it starts empty after a deploy or
restart. Nothing here changes data.
"""
import asyncio
import logging
import os
import threading
import time
from collections import deque
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# How long errors and failed requests are kept, and at most how many.
KEEP_SECONDS = 24 * 3600
MAX_KEPT = 2000

# Which part of the app an error came from, by the logger's name (module path)
# or a tag at the start of the message. First match wins.
_AREAS = [
    ("payments", ("subscriptions", "stripe", "flutterwave", "paypal", "payout", "commission", "revenue", "refund")),
    ("email", ("emailing", "email")),
    ("meta", ("meta_capi",)),
    ("checkups", ("decision_engine", "analyzer", "guest-checkup", "checkup")),
    ("micromodel", ("clarity", "micromodel", "exam-job", "teacher")),
    ("auth", ("auth", "login")),
    ("database", ("sqlalchemy", "database", "pg_")),
]

_lock = threading.Lock()
_errors: deque = deque(maxlen=MAX_KEPT)          # (time, area, logger name, message)
_failed_requests: deque = deque(maxlen=MAX_KEPT)  # (time, method, path, status)
_jobs: dict[str, dict] = {}                       # name -> {started, stopped, error}
_started_at = time.time()


def area_of(logger_name: str, message: str) -> str:
    """The part of the app a log line belongs to ('other' if unknown)."""
    text = f"{logger_name} {message[:60]}".lower()
    for area, words in _AREAS:
        if any(word in text for word in words):
            return area
    return "other"


def _prune(items: deque, now: float) -> None:
    """Drop entries older than KEEP_SECONDS (oldest are on the left)."""
    while items and now - items[0][0] > KEEP_SECONDS:
        items.popleft()


class _ErrorCollector(logging.Handler):
    """Keeps every ERROR (and worse) log line, with its area."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # 1. The message (and the exception, if there was one).
            message = record.getMessage()
            if record.exc_info and record.exc_info[1] is not None:
                message += f" ({type(record.exc_info[1]).__name__}: {record.exc_info[1]})"
            # 2. Kept with its time and area.
            with _lock:
                _errors.append((record.created, area_of(record.name, message), record.name, message[:500]))
        except Exception:
            # A monitoring problem must never break logging itself.
            pass


_collector = _ErrorCollector(level=logging.ERROR)


def install() -> None:
    """Start collecting errors (safe to call more than once). Uvicorn's own
    loggers don't pass their lines to the root logger, so they get it too."""
    for name in ("", "uvicorn", "uvicorn.error"):
        target = logging.getLogger(name)
        if _collector not in target.handlers:
            target.addHandler(_collector)


def record_request(method: str, path: str, status: int) -> None:
    """Remember a response with status 500 or above."""
    if status >= 500:
        with _lock:
            _failed_requests.append((time.time(), method, path, status))


def recent_errors(seconds: int = 3600, area: str | None = None) -> list[dict]:
    """Errors in the last `seconds` (newest first), optionally from one area."""
    now = time.time()
    with _lock:
        _prune(_errors, now)
        rows = [e for e in _errors if now - e[0] <= seconds and (area is None or e[1] == area)]
    return [{"at": datetime.fromtimestamp(t, UTC).isoformat(), "area": a, "logger": n, "message": m}
            for t, a, n, m in reversed(rows)]


def recent_failed_requests(seconds: int = 3600) -> list[dict]:
    """Responses with status 500+ in the last `seconds` (newest first)."""
    now = time.time()
    with _lock:
        _prune(_failed_requests, now)
        rows = [r for r in _failed_requests if now - r[0] <= seconds]
    return [{"at": datetime.fromtimestamp(t, UTC).isoformat(), "method": m, "path": p, "status": s}
            for t, m, p, s in reversed(rows)]


def uptime_seconds() -> int:
    """How long this server has been running (monitoring data covers only this)."""
    return int(time.time() - _started_at)


# ------------------------------------------------------------------ jobs

def watch_job(name: str, coro) -> asyncio.Task:
    """Start a background job and record if it ever stops (a crash, or an
    early return). Returns the task."""
    _jobs[name] = {"started": time.time(), "stopped": None, "error": None}

    async def runner():
        try:
            await coro
            _jobs[name].update(stopped=time.time(), error="The job ended by itself.")
        except asyncio.CancelledError:
            # Server shutting down: not a failure.
            raise
        except Exception as exc:
            _jobs[name].update(stopped=time.time(), error=f"{type(exc).__name__}: {exc}"[:300])
            logger.error(f"[monitoring] background job {name} crashed: {exc}", exc_info=True)

    return asyncio.create_task(runner())


def jobs() -> dict[str, dict]:
    """Each watched job: started, stopped (None while running) and error."""
    return {name: dict(info) for name, info in _jobs.items()}


# ------------------------------------------------------------------ alerts

# The last status of each health check, to email only when it changes.
_last_status: dict[str, str] = {}


def _send_alert(subject: str, lines: list[str]) -> None:
    """Email the admin (ADMIN_ALERT_EMAIL, else SUPPORT_EMAIL). Never raises."""
    try:
        from emailing.email_service import email_service
        to = os.getenv("ADMIN_ALERT_EMAIL", os.getenv("SUPPORT_EMAIL", "support@lavoo.io"))
        text = "\n".join(lines) + "\n\nDetails: the admin panel's Engine Health page."
        html_body = "".join(f"<p>{line}</p>" for line in lines) + "<p>Details: the admin panel's Engine Health page.</p>"
        email_service._send_email(to_email=to, to_name="Lavoo Admin", subject=subject,
                                  html_content=html_body, text_content=text)
    except Exception as exc:
        logger.warning(f"[monitoring] alert email not sent: {exc}")


def alerts_for(checks: list[dict]) -> tuple[list[str], list[str]]:
    """Compare checks with the last run: (newly failing lines, recovered lines).
    The very first run only remembers the statuses (no email after a deploy
    for something that was already known)."""
    first_run = not _last_status
    broken, fixed = [], []
    for check in checks:
        before = _last_status.get(check["key"])
        now = check["status"]
        if not first_run and now == "fail" and before != "fail":
            broken.append(f"{check['name']}: {check['detail']}")
        if not first_run and before == "fail" and now != "fail":
            fixed.append(f"{check['name']} is working again.")
        _last_status[check["key"]] = now
    return broken, fixed


async def run_health_alert_job():
    """Every 5 minutes: run the health checks and email the admin when a
    check starts failing or recovers."""
    from database.pg_connections import SessionLocal
    from decision_engine.health import run_health_checks
    # 1. Let the server finish starting.
    await asyncio.sleep(120)
    while True:
        try:
            # 2. The same checks as the Engine Health page (no live LLM call).
            with SessionLocal() as db:
                result = await run_health_checks(db)
            # 3. Email only what changed.
            broken, fixed = alerts_for(result["checks"])
            if broken:
                _send_alert(f"⚠️ Lavoo: {len(broken)} part(s) stopped working", broken)
            if fixed:
                _send_alert("✅ Lavoo: working again", fixed)
        except Exception as exc:
            logger.error(f"[monitoring] health alert job error: {exc}")
        # 4. Again in 5 minutes.
        await asyncio.sleep(300)
