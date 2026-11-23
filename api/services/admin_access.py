"""
Admin team access: who in the company may SEE and who may CHANGE each part
of the admin panel.

HOW IT WORKS
  1. Every admin panel page is an "area" (AREAS below), e.g. Revenue, Users.
     Each area lists the backend addresses its page uses.
  2. A role (AdminRole in database/pg_models.py) holds permissions such as
     "revenue.view" (may look) or "revenue.manage" (may also change things;
     manage includes view).
  3. Every admin gets a role. The Owner role (and an admin with no role, i.e.
     the original admin account) has full access, including the Team page.
  4. A middleware in api/main.py (enforce_admin_access) calls check_request()
     for every request: reading an area needs .view, changing it (POST, PUT,
     PATCH, DELETE) needs .manage. An admin address that belongs to no area
     is Owner-only, so a new admin page is closed until it is added here.
  Ordinary users are not affected: they never had admin access, and the
  route's own admin check still turns them away.
"""
import logging

logger = logging.getLogger(__name__)

OWNER_ROLE = "Owner"
VIEW, MANAGE = "view", "manage"

# The admin panel's areas: key, label, sidebar group, what it covers, and the
# backend addresses (after "/api") its page uses.
AREAS = [
    {"key": "dashboard", "label": "Dashboard", "group": "Overview",
     "description": "Headline numbers and recent platform activity.",
     "paths": ["/admin/dashboard", "/admin/analytics", "/admin/activity-stream", "/admin/analyses",
               "/admin/analysis-types"]},
    {"key": "revenue", "label": "Revenue", "group": "Overview",
     "description": "Payments, Builder Bonuses and payouts to users.",
     "paths": ["/control/revenue", "/commissions/admin", "/payments/flutterwave/connectivity-check",
               "/payments/flutterwave/reconcile-payouts"]},
    {"key": "payouts", "label": "Payout Tracker", "group": "Overview",
     "description": "Where each Builder Bonus payout is.",
     "paths": ["/control/payout-tracker"]},
    {"key": "refunds", "label": "Refunds", "group": "Overview",
     "description": "Refund Stripe payments.",
     "paths": ["/control/refunds"]},
    {"key": "users", "label": "Users", "group": "Management",
     "description": "User accounts: details, status and deleting accounts.",
     "paths": ["/control/users", "/admin/users"]},
    {"key": "support", "label": "Support Desk", "group": "Management",
     "description": "Support tickets, chats and reviews.",
     "paths": ["/customer-service/admin", "/customer-service/ws/admin", "/admin/reviews"]},
    {"key": "contact", "label": "Contact", "group": "Management",
     "description": "Messages sent through the contact form.",
     "paths": ["/control/contact", "/support/contact/inquiries"]},
    {"key": "email_users", "label": "Email a User", "group": "Management",
     "description": "Send an email to a user.",
     "paths": ["/control/user-emails"]},
    {"key": "community_roles", "label": "Permissions", "group": "Management",
     "description": "Make users moderators, Staff or partners.",
     "paths": ["/control/permissions"]},
    {"key": "staff_referrals", "label": "Staff Referrals", "group": "Management",
     "description": "The staff referral pool.",
     "paths": ["/control/staff-referral-pool"]},
    {"key": "marketplace", "label": "Marketplace", "group": "Management",
     "description": "Marketplace tools and tool requests.",
     "paths": ["/marketplace/admin"]},
    {"key": "content", "label": "Content", "group": "Management",
     "description": "Alerts and insights shown to users.",
     "paths": ["/admin/content", "/alerts/admin"]},
    {"key": "feature_flags", "label": "Feature Flags", "group": "Management",
     "description": "Turn product features on and off.",
     "paths": ["/admin/mvp-features"]},
    {"key": "team", "label": "Team & Access", "group": "System",
     "description": "Admin team members, their roles and what each role may see and do.",
     "paths": ["/control/team"]},
    {"key": "activity", "label": "Admin Activity", "group": "System",
     "description": "Who did what in the admin panel, and when.",
     "paths": ["/control/activity"]},
    {"key": "security", "label": "Security", "group": "System",
     "description": "Firewall, blocked IPs and security scans.",
     "paths": ["/security"]},
    {"key": "fraud", "label": "Fraud Review", "group": "System",
     "description": "Suspicious accounts and referrals.",
     "paths": ["/control/fraud"]},
    {"key": "engine_health", "label": "Engine Health", "group": "System",
     "description": "Health of the Decision Engine.",
     "paths": ["/business/engine"]},
    {"key": "micromodel", "label": "Micromodel", "group": "System",
     "description": "Micromodel training, exams and tool discovery.",
     "paths": ["/business/clarify/", "/business/tools"]},
    {"key": "settings", "label": "Settings", "group": "System",
     "description": "Platform settings.",
     "paths": ["/control/settings"]},
    {"key": "maintenance", "label": "Maintenance", "group": "System",
     "description": "One-off repair jobs (charge beta users, fix subscriptions).",
     "paths": ["/admin/charge-beta-users", "/admin/fix-expired-subscriptions", "/admin/update-existing-analyses"]},
]
AREA_KEYS = [a["key"] for a in AREAS]
ALL_PERMISSIONS = [f"{key}.{level}" for key in AREA_KEYS for level in (VIEW, MANAGE)]

