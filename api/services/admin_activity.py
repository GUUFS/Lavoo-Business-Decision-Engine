"""
Admin activity stamps: every change an admin makes from the admin end is
recorded with WHO did it, WHAT it was, and WHEN, for transparency.

HOW IT WORKS
  1. A middleware in api/main.py (record_admin_actions) sees every request.
  2. should_record() keeps only CHANGES (POST/PUT/PATCH/DELETE) that come
     from the admin end: an admin-only address (/api/control, /api/admin,
     /api/security), or any address called from the admin website (its
     Origin/Referer is control.* or admin.*, or listed in ADMIN_APP_ORIGINS).
  3. record() runs after the response is sent (in a worker thread): it works
     out who made the request from their login token, skips anyone who isn't
     an admin, and saves one admin_activity row with a plain-words
     description (describe()) and whether it worked (the HTTP status).
  Request bodies are never stored, so passwords and messages can't leak
  into the log.

Shown on the admin Activity page (api/routes/admin/activity.py) and as
"by <admin> on <date>" stamps on records.
"""
import logging
import os
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_ADMIN_PATH_PREFIXES = ("/api/control/", "/api/admin/", "/api/security/", "/admin/", "/security/")
# Extra admin website origins, comma-separated (e.g. a staging admin site).
_EXTRA_ADMIN_ORIGINS = {o.strip().rstrip("/") for o in os.getenv("ADMIN_APP_ORIGINS", "").split(",") if o.strip()}

# Plain-words descriptions: (method, path pattern after "/api", description).
# {name} in the description is filled from the pattern's (?P<name>...) group.
_RULES = [
    ("POST", r"/control/refunds/payments/(?P<id>[^/]+)/refund", "Refunded Stripe payment {id}"),
    ("POST", r"/control/user-emails", "Sent an email to a user"),
    ("POST", r"/control/account/password", "Changed their own admin password"),
    ("POST", r"/control/contact/(?P<id>\d+)/reply", "Replied to contact message #{id}"),
    ("PATCH", r"/control/contact/(?P<id>\d+)/status", "Changed the status of contact message #{id}"),
    ("DELETE", r"/control/contact/(?P<id>\d+)", "Deleted contact message #{id}"),
    ("PATCH", r"/control/permissions/(?P<id>\d+)/role", "Changed the role of user #{id}"),
    ("PATCH", r"/control/permissions/(?P<id>\d+)/staff", "Changed staff status of user #{id}"),
    ("PATCH", r"/control/permissions/(?P<id>\d+)/partner", "Changed partner status of user #{id}"),
    ("POST", r"/control/revenue/commissions/approve/(?P<id>\d+)", "Approved builder bonuses for user #{id}"),
    ("POST", r"/control/revenue/payouts/retry/(?P<id>\d+)", "Retried payout #{id}"),
    ("POST", r"/control/revenue/payouts/simulate-complete/(?P<id>\d+)", "Marked payout #{id} as completed (simulated)"),
    ("PATCH", r"/control/settings", "Changed platform settings"),
    ("POST", r"/control/staff-referral-pool", "Added a staff member to the referral pool"),
    ("DELETE", r"/control/staff-referral-pool/(?P<id>\d+)", "Removed entry #{id} from the staff referral pool"),
    ("POST", r"/control/staff-referral-pool/backfill", "Assigned unreferred signups to the staff referral pool"),
    ("PATCH", r"/control/users/(?P<id>\d+)/status", "Changed the account status of user #{id}"),
    ("PATCH", r"/admin/users/(?P<id>\d+)/status", "Changed the account status of user #{id}"),
    ("DELETE", r"/control/users/(?P<id>\d+)", "Deleted user #{id}"),
    ("POST", r"/control/users/delete-bulk", "Deleted several users"),
    ("POST", r"/control/users/generate-referral-codes", "Generated missing referral codes"),
    ("POST", r"/control/users/sync-subscriptions", "Re-synced user subscriptions"),
    ("POST", r"/admin/charge-beta-users", "Charged beta users' saved cards"),
    ("POST", r"/admin/fix-expired-subscriptions", "Fixed expired subscriptions"),
    ("POST", r"/admin/update-existing-analyses", "Updated existing analyses"),
    ("POST", r"/admin/content/(?P<kind>alerts|insights)", "Created a new {kind} item"),
    ("PUT", r"/admin/content/(?P<kind>alerts|insights)/(?P<id>\d+)", "Edited {kind} item #{id}"),
    ("DELETE", r"/admin/content/(?P<kind>alerts|insights)/(?P<id>\d+)", "Deleted {kind} item #{id}"),
    ("POST", r"/security/block-ip", "Blocked an IP address"),
    ("POST", r"/security/unblock-ip", "Unblocked an IP address"),
    ("POST", r"/security/firewall/rules", "Added a firewall rule"),
    ("PATCH", r"/security/firewall/rules/(?P<id>\d+)", "Changed firewall rule #{id}"),
    ("DELETE", r"/security/firewall/rules/(?P<id>\d+)", "Deleted firewall rule #{id}"),
    ("POST", r"/security/scan/(?P<kind>full|database)", "Ran a {kind} security scan"),
    ("POST", r"/business/clarify/teach", "Ran the micromodel teacher"),
    ("POST", r"/business/clarify/exam", "Added a micromodel exam question"),
    ("DELETE", r"/business/clarify/exam/(?P<id>\d+)", "Removed micromodel exam question #{id}"),
    ("POST", r"/business/clarify/exam/run", "Ran the micromodel exam"),
    ("POST", r"/business/clarify/llm-answers-to-check/(?P<id>\d+)", "Checked LLM answer #{id}"),
    ("POST", r"/business/tools/discover", "Ran tool discovery"),
    ("POST", r"/control/team/members", "Added a team member"),
    ("PATCH", r"/control/team/members/(?P<id>\d+)", "Changed the title or role of team member #{id}"),
    ("POST", r"/control/team/members/(?P<id>\d+)/reset-password", "Reset the password of team member #{id}"),
    ("DELETE", r"/control/team/members/(?P<id>\d+)", "Removed team member #{id} from the admin team"),
    ("POST", r"/control/team/roles", "Created an admin role"),
    ("PATCH", r"/control/team/roles/(?P<id>\d+)", "Changed admin role #{id}"),
    ("DELETE", r"/control/team/roles/(?P<id>\d+)", "Deleted admin role #{id}"),
]
_COMPILED = [(m, re.compile(rf"^{p}/?$"), d) for m, p, d in _RULES]
_VERBS = {"POST": "Did", "PUT": "Updated", "PATCH": "Updated", "DELETE": "Deleted"}


