"""
Simulation of a normal person signing up for Lavoo, checking that nothing
along the way answers 403 (Forbidden) when it shouldn't.

Runs the REAL app (api/main.py: every route, the firewall middleware, auth,
the free trial and the Decision Engine gate) through FastAPI's TestClient,
against a throwaway local Postgres database (lavoo_signup_sim). Only the
outside world is faked: emails are recorded instead of sent, Google's OAuth
servers answer from a stub, and every other network connection is refused.

Journeys, each run under several app modes (APP_MODE / LAUNCH_DATE):
  1. Email signup:  POST /api/signup -> /api/signup/verify -> /api/login,
     then the requests the website makes on the first visit (login page
     prefetch, layout, home feed, Decision Engine pages, Missions).
  2. Google signup: /api/auth/google/callback with a new Google account.
  3. Ad check-up:   a visitor's finished check-up is claimed after signup,
     then its result and Missions are opened (/l/checkup-result/ID).
  4. Route sweep:   every user-facing route, called as the new account.
     Decision Engine routes must let a trial account in; no other route may
     answer 403 except admin-only ones.
  5. Trial over:    after the free trial, only the Decision Engine may say 403.
  6. Firewall:      the first page load, fired as one burst from one IP.

Usage (needs a LOCAL Postgres with pgvector; see memory/local-test-environment):

    SIM_BASE_DATABASE_URL=postgresql://postgres@localhost/postgres \\
        venv/bin/python -m tests.simulation.signup_journey_simulation --out /tmp/signup_sim

Prints a summary, writes report.json and report.md to --out, and exits 1 if
any check failed.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import signal
import sys
import time
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.simulation import payment_simulation as payment_sim  # noqa: E402

SIM_DB_NAME = "lavoo_signup_sim"
PASSWORD = "Sim-Passw0rd!"
REQUEST_TIMEOUT_SECONDS = 20

# The app modes a new person can sign up under. "launch_date" is DD/MM/YYYY
# like the real setting; None means no launch date is set.
TODAY = datetime.now(UTC)
SCENARIOS = [
    {"name": "launch mode, launched", "APP_MODE": "launch",
     "LAUNCH_DATE": (TODAY - timedelta(days=30)).strftime("%d/%m/%Y")},
    {"name": "launch mode, no launch date", "APP_MODE": "launch", "LAUNCH_DATE": None},
    {"name": "launch mode, launch date ahead", "APP_MODE": "launch",
     "LAUNCH_DATE": (TODAY + timedelta(days=10)).strftime("%d/%m/%Y")},
    {"name": "beta mode, launch date ahead", "APP_MODE": "beta",
     "LAUNCH_DATE": (TODAY + timedelta(days=10)).strftime("%d/%m/%Y")},
    {"name": "beta mode, no launch date", "APP_MODE": "beta", "LAUNCH_DATE": None},
    {"name": "beta mode, launch date passed", "APP_MODE": "beta",
     "LAUNCH_DATE": (TODAY - timedelta(days=30)).strftime("%d/%m/%Y")},
]

# What the website asks for on a new user's first visit (lib/api.ts paths):
# the login page's prefetch, the sidebar/header, and the home feed.
FIRST_VISIT = [
    "/api/profile", "/api/user/stats", "/api/alerts", "/api/beta-status",
    "/api/alerts/paginated?page=1&limit=7", "/api/notifications",
    "/api/alerts/paginated?page=1&limit=2&today_only=true", "/api/user/progress",
]
# The Decision Engine and Missions pages (gated by subscriber_or_ad_checkup_owner).
DECISION_ENGINE_VISIT = [
    "/api/business/checkups/allowance", "/api/business/analyses?limit=1",
    "/api/business/analyses?limit=10", "/api/missions", "/api/missions/active",
    "/api/missions/constraints/active",
]
DECISION_ENGINE_PREFIXES = ("/api/business", "/api/missions")
# Routes the sweep never calls: endless streams, and ones that would end
# the session (logout, account deletion) part-way through the sweep.
SKIP_PATTERN = re.compile(r"stream|/sse|/ws\b|websocket|logout|delete-account|/events$", re.I)
# The detail every admin-only check answers with (admin_required, get_admin_user).
# (and moderator-only ones for The Signal's authoring tools).
ADMIN_ONLY_DETAILS = ("You do not have permission to access this resource.", "Admin access required",
                      "Administrative privileges required", "Only moderators can")

_ids = itertools.count(1)


# ── Recording results ───────────────────────────────────────────────────────

class Report:
    """Every check the simulation makes, with pass/fail and details."""

    def __init__(self) -> None:
        """Start with no checks."""
        # 1. One dict per check.
        self.checks: list[dict] = []

    def check(self, scenario: str, journey: str, name: str, ok: bool, detail: str = "") -> bool:
        """Record one check and return whether it passed."""
        # 1. Save it.
        self.checks.append({"scenario": scenario, "journey": journey, "check": name, "ok": bool(ok), "detail": detail})
        # 2. Show failures as they happen.
        if not ok:
            print(f"  FAIL [{scenario}] {journey}: {name} {detail}")
        return bool(ok)

    @property
    def failures(self) -> list[dict]:
        """The checks that failed."""
        # 1. Only the failed ones.
        return [c for c in self.checks if not c["ok"]]


# ── Environment ─────────────────────────────────────────────────────────────

def set_environment(sim_url: str) -> None:
    """Point the app at the throwaway database and fake credentials BEFORE
    any app module is imported (the app reads these at import time)."""
    # 1. Database, secrets and providers (all fake).
    os.environ.update({
        "DATABASE_URL": sim_url, "SECRET_KEY": "signup-simulation-secret", "ENVIRONMENT": "development",
        "STRIPE_SECRET_KEY": "sk_test_simulation", "NEXT_PUBLIC_FLUTTERWAVE_SECRET_KEY": "FLWSECK_TEST-simulation",
        "REDIS_URL": "", "BASE_URL": "http://localhost", "FRONTEND_URL": "http://frontend.local",
        "GOOGLE_CLIENT_ID": "sim-google-client", "GOOGLE_CLIENT_SECRET": "sim-google-secret",
    })


def create_tables() -> None:
    """Create every table from database/pg_models.py (the embedding columns
    get their real vector(384) type so CREATE TABLE works)."""
    from sqlalchemy.types import NullType, UserDefinedType

    from database.pg_connections import engine
    from database.pg_models import Base

    class Vector384(UserDefinedType):
        """DDL-only stand-in for Postgres's vector(384) type."""
        cache_ok = True

        def get_col_spec(self, **kw):
            """The column type in CREATE TABLE."""
            # 1. pgvector's type.
            return "vector(384)"

    # 1. Give untyped embedding columns their database type.
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, NullType):
                column.type = Vector384()
    # 2. Create everything.
    Base.metadata.create_all(engine)