# Addresses every admin may use, whatever their role (their own account).
SELF_SERVICE_PATHS = ["/control/team/me", "/control/account"]

# Addresses that belong to the admin end. One of these that matches no area
# above is Owner-only.
ADMIN_PATHS = ["/control", "/admin", "/security", "/customer-service/admin", "/customer-service/ws/admin",
               "/commissions/admin", "/marketplace/admin", "/alerts/admin", "/business/clarify/",
               "/business/tools", "/business/engine", "/payments/flutterwave/connectivity-check",
               "/payments/flutterwave/reconcile-payouts", "/support/contact/inquiries"]


def _everything_but(*keys_and_levels: str) -> list[str]:
    """Manage on every area, except the given "area" (left out) or "area.view" (view only)."""
    out = []
    for key in AREA_KEYS:
        if key in keys_and_levels:
            continue
        out.append(f"{key}.{VIEW}" if f"{key}.{VIEW}" in keys_and_levels else f"{key}.{MANAGE}")
    return out


# The roles a company starts with (created the first time the Team page opens).
DEFAULT_ROLES = [
    {"name": OWNER_ROLE, "is_system": True,
     "description": "Full access to everything, including the team and its roles.",
     "permissions": ALL_PERMISSIONS},
    {"name": "Administrator",
     "description": "Runs the platform day to day: everything except managing the team.",
     "permissions": _everything_but("team.view")},
    {"name": "Developer",
     "description": "Engineering: engine health, micromodel, security, feature flags and maintenance.",
     "permissions": ["dashboard.view", "engine_health.manage", "micromodel.manage", "security.manage",
                     "feature_flags.manage", "maintenance.manage", "settings.view", "activity.view", "users.view"]},
    {"name": "Finance",
     "description": "Money: revenue, payouts, refunds and staff referrals.",
     "permissions": ["dashboard.view", "revenue.manage", "payouts.manage", "refunds.manage",
                     "staff_referrals.view", "fraud.view", "users.view"]},
    {"name": "Customer Support",
     "description": "Helps users: support desk, contact messages and emails.",
     "permissions": ["dashboard.view", "users.view", "support.manage", "contact.manage", "email_users.manage"]},
    {"name": "Content & Community",
     "description": "What users see: content, marketplace and community roles.",
     "permissions": ["dashboard.view", "content.manage", "marketplace.manage", "community_roles.manage"]},
    {"name": "Viewer",
     "description": "Read-only: can look at every area but change nothing.",
     "permissions": [f"{key}.{VIEW}" for key in AREA_KEYS if key != "team"]},
]


def _short(path: str) -> str:
    """The address without its "/api" start: "/api/control/x" -> "/control/x"."""
    return path[4:] if path.startswith("/api/") else path


def _under(path: str, prefix: str) -> bool:
    """True if `path` is `prefix` or inside it (whole address parts only)."""
    if prefix.endswith("/"):
        return path.startswith(prefix)
    return path == prefix or path.startswith(prefix + "/")


def area_for(path: str) -> str | None:
    """The area an address belongs to ("revenue"), or None. Longest match wins."""
    short = _short(path)
    best, best_len = None, -1
    for area in AREAS:
        for prefix in area["paths"]:
            if _under(short, prefix) and len(prefix) > best_len:
                best, best_len = area["key"], len(prefix)
    return best


def is_admin_path(path: str) -> bool:
    """True if the address belongs to the admin end."""
    short = _short(path)
    return any(_under(short, prefix) for prefix in ADMIN_PATHS)


