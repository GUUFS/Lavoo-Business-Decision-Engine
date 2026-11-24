"""
Monitoring (api/services/monitoring.py, decision_engine/health.py) and the
stuck-checkup fix (decision_engine/checkup_limits.py):

  - a streamed checkup's outcome is saved even after its request's session
    let go of the row (that bug left every streamed checkup at 'started');
  - checkups stuck at 'started' are completed (if their analysis was saved)
    or failed, which gives the checkup back;
  - errors logged anywhere show on the Engine Health page, by area;
  - a background job that stops is reported;
  - alert emails go out only when a check starts failing or recovers.
"""
import asyncio
import logging
from datetime import UTC, datetime, timedelta

from api.services import monitoring
from database.pg_models import BusinessAnalysis, CheckupUsage, GuestCheckup, User
from decision_engine import checkup_limits, guest_checkup, health


def _user(db, email):
    """A saved user."""
    user = User(name="M", email=email, password="x", confirm_password="x", is_admin=True)
    db.add(user)
    db.flush()
    return user


# ── The stuck checkups ──────────────────────────────────────────────────────

def test_the_outcome_is_saved_after_the_session_let_go_of_the_row(db):
    user = _user(db, "stream@mon.test")
    usage = checkup_limits.reserve_checkup(db, user)
    # 1. What the streaming route sees: the row expired by the commit and
    #    no longer attached to a session (reading usage.id would fail).
    db.expunge(usage)
    # 2. The outcome is still saved.
    checkup_limits.confirm_checkup(db, usage, analysis_id=None)
    row = db.query(CheckupUsage).filter(CheckupUsage.user_id == user.id).one()
    assert row.status == "completed" and row.finished_at is not None


def test_stuck_checkups_are_completed_or_given_back(db):
    now = datetime.now(UTC)
    user = _user(db, "stuck@mon.test")
    started = now - timedelta(hours=2)
    # 1. One whose analysis was saved, one that never got one.
    with_analysis = CheckupUsage(user_id=user.id, status="started", created_at=started)
    lost = CheckupUsage(user_id=user.id, status="started", created_at=now - timedelta(days=3))
    recent = CheckupUsage(user_id=user.id, status="started", created_at=now - timedelta(minutes=5))
    db.add_all([with_analysis, lost, recent])
    analysis = BusinessAnalysis(user_id=user.id, business_goal="x", created_at=started + timedelta(minutes=2))
    db.add(analysis)
    db.flush()
    # 2. Closed: completed with its analysis, and failed (given back).
    assert checkup_limits.close_stuck_checkups(db, now) == {"completed": 1, "failed": 1}
    assert (with_analysis.status, with_analysis.analysis_id) == ("completed", analysis.id)
    assert lost.status == "failed" and "Never finished" in lost.error
    # 3. One still running normally is left alone.
    assert recent.status == "started"


def test_stuck_ad_checkups_are_failed(db):
    row = GuestCheckup(token="stuck-token-123", business_goal="x", status="started",
                       created_at=datetime.now(UTC) - timedelta(hours=1))
    db.add(row)
    db.flush()
    assert guest_checkup.close_stuck(db) >= 1
    assert row.status == "failed"


# ── Errors, jobs and alerts ─────────────────────────────────────────────────

def test_logged_errors_show_by_area():
    monitoring.install()
    monitoring._errors.clear()
    monitoring._failed_requests.clear()
    logging.getLogger("subscriptions.stripe").error("Webhook signature check failed")
    logging.getLogger("emailing.email_service").error("Resend answered 500")
    logging.getLogger("subscriptions.stripe").info("Just information")
    monitoring.record_request("POST", "/api/stripe/webhook", 500)
    monitoring.record_request("GET", "/api/profile", 404)
    assert [e["area"] for e in monitoring.recent_errors()] == ["email", "payments"]
    status, detail = health._server_errors()
    assert status == "warn" and "payments 1" in detail and "/api/stripe/webhook" in detail
    assert len(monitoring.recent_failed_requests()) == 1


def test_payment_errors_and_missing_keys_show_on_payments(monkeypatch):
    for name in ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "FLUTTERWAVE_SECRET_KEY", "FLUTTERWAVE_WEBHOOK_SECRET"):
        monkeypatch.setenv(name, "set")
    monitoring._errors.clear()
    assert health._payments()[0] == "ok"
    logging.getLogger("subscriptions.flutterwave").error("Verify call timed out")
    status, detail = health._payments()
    assert status == "warn" and "Verify call timed out" in detail
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET")
    assert health._payments() == ("fail", health._payments()[1]) and "STRIPE_WEBHOOK_SECRET" in health._payments()[1]


def test_a_stopped_job_is_reported():
    async def crashes():
        raise RuntimeError("database gone")

    async def go():
        monitoring._jobs.clear()
        task = monitoring.watch_job("Payout reconcile", crashes())
        await asyncio.gather(task, return_exceptions=True)

    asyncio.run(go())
    status, detail = health._background_jobs()
    assert status == "fail" and "Payout reconcile" in detail and "database gone" in detail
    monitoring._jobs.clear()


def test_alerts_only_when_a_check_starts_failing_or_recovers():
    monitoring._last_status.clear()
    ok = {"key": "email", "name": "Email", "status": "ok", "detail": "fine"}
    bad = {**ok, "status": "fail", "detail": "No email service"}
    # 1. First run after a deploy: remembered, no email.
    assert monitoring.alerts_for([bad]) == ([], [])
    monitoring._last_status.clear()
    assert monitoring.alerts_for([ok]) == ([], [])
    # 2. Starts failing: one alert, not repeated.
    assert monitoring.alerts_for([bad]) == (["Email: No email service"], [])
    assert monitoring.alerts_for([bad]) == ([], [])
    # 3. Recovers.
    assert monitoring.alerts_for([ok]) == ([], ["Email is working again."])