@contextmanager
def app_mode(scenario: dict):
    """Run with this scenario's APP_MODE and LAUNCH_DATE, whatever is in .env."""
    from subscriptions.beta_service import BetaService

    # 1. The settings BetaService reads (its .env reader is replaced, so the
    #    real .env file can't change the scenario).
    settings = {"APP_MODE": scenario["APP_MODE"]}
    if scenario["LAUNCH_DATE"]:
        settings["LAUNCH_DATE"] = scenario["LAUNCH_DATE"]
    saved = {k: os.environ.pop(k, None) for k in ("APP_MODE", "LAUNCH_DATE", "BETA_MODE")}
    try:
        with patch.object(BetaService, "_get_dynamic_env", staticmethod(lambda: dict(settings))):
            yield
    finally:
        # 2. Put the environment back.
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value


def fake_outside_world(stack: ExitStack) -> list[tuple]:
    """Record emails instead of sending them, answer Google OAuth from a stub,
    and never block on Meta. Returns the list emails are recorded in."""
    from api.routes.auth import google_oauth
    from emailing.email_service import email_service

    sent: list[tuple] = []

    # 1. Every email_service.send_* just records its arguments.
    for attr in dir(email_service):
        if attr.startswith("send_") and callable(getattr(email_service, attr)):
            stack.enter_context(patch.object(
                email_service, attr, (lambda name: lambda *a, **k: sent.append((name, a)) or True)(attr)))

    # 2. Google: the token exchange and userinfo answer with the account the
    #    test put in the code (code = "sim:<email>").
    class FakeGoogleResponse:
        """One answer from the fake Google servers."""

        def __init__(self, payload: dict) -> None:
            """Hold the JSON to return."""
            # 1. Always 200.
            self.status_code, self._payload, self.text = 200, payload, json.dumps(payload)

        def json(self) -> dict:
            """The JSON body."""
            # 1. As given.
            return self._payload

    class FakeGoogleClient:
        """Stands in for httpx.AsyncClient inside google_oauth."""

        async def __aenter__(self):
            """Open (nothing to do)."""
            # 1. Itself.
            return self

        async def __aexit__(self, *exc):
            """Close (nothing to do)."""
            # 1. Don't swallow errors.
            return False

        async def post(self, url, data=None, **kwargs):
            """The token exchange: the code carries the test account's email."""
            # 1. A token that is just the email.
            return FakeGoogleResponse({"access_token": (data or {}).get("code", "").removeprefix("sim:")})

        async def get(self, url, headers=None, **kwargs):
            """Userinfo for that token."""
            # 1. The email back from the bearer token.
            email = (headers or {}).get("Authorization", "").removeprefix("Bearer ")
            return FakeGoogleResponse({"id": f"g-{email}", "email": email, "name": "Google Sim", "picture": None})

    stack.enter_context(patch.object(google_oauth.httpx, "AsyncClient", FakeGoogleClient))
    # 3. The Meta conversion event after a check-up claim is not under test.
    stack.enter_context(patch("api.routes.public_checkup.meta_capi.send_event", lambda *a, **k: None))
    return sent


