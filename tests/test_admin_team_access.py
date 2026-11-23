"""
Admin team access (api/services/admin_access.py) and the Team & Access page
(api/routes/admin/team.py): each admin has a role, the role decides which
admin areas they may view or change, and nobody can give themselves more
power than they have.
"""
import pytest
from fastapi import HTTPException

from api.routes.admin import team
from api.services import admin_access
from database.pg_models import AdminActivity, AdminRole, User


def _user(db, email, **fields):
    """A saved user (admin or not)."""
    user = User(name=email.split("@")[0].title(), email=email, password="x", confirm_password="x", **fields)
    db.add(user)
    db.flush()
    return user


def _role(db, name):
    """One of the starting roles."""
    admin_access.ensure_default_roles(db)
    return db.query(AdminRole).filter(AdminRole.name == name).one()


# ------------------------------------------------------------ the rules

def test_addresses_map_to_their_admin_area():
    assert admin_access.area_for("/api/control/revenue/stats") == "revenue"
    assert admin_access.area_for("/api/control/payout-tracker/commissions/3") == "payouts"
    assert admin_access.area_for("/api/admin/users/4/status") == "users"
    assert admin_access.area_for("/customer-service/admin/tickets") == "support"
    assert admin_access.area_for("/api/business/clarify/exam/run") == "micromodel"
    # The user's own clarify call is not an admin address at all.
    assert not admin_access.is_admin_path("/api/business/clarify")
    assert not admin_access.is_admin_path("/api/profile")
    # Whole address parts only: /control/teams is not /control/team.
    assert admin_access.area_for("/api/control/teams") is None


def test_manage_includes_view_and_unknown_permissions_are_dropped():
    assert admin_access.clean_permissions(["revenue.manage", "made.up"]) == ["revenue.view", "revenue.manage"]
    assert admin_access.has(["revenue.view"], "revenue", "view")
    assert not admin_access.has(["revenue.view"], "revenue", "manage")


def test_every_admin_route_belongs_to_an_area():
    """A new admin address must be added to AREAS, or only Owners can use it."""
    from api.main import app
    missing = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if admin_access.is_admin_path(path) and admin_access.area_for(path) is None \
                and not any(admin_access._under(admin_access._short(path), p) for p in admin_access.SELF_SERVICE_PATHS):
            missing.append(path)
    assert missing == []


def test_the_original_admin_is_an_owner_and_may_do_everything(db):
    boss = _user(db, "boss@team.test", is_admin=True)
    assert admin_access.access_of(db, boss)["is_owner"]
    assert admin_access.denial(db, boss, "POST", "/api/control/refunds/payments/ch_1/refund") is None
    assert admin_access.denial(db, boss, "POST", "/api/control/brand-new-thing") is None


def test_a_role_allows_only_its_areas(db):
    money = _user(db, "money@team.test", is_admin=True, admin_role_id=_role(db, "Finance").id)
    # 1. Finance manages revenue and refunds.
    assert admin_access.denial(db, money, "GET", "/api/control/revenue/stats") is None
    assert admin_access.denial(db, money, "POST", "/api/control/refunds/payments/ch_1/refund") is None
    # 2. Users is view-only for Finance.
    assert admin_access.denial(db, money, "GET", "/api/control/users") is None
    assert "can't make changes in Users" in admin_access.denial(db, money, "DELETE", "/api/control/users/5")
    # 3. Security and the team are closed.
    assert "can't view Security" in admin_access.denial(db, money, "GET", "/api/security/metrics")
    assert admin_access.denial(db, money, "GET", "/api/control/team/members").startswith("Missing permission")
    # 4. An admin address in no area is Owner-only.
    assert "only an Owner" in admin_access.denial(db, money, "GET", "/api/control/brand-new-thing")
    # 5. Their own account always works.
    assert admin_access.denial(db, money, "GET", "/api/control/team/me") is None
    assert admin_access.denial(db, money, "POST", "/api/control/account/password") is None


def test_ordinary_users_are_left_to_the_routes_own_checks(db):
    member = _user(db, "member@team.test")
    assert admin_access.denial(db, member, "GET", "/api/control/revenue/stats") is None


def test_a_refused_change_is_stamped_with_the_role(db, monkeypatch):
    from types import SimpleNamespace

    from api.routes.auth import login
    from api.services import admin_activity
    from database import pg_connections as connections
    helper = _user(db, "helper@team.test", is_admin=True, admin_role_id=_role(db, "Customer Support").id)
    monkeypatch.setattr(connections, "SessionLocal", lambda: SimpleNamespace(
        add=db.add, commit=db.flush, rollback=lambda: None, close=lambda: None, get=db.get, query=db.query))
    monkeypatch.setattr(login, "get_current_user", lambda a, c, s: helper)
    admin_activity.record("Bearer x", None, "POST", "/api/control/refunds/payments/ch_7/refund", "", 403, None)
    stamp = db.query(AdminActivity).filter(AdminActivity.admin_id == helper.id).one()
    assert stamp.admin_role == "Customer Support" and stamp.succeeded is False


# ------------------------------------------------------------ the team page