def _host_of(url: str | None) -> str:
    """'control.lavooai.com' from 'https://control.lavooai.com/admin/x'."""
    if not url:
        return ""
    return (urlparse(url).hostname or "").lower()


def is_from_admin_site(origin_or_referer: str | None) -> bool:
    """True if the request came from the admin website."""
    if not origin_or_referer:
        return False
    host = _host_of(origin_or_referer)
    origin = f"{urlparse(origin_or_referer).scheme}://{urlparse(origin_or_referer).netloc}".rstrip("/")
    return host.startswith(("control.", "admin.")) or origin in _EXTRA_ADMIN_ORIGINS


def should_record(method: str, path: str, origin_or_referer: str | None) -> bool:
    """A change made from the admin end (who made it is checked in record())."""
    # 1. Only changes, never reads.
    if method.upper() not in _WRITE_METHODS:
        return False
    # 2. An admin-only address, or any address called from the admin website.
    return path.startswith(_ADMIN_PATH_PREFIXES) or is_from_admin_site(origin_or_referer)


def describe(method: str, path: str) -> str:
    """A plain-words description of the change, e.g. 'Refunded Stripe payment ch_1'."""
    short = path[4:] if path.startswith("/api/") else path
    # 1. A known action.
    for rule_method, pattern, text in _COMPILED:
        found = pattern.match(short)
        if rule_method == method.upper() and found:
            return text.format(**found.groupdict())
    # 2. Anything else: the verb and the address, readably.
    parts = [p for p in short.strip("/").split("/") if p and p not in ("control", "admin")]
    return f"{_VERBS.get(method.upper(), method.upper())}: {' → '.join(parts) or '/'}"


def record(authorization: str | None, cookie_token: str | None, method: str, path: str,
           query: str, status_code: int, ip: str | None) -> None:
    """Save one admin_activity row if the requester is an admin. Never raises
    (runs after the response, in a worker thread)."""
    from api.routes.auth.login import get_current_user
    from database.pg_connections import SessionLocal
    from database.pg_models import AdminActivity

    db = SessionLocal()
    try:
        # 1. Who made the request (skip anyone not logged in or not an admin).
        try:
            user = get_current_user(authorization, cookie_token, db)
        except Exception:
            return
        if not user or not getattr(user, "is_admin", False):
            return
        # 2. Their admin role at this moment ("Owner", "Finance").
        from api.services.admin_access import access_of
        role = access_of(db, user)["role"]
        # 3. Save the stamp (a 403 is a change their role didn't allow; it's kept as a failed attempt).
        db.add(AdminActivity(
            admin_id=user.id, admin_name=user.name, admin_email=user.email, admin_role=role,
            method=method.upper(), path=path[:500], query=(query or "")[:500] or None,
            action=describe(method, path)[:300], status_code=status_code,
            succeeded=200 <= status_code < 400, ip_address=(ip or "")[:64] or None,
        ))
        db.commit()
    except Exception as e:
        logger.warning(f"[admin-activity] couldn't record {method} {path}: {e}")
        db.rollback()
    finally:
        db.close()


def stamp(db, admin_id: int | None, when) -> dict | None:
    """{'by': name, 'by_email': email, 'at': iso} for showing "by X on <date>" on a record."""
    if not admin_id:
        return None
    from database.pg_models import User
    admin = db.get(User, admin_id)
    return {"by": admin.name if admin else f"User #{admin_id}", "by_email": admin.email if admin else None,
            "at": when.isoformat() if when else None}