# ── Calling the app ─────────────────────────────────────────────────────────

class _Timeout(Exception):
    """A request took longer than REQUEST_TIMEOUT_SECONDS."""


def _on_alarm(signum, frame):
    """SIGALRM handler: give up on the current request."""
    # 1. Interrupt the wait.
    raise _Timeout()


def call(client, method: str, path: str, token: str | None = None, **kwargs):
    """One request to the app, with a time limit. Returns (status, json-or-text);
    status is 0 on a timeout or a crash inside the test client."""
    # 1. Authenticate like the website does (Authorization header).
    headers = dict(kwargs.pop("headers", {}) or {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # 2. Send it, giving up after the time limit.
    signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(REQUEST_TIMEOUT_SECONDS)
    try:
        response = client.request(method, path, headers=headers, follow_redirects=False, **kwargs)
    except _Timeout:
        return 0, "timeout"
    except Exception as exc:  # the app raised through the test client
        return 0, f"{type(exc).__name__}: {exc}"
    finally:
        signal.alarm(0)
    # 3. The body, as JSON if it is JSON.
    try:
        return response.status_code, response.json()
    except Exception:
        return response.status_code, response.text[:300]


def detail_of(body) -> str:
    """The error message in a response body ("detail"), or the body itself."""
    # 1. FastAPI errors put it in "detail".
    if isinstance(body, dict):
        return str(body.get("detail") or body.get("message") or body)[:200]
    return str(body)[:200]


def new_client():
    """A fresh browser: the real app, no cookies, errors returned as 500s."""
    from fastapi.testclient import TestClient

    from api.main import app
    # 1. raise_server_exceptions=False: a crash shows up as a 500, like in production.
    client = TestClient(app, base_url="http://localhost", raise_server_exceptions=False)
    # 2. A real-looking public IP, sent the way Railway's proxy sends it (the
    #    test client's own address is the word "testclient", which the
    #    ip_blacklist inet column rejects).
    client.headers["X-Forwarded-For"] = f"203.0.113.{next(_ids) % 250 + 1}"
    return client


@contextmanager
def firewall_flood_check(enabled: bool):
    """Turn the firewall's 25-requests-a-second flood block off (for the
    sweep, which fires far faster than a person) or leave it on."""
    from api.security.firewall import firewall_manager
    # 1. Off: the flood check always allows.
    if not enabled:
        with patch.object(firewall_manager, "_analyze_behavior", lambda *a, **k: None):
            yield
        return
    # 2. On: start counting from zero.
    firewall_manager._behavior_tracking = {}
    yield


# ── Journeys ────────────────────────────────────────────────────────────────

def email_signup(report: Report, scenario: str, client) -> tuple[str | None, str]:
    """Sign up with email and password, verify the emailed code, and log in.
    Returns (access token, email)."""
    from database.pg_connections import SessionLocal
    from database.pg_models import PendingSignup

    email = f"new{next(_ids)}.{int(time.time())}@sim.local"
    j = "email signup"
    # 1. The signup form.
    status, body = call(client, "POST", "/api/signup", data={
        "name": "New Person", "email": email, "password": PASSWORD, "confirm_password": PASSWORD})
    if not report.check(scenario, j, "POST /api/signup succeeds", status == 200, f"{status} {detail_of(body)}"):
        return None, email
    # 2. The code from the email (read where the app keeps it).
    with SessionLocal() as db:
        pending = db.query(PendingSignup).filter(PendingSignup.email == email).first()
        code = pending.verification_code if pending else ""
    # 3. Verify it.
    status, body = call(client, "POST", "/api/signup/verify", data={"email": email, "code": code})
    if not report.check(scenario, j, "POST /api/signup/verify succeeds", status == 200, f"{status} {detail_of(body)}"):
        return None, email
    # 4. Log in, as /login?registered=true makes them do.
    status, body = call(client, "POST", "/api/login", json={"email": email, "password": PASSWORD})
    if not report.check(scenario, j, "POST /api/login succeeds", status == 200, f"{status} {detail_of(body)}"):
        return None, email
    # 5. What the website stores from the login answer (app/(auth)/login/page.tsx
    #    setAuth). Without decision_engine_access, the frontend treats a trial
    #    account as having no access until /api/profile loads.
    report.check(scenario, j, "login answer says whether the account can use the Decision Engine",
                 isinstance(body, dict) and "decision_engine_access" in body,
                 f"login answer fields: {sorted(body) if isinstance(body, dict) else body}")
    return (body.get("access_token") if isinstance(body, dict) else None), email


def google_signup(report: Report, scenario: str, client) -> str | None:
    """Sign up with a new Google account. Returns the access token."""
    email = f"google{next(_ids)}.{int(time.time())}@sim.local"
    j = "google signup"
    # 1. Google sends the browser back with a code.
    status, body = call(client, "GET", f"/api/auth/google/callback?code=sim:{email}")
    # 2. The redirect to the website carries the token (not an error page).
    status_ok = status in (302, 303, 307)
    report.check(scenario, j, "Google callback redirects to the website", status_ok, f"{status} {detail_of(body)}")
    if not status_ok:
        return None
    token = _last_redirect_token(client, email)
    report.check(scenario, j, "redirect is the login, not ?error=", bool(token))
    return token


def _last_redirect_token(client, email: str) -> str | None:
    """The token in the Google callback's redirect (re-requested to read its
    Location header, which call() doesn't return)."""
    # 1. Ask again: the account now exists, so this is a normal Google login.
    response = client.get(f"/api/auth/google/callback?code=sim:{email}", follow_redirects=False)
    # 2. Read token=... from the redirect.
    query = parse_qs(urlparse(response.headers.get("location", "")).query)
    return (query.get("token") or [None])[0]


def make_ad_checkup() -> str:
    """A finished check-up a visitor ran from an ad before signing up
    (decision_engine/guest_checkup.py). Returns its claim code."""
    from database.pg_connections import SessionLocal
    from database.pg_models import BusinessAnalysis, GuestCheckup

    token = f"simclaim{next(_ids):08d}{int(time.time())}"
    with SessionLocal() as db:
        # 1. The analysis, with no owner yet.
        analysis = BusinessAnalysis(business_goal="Get more customers for my bakery")
        db.add(analysis)
        db.flush()
        # 2. The guest record, finished and waiting to be claimed.
        db.add(GuestCheckup(token=token, business_goal=analysis.business_goal, status="completed",
                            analysis_id=analysis.id))
        db.commit()
    return token


def visit(report: Report, scenario: str, journey: str, client, token: str, paths: list[str],
          forbidden_ok: bool = False) -> list[tuple[str, int, str]]:
    """Open these paths as the user. Each must not answer 403 (unless
    forbidden_ok). Returns (path, status, detail) for each."""
    results = []
    for path in paths:
        # 1. Ask for it.
        status, body = call(client, "GET", path, token)
        results.append((path, status, detail_of(body)))
        # 2. A normal user must never be refused here.
        if not forbidden_ok:
            report.check(scenario, journey, f"GET {path} is not 403", status != 403, f"{status} {detail_of(body)}")
    return results


def user_routes():
    """Every route a logged-in user could reach: (method, path template, is Decision Engine)."""
    from fastapi.routing import APIRoute

    from api.main import app
    routes = []
    for route in app.routes:
        # 1. Only API routes under /api, never admin ones or endless streams.
        if not isinstance(route, APIRoute) or not route.path.startswith("/api"):
            continue
        if "/admin" in route.path or "/control" in route.path or SKIP_PATTERN.search(route.path):
            continue
        is_de = route.path.startswith(DECISION_ENGINE_PREFIXES)
        for method in sorted(route.methods or ()):
            # 2. Every GET; for the Decision Engine, also the writes (sent with
            #    an empty body: the gate answers before the body is checked).
            if method == "GET" or (is_de and method in ("POST", "PUT", "PATCH", "DELETE")):
                routes.append((method, route.path, is_de))
    return routes


def fill_path(template: str, user_id: int | None = None) -> str:
    """A path with {user_id} filled with the account's own id (as the website
    sends it) and every other {param} with an id that doesn't exist."""
    # 1. Their own id; numbers for other ids; words for everything else.
    def value(match):
        name = match.group(1).split(":")[0]
        if name == "user_id" and user_id:
            return str(user_id)
        return "999999" if name.endswith("id") or name in ("step_number", "page") else "sim-missing"
    return re.sub(r"\{([^}]+)\}", value, template)


def sweep(report: Report, scenario: str, client, token: str, user_id: int | None, trial_over: bool = False) -> dict:
    """Call every user route as this account. Decision Engine routes may say
    403 only once the trial is over; nothing else may, except admin-only
    routes. Returns counts by outcome."""
    journey = "route sweep (trial over)" if trial_over else "route sweep"
    counts = {"called": 0, "admin_only_403": 0, "de_403": 0, "other_403": 0, "server_errors": 0}
    for method, template, is_de in user_routes():
        path = fill_path(template, user_id)
        # 1. Call it (writes get an empty JSON body).
        kwargs = {"json": {}} if method != "GET" else {}
        status, body = call(client, method, path, token, **kwargs)
        counts["called"] += 1
        if status >= 500 or status == 0:
            # Not a 403, but still a break: keep which route it was.
            counts["server_errors"] += 1
            counts.setdefault("server_error_routes", []).append(f"{method} {template} -> {status} {detail_of(body)[:80]}")
        if status != 403:
            continue
        detail = detail_of(body)
        # 2. Admin-only routes: 403 is right for a normal user.
        if any(d in detail for d in ADMIN_ONLY_DETAILS):
            counts["admin_only_403"] += 1
            continue
        # 3. The Decision Engine: 403 only after the trial.
        if is_de:
            counts["de_403"] += 1
            report.check(scenario, journey, f"{method} {template} lets the account in", trial_over,
                         f"403 {detail}")
            continue
        # 4. Anything else refusing a normal user.
        counts["other_403"] += 1
        report.check(scenario, journey, f"{method} {template} is not 403", False, f"403 {detail}")
    report.check(scenario, journey, "sweep ran", counts["called"] > 50, json.dumps(counts))
    return counts


def end_trial(email: str) -> None:
    """Move this account's free trial end into the past."""
    from database.pg_connections import SessionLocal
    from database.pg_models import User
    with SessionLocal() as db:
        # 1. Ended an hour ago.
        user = db.query(User).filter(User.email == email).first()
        user.grace_period_ends_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()


def first_visit_burst(report: Report, scenario: str, client, token: str) -> int:
    """The first page load (login prefetch + layout + home feed + Decision
    Engine widgets), fired as fast as one browser can, with the firewall's
    flood check on. Returns how many requests were sent."""
    paths = FIRST_VISIT + DECISION_ENGINE_VISIT + ["/api/profile", "/api/beta-status", "/api/user/stats"]
    blocked = []
    with firewall_flood_check(enabled=True):
        for path in paths:
            # 1. Each request of the burst.
            status, body = call(client, "GET", path, token)
            if status == 403 and "flood" in json.dumps(body).lower() + str(body).lower():
                blocked.append(path)
    # 2. None of a normal page load may be taken for a flood.
    report.check(scenario, "first-visit burst", f"{len(paths)} requests at once are not blocked as a flood",
                 not blocked, f"blocked: {blocked}")
    return len(paths)


def run_scenario(report: Report, scenario: dict, summary: dict) -> None:
    """Every journey under one app mode."""
    name = scenario["name"]
    print(f"\n== {name} ==")
    info: dict = {}
    with app_mode(scenario), firewall_flood_check(enabled=False):
        # 1. Email signup, then the first visit and the Decision Engine pages.
        client = new_client()
        token, email = email_signup(report, name, client)
        if token:
            status, profile = call(client, "GET", "/api/profile", token)
            info["trial_ends_at"] = (profile or {}).get("decision_engine_access_ends_at") if isinstance(profile, dict) else None
            info["profile_says_access"] = (profile or {}).get("decision_engine_access") if isinstance(profile, dict) else None
            report.check(name, "email signup", "/api/profile says the new account can use the Decision Engine",
                         info["profile_says_access"] is True, f"profile: access={info['profile_says_access']} "
                         f"ends_at={info['trial_ends_at']}")
            visit(report, name, "first visit", client, token, FIRST_VISIT)
            visit(report, name, "Decision Engine pages", client, token, DECISION_ENGINE_VISIT)
            # 2. Every route.
            info["user_id"] = profile.get("id") if isinstance(profile, dict) else None
            info["sweep"] = sweep(report, name, client, token, info["user_id"])

        # 3. Google signup.
        gclient = new_client()
        gtoken = google_signup(report, name, gclient)
        if report.check(name, "google signup", "redirect carries a token", bool(gtoken)):
            visit(report, name, "google signup", gclient, gtoken, FIRST_VISIT + DECISION_ENGINE_VISIT)

        # 4. Ad check-up: sign up, claim it, open its result and Missions.
        aclient = new_client()
        claim_code = make_ad_checkup()
        atoken, _ = email_signup(report, name, aclient)
        if atoken:
            status, body = call(aclient, "POST", "/api/public/checkup/claim", atoken, json={"token": claim_code})
            ok = report.check(name, "ad check-up", "claim succeeds", status == 200, f"{status} {detail_of(body)}")
            if ok:
                analysis_id = body["data"]["analysis_id"]
                visit(report, name, "ad check-up", aclient, atoken,
                      [f"/api/business/analyses/{analysis_id}", f"/api/missions/{analysis_id}"])

    # 5. After the trial (back in normal launch mode): nothing but the
    #    Decision Engine may refuse them.
    if token:
        end_trial(email)
        with firewall_flood_check(enabled=False):
            info["sweep_trial_over"] = sweep(report, name, client, token, info.get("user_id"), trial_over=True)
        # 6. The first page load as one burst.
        info["burst_size"] = first_visit_burst(report, name, client, token)
    summary[name] = info


def write_report(report: Report, summary: dict, out: Path) -> None:
    """report.json (everything) and report.md (readable summary)."""
    out.mkdir(parents=True, exist_ok=True)
    # 1. Everything.
    (out / "report.json").write_text(json.dumps({"summary": summary, "checks": report.checks}, indent=2, default=str))
    # 2. The readable version.
    lines = ["# Signup journey simulation", "",
             f"{len(report.checks)} checks, {len(report.failures)} failed.", ""]
    for name, info in summary.items():
        failed = [c for c in report.failures if c["scenario"] == name]
        lines.append(f"## {name}: {'OK' if not failed else f'{len(failed)} failed'}")
        lines.append(f"- profile access: {info.get('profile_says_access')}, trial ends: {info.get('trial_ends_at')}")
        if "sweep" in info:
            lines.append(f"- sweep: {info['sweep']}")
        if "sweep_trial_over" in info:
            lines.append(f"- sweep after trial: {info['sweep_trial_over']}")
        for c in failed:
            lines.append(f"  - FAIL {c['journey']}: {c['check']} — {c['detail']}")
        lines.append("")
    (out / "report.md").write_text("\n".join(lines))


def main() -> int:
    """Build the database, run every scenario, write the report."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    # 1. A fresh local database, and the app pointed at it.
    base = os.environ.get("SIM_BASE_DATABASE_URL")
    if not base:
        raise SystemExit("Set SIM_BASE_DATABASE_URL to a LOCAL Postgres (with pgvector).")
    payment_sim.SIM_DB_NAME = SIM_DB_NAME
    sim_url = payment_sim.prepare_database(base)
    set_environment(sim_url)
    # 2. No real network (Postgres is on a local socket).
    payment_sim.install_network_guard()
    import api.routes.auth  # noqa: F401  (import order that avoids an existing circular import)
    from database.pg_connections import engine
    if SIM_DB_NAME not in str(engine.url):
        raise SystemExit(f"The app is not using the simulation database ({engine.url}); refusing to run.")
    create_tables()
    import api.main  # noqa: F401
    # 3. Every scenario.
    report, summary = Report(), {}
    with ExitStack() as stack:
        sent = fake_outside_world(stack)
        for scenario in SCENARIOS:
            run_scenario(report, scenario, summary)
    # 4. The report.
    write_report(report, summary, args.out)
    print(f"\n{len(report.checks)} checks, {len(report.failures)} failed. "
          f"Emails recorded: {len(sent)}. Blocked outside connections: {len(payment_sim.BLOCKED_CONNECTIONS)}.")
    print(f"Report: {args.out / 'report.md'}")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