def test_adding_a_new_person_gives_a_temporary_password(db):
    boss = _user(db, "boss2@team.test", is_admin=True)
    added = team.add_member(team.AddMember(name="Dev One", email="Dev1@Team.test", title="Backend Developer",
                                           role_id=_role(db, "Developer").id), boss, db)
    assert added["temporary_password"] and len(added["temporary_password"]) >= 12
    dev = db.query(User).filter(User.email == "dev1@team.test").one()
    assert dev.is_admin and dev.admin_title == "Backend Developer"
    assert admin_access.access_of(db, dev)["role"] == "Developer"
    # The same person can't be added twice.
    with pytest.raises(HTTPException) as again:
        team.add_member(team.AddMember(name="Dev One", email="dev1@team.test", role_id=_role(db, "Developer").id), boss, db)
    assert again.value.status_code == 409


def test_an_existing_account_keeps_its_password(db):
    boss = _user(db, "boss3@team.test", is_admin=True)
    _user(db, "already@team.test")
    added = team.add_member(team.AddMember(name="x", email="already@team.test", role_id=_role(db, "Viewer").id), boss, db)
    assert added["temporary_password"] is None


def test_nobody_can_climb_above_their_own_access(db):
    boss = _user(db, "boss4@team.test", is_admin=True)
    lead = _user(db, "lead@team.test", is_admin=True, admin_role_id=_role(db, "Administrator").id)
    peer = _user(db, "peer@team.test", is_admin=True, admin_role_id=_role(db, "Viewer").id)
    owner_role = _role(db, "Owner")
    # 1. Only an Owner makes Owners.
    with pytest.raises(HTTPException) as e:
        team.change_member(peer.id, team.ChangeMember(role_id=owner_role.id), lead, db)
    assert e.value.status_code == 403
    # 2. A role can't include access the builder doesn't have (Administrator lacks team.manage).
    with pytest.raises(HTTPException) as e:
        team.create_role(team.RoleBody(name="Sneaky", permissions=["team.manage"]), lead, db)
    assert e.value.status_code == 403
    # 3. Nobody changes their own role, and only Owners change Owners.
    with pytest.raises(HTTPException):
        team.change_member(lead.id, team.ChangeMember(role_id=_role(db, "Viewer").id), lead, db)
    with pytest.raises(HTTPException) as e:
        team.remove_member(boss.id, lead, db)
    assert e.value.status_code == 403


def test_the_last_owner_stays(db):
    # Make this test's owner the only one (others may exist from earlier tests in the session).
    db.query(User).filter(User.is_admin.is_(True)).update({"is_admin": False})
    boss = _user(db, "boss5@team.test", is_admin=True)
    second = _user(db, "second@team.test", is_admin=True, admin_role_id=_role(db, "Owner").id)
    # Two Owners: one may step the other down.
    team.change_member(second.id, team.ChangeMember(role_id=_role(db, "Viewer").id), boss, db)
    # Now boss is the last Owner: the Viewer can't remove them, and nor can anyone demote them.
    with pytest.raises(HTTPException):
        team.remove_member(boss.id, second, db)
    assert admin_access.access_of(db, boss)["is_owner"]


def test_removing_a_member_takes_access_away_at_once(db):
    boss = _user(db, "boss6@team.test", is_admin=True)
    gone = _user(db, "gone@team.test", is_admin=True, admin_role_id=_role(db, "Finance").id, admin_title="Accountant")
    team.remove_member(gone.id, boss, db)
    assert not gone.is_admin and gone.admin_role_id is None and gone.admin_title is None
    # Not an admin any more: the route's own admin check now turns them away.
    with pytest.raises(HTTPException):
        from api.routes.dependencies import admin_required
        admin_required(gone, db)


def test_roles_can_be_built_edited_and_deleted(db):
    boss = _user(db, "boss7@team.test", is_admin=True)
    made = team.create_role(team.RoleBody(name="Growth", description="Ads and content",
                                          permissions=["content.manage", "dashboard.view"]), boss, db)["data"]
    assert made["permissions"] == ["dashboard.view", "content.view", "content.manage"]
    # A duplicate name is refused.
    with pytest.raises(HTTPException) as e:
        team.create_role(team.RoleBody(name="growth"), boss, db)
    assert e.value.status_code == 409
    # A role somebody has can't be deleted; once nobody has it, it can.
    person = _user(db, "grower@team.test", is_admin=True, admin_role_id=made["id"])
    with pytest.raises(HTTPException):
        team.delete_role(made["id"], boss, db)
    person.admin_role_id = _role(db, "Viewer").id
    db.flush()
    team.delete_role(made["id"], boss, db)
    # The Owner role is fixed.
    with pytest.raises(HTTPException):
        team.change_role(_role(db, "Owner").id, team.RoleBody(name="Owner", permissions=[]), boss, db)


def test_me_reports_the_role_and_its_permissions(db):
    money = _user(db, "money2@team.test", is_admin=True, admin_role_id=_role(db, "Finance").id, admin_title="CFO")
    me = team.who_am_i(money, db)["data"]
    assert me["role"] == "Finance" and me["title"] == "CFO" and not me["is_owner"]
    assert "revenue.manage" in me["permissions"] and "security.view" not in me["permissions"]