def level_for(method: str) -> str:
    """Reading needs view; changing needs manage."""
    return VIEW if method.upper() in ("GET", "HEAD", "OPTIONS") else MANAGE


def clean_permissions(permissions) -> list[str]:
    """Only known permissions, each once; manage adds its view."""
    chosen = {p for p in (permissions or []) if p in ALL_PERMISSIONS}
    for p in list(chosen):
        if p.endswith(f".{MANAGE}"):
            chosen.add(p.replace(f".{MANAGE}", f".{VIEW}"))
    return [p for p in ALL_PERMISSIONS if p in chosen]


def has(permissions, area: str, level: str) -> bool:
    """True if the permissions allow `level` on `area` (manage includes view)."""
    perms = set(permissions or [])
    if f"{area}.{MANAGE}" in perms:
        return True
    return level == VIEW and f"{area}.{VIEW}" in perms


def is_owner(user, role=None) -> bool:
    """True for an Owner: an admin with no role (the original admin) or the Owner role."""
    if not getattr(user, "is_admin", False):
        return False
    if getattr(user, "admin_role_id", None) is None:
        return True
    return bool(role and role.is_system and role.name == OWNER_ROLE)


def access_of(db, user) -> dict:
    """What this admin may do: {role, role_id, is_owner, permissions}."""
    from database.pg_models import AdminRole
    # 1. Not an admin: nothing.
    if not getattr(user, "is_admin", False):
        return {"role": None, "role_id": None, "is_owner": False, "permissions": []}
    # 2. Their role (none = the original admin = Owner).
    role = db.get(AdminRole, user.admin_role_id) if getattr(user, "admin_role_id", None) else None
    if is_owner(user, role):
        return {"role": OWNER_ROLE, "role_id": role.id if role else None, "is_owner": True,
                "permissions": list(ALL_PERMISSIONS)}
    return {"role": role.name if role else None, "role_id": role.id if role else None, "is_owner": False,
            "permissions": clean_permissions(role.permissions if role else [])}


def denial(db, user, method: str, path: str) -> str | None:
    """Why this admin may NOT make this request, or None if they may."""
    # 1. Not an admin address, or not an admin: this check doesn't apply.
    if not is_admin_path(path) or not getattr(user, "is_admin", False):
        return None
    # 2. Their own account (password, who am I): always allowed.
    short = _short(path)
    if any(_under(short, p) for p in SELF_SERVICE_PATHS):
        return None
    # 3. Owners may do everything.
    access = access_of(db, user)
    if access["is_owner"]:
        return None
    # 4. Otherwise the area's view/manage permission decides; no area = Owner only.
    area, level = area_for(path), level_for(method)
    if area is None:
        return "Missing permission: only an Owner can use this."
    if has(access["permissions"], area, level):
        return None
    label = next(a["label"] for a in AREAS if a["key"] == area)
    action = "view" if level == VIEW else "make changes in"
    return f"Missing permission: your role ({access['role'] or 'no role'}) can't {action} {label}."


def check_request(authorization: str | None, cookie_token: str | None, method: str, path: str) -> str | None:
    """For the middleware: the denial message for this request, or None to let it through.
    Runs in a worker thread with its own database session. Never raises."""
    if method.upper() == "OPTIONS" or not is_admin_path(path):
        return None
    from api.routes.auth.login import get_current_user
    from database.pg_connections import SessionLocal

    db = SessionLocal()
    try:
        # 1. Who is asking (not logged in: the route itself answers 401).
        try:
            user = get_current_user(authorization, cookie_token, db)
        except Exception:
            return None
        # 2. Their role's answer.
        return denial(db, user, method, path)
    except Exception as e:
        # Fail closed for admins: if we can't tell, don't let a limited role through.
        logger.warning(f"[admin-access] couldn't check {method} {path}: {e}")
        return "Missing permission: access could not be checked, please try again."
    finally:
        db.close()


def ensure_default_roles(db) -> None:
    """Create the starting roles the first time (never changes existing ones)."""
    from database.pg_models import AdminRole
    existing = {name for (name,) in db.query(AdminRole.name).all()}
    added = False
    for spec in DEFAULT_ROLES:
        if spec["name"] in existing:
            continue
        db.add(AdminRole(name=spec["name"], description=spec["description"],
                         permissions=clean_permissions(spec["permissions"]), is_system=spec.get("is_system", False)))
        added = True
    if added:
        db.commit()
