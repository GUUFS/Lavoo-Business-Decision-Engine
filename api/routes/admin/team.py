"""
Team & Access page: the company's admin team, their roles, and what each
role may see and change in the admin panel (rules in api/services/admin_access.py).

  GET    /api/control/team/me                          who I am and what I may do (any admin)
  GET    /api/control/team/catalog                     the admin areas a role can be given
  GET    /api/control/team/members                     everyone on the admin team
  POST   /api/control/team/members                     add someone {name, email, title, role_id}
  PATCH  /api/control/team/members/{id}                change their title and/or role
  POST   /api/control/team/members/{id}/reset-password give them a new temporary password
  DELETE /api/control/team/members/{id}                take away their admin access
  GET    /api/control/team/roles                       the roles, with how many people have each
  POST   /api/control/team/roles                       create a role {name, description, permissions}
  PATCH  /api/control/team/roles/{id}                  change a role
  DELETE /api/control/team/roles/{id}                  delete a role nobody has

Reading needs "team.view" and changing needs "team.manage" (checked by the
middleware). On top of that, to stop anyone giving themselves more power:
  - only an Owner can make someone an Owner or change an Owner;
  - you can only hand out roles, and build roles, within your own access;
  - you can't change your own role or remove yourself;
  - the last Owner can't be removed or demoted.
Every change is stamped in Admin Activity (api/services/admin_activity.py).
"""
import html
import logging
import os
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from api.routes.auth.login import pwd_context
from api.routes.dependencies import admin_required
from api.services import admin_access
from api.services.admin_access import OWNER_ROLE
from database.pg_connections import get_db
from database.pg_models import AdminActivity, AdminRole, User

router = APIRouter(prefix="/control/team", tags=["admin-team"])
logger = logging.getLogger(__name__)

# Where team members sign in (the admin panel). Set ADMIN_PANEL_URL to change it.
ADMIN_PANEL_URL = os.getenv("ADMIN_PANEL_URL", "https://control.lavooai.com")


class AddMember(BaseModel):
    """Someone joining the admin team."""
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    title: str | None = Field(None, max_length=120)
    role_id: int


class ChangeMember(BaseModel):
    """A new title and/or role for a team member (leave out what doesn't change)."""
    title: str | None = Field(None, max_length=120)
    role_id: int | None = None


class RoleBody(BaseModel):
    """A role's name, what it is for, and its permissions ("revenue.view", "users.manage")."""
    name: str = Field(..., min_length=1, max_length=80)
    description: str | None = Field(None, max_length=300)
    permissions: list[str] = []


# ---------------------------------------------------------------- helpers

def _temporary_password() -> str:
    """A random 12-character password to share once with a new team member."""
    return secrets.token_urlsafe(9)


def send_team_email(email: str, name: str, role_name: str, title: str | None,
                    temporary_password: str | None, invited_by: str, reset: bool = False) -> None:
    """Email a team member that they were added to the admin team (or that
    their password was reset): where to sign in, their role, and their
    temporary password if they have one. Runs after the response; never raises."""
    try:
        from emailing.email_service import email_service
        # 1. The words, for an invitation or a password reset.
        role_text = f"{role_name} ({title})" if title else role_name
        if reset:
            subject = "Your Lavoo admin password was reset"
            intro = f"{invited_by} gave you a new temporary password for the Lavoo admin panel."
        else:
            subject = f"You've been added to the Lavoo admin team as {role_name}"
            intro = f"{invited_by} added you to the Lavoo admin team. Your role: {role_text}."
        if temporary_password:
            login = (f"Sign in with this email and the temporary password {temporary_password} , "
                     "then change it with Change password at the bottom of the admin menu.")
        else:
            login = "Sign in with this email and your usual Lavoo password."
        text = f"Hi {name},\n\n{intro}\n\nSign in at {ADMIN_PANEL_URL}\n{login}\n"
        # 2. The same in HTML (every value escaped).
        password_html = (f'<p>Temporary password: <strong style="font-family:monospace;font-size:16px">'
                         f'{html.escape(temporary_password)}</strong><br>After you sign in, change it with Change password at the bottom of the admin menu.</p>'
                         if temporary_password else "<p>Sign in with this email and your usual Lavoo password.</p>")
        body_html = (
            '<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#333;line-height:1.6">'
            '<div style="background:#18181b;border-bottom:3px solid #e87a02;color:#fff;padding:24px;border-radius:10px 10px 0 0">'
            f'<h2 style="margin:0">{html.escape(subject)}</h2></div>'
            '<div style="background:#f9f9f9;padding:24px;border-radius:0 0 10px 10px">'
            f'<p>Hi {html.escape(name)},</p><p>{html.escape(intro)}</p>'
            f'<p>Email: <strong>{html.escape(email)}</strong></p>{password_html}'
            f'<p><a href="{html.escape(ADMIN_PANEL_URL)}" style="display:inline-block;padding:12px 28px;background:#e87a02;'
            'color:#fff;text-decoration:none;border-radius:5px">Open the admin panel</a></p>'
            '<p style="font-size:12px;color:#666">If you weren\'t expecting this, tell the person who added you.</p>'
            '</div></div>')
        # 3. Send it.
        email_service._send_email(to_email=email, to_name=name, subject=subject,
                                  html_content=body_html, text_content=text)
    except Exception as exc:
        logger.error(f"[team] email to new team member not sent: {exc}")


def _owner_role(db: Session) -> AdminRole:
    """The Owner role (created with the other starting roles if missing)."""
    admin_access.ensure_default_roles(db)
    return db.query(AdminRole).filter(AdminRole.name == OWNER_ROLE, AdminRole.is_system.is_(True)).first()


def _owners_query(db: Session):
    """All Owners: admins with no role (the original admin) or the Owner role."""
    owner = _owner_role(db)
    return db.query(User).filter(User.is_admin.is_(True),
                                 or_(User.admin_role_id.is_(None), User.admin_role_id == owner.id))


def _role_or_404(db: Session, role_id: int) -> AdminRole:
    """The role, or 404."""
    role = db.get(AdminRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


def _member_or_404(db: Session, user_id: int) -> User:
    """A team member (an admin), or 404."""
    user = db.get(User, user_id)
    if not user or not user.is_admin:
        raise HTTPException(status_code=404, detail="Team member not found")
    return user


def _within_my_access(caller_access: dict, permissions) -> bool:
    """True if every permission is one the caller has themselves."""
    return caller_access["is_owner"] or set(permissions) <= set(caller_access["permissions"])


def _may_hand_out(db: Session, caller, role: AdminRole) -> None:
    """Stop a caller handing out a role above their own access (403)."""
    mine = admin_access.access_of(db, caller)
    if role.is_system and role.name == OWNER_ROLE and not mine["is_owner"]:
        raise HTTPException(status_code=403, detail="Only an Owner can make someone an Owner.")
    if not _within_my_access(mine, admin_access.clean_permissions(role.permissions)):
        raise HTTPException(status_code=403, detail="You can only give roles within your own access.")


def _may_change(db: Session, caller, target: User) -> None:
    """Stop a caller changing themselves or (unless an Owner) an Owner (400/403)."""
    if target.id == caller.id:
        raise HTTPException(status_code=400, detail="You can't change your own access. Ask another Owner.")
    if admin_access.access_of(db, target)["is_owner"] and not admin_access.access_of(db, caller)["is_owner"]:
        raise HTTPException(status_code=403, detail="Only an Owner can change an Owner.")


def _keep_one_owner(db: Session, target: User) -> None:
    """Stop the last Owner being removed or demoted (400)."""
    if admin_access.access_of(db, target)["is_owner"] and _owners_query(db).count() <= 1:
        raise HTTPException(status_code=400, detail="This is the last Owner. Make someone else an Owner first.")


def _member_view(db: Session, user: User, last_action) -> dict:
    """One team member for the page."""
    access = admin_access.access_of(db, user)
    return {"id": user.id, "name": user.name, "email": user.email, "title": user.admin_title,
            "role": access["role"], "role_id": access["role_id"], "is_owner": access["is_owner"],
            "is_active": bool(user.is_active),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "last_action": last_action.isoformat() if last_action else None}


def _role_view(role: AdminRole, members: int) -> dict:
    """One role for the page."""
    owner = role.is_system and role.name == OWNER_ROLE
    return {"id": role.id, "name": role.name, "description": role.description,
            "permissions": admin_access.ALL_PERMISSIONS if owner else admin_access.clean_permissions(role.permissions),
            "is_system": bool(role.is_system), "members": members}


# ---------------------------------------------------------------- me and catalog

@router.get("/me")
def who_am_i(admin=Depends(admin_required), db: Session = Depends(get_db)):
    """The signed-in admin and what they may do (the panel shows only those areas)."""
    access = admin_access.access_of(db, admin)
    return {"success": True, "data": {"id": admin.id, "name": admin.name, "email": admin.email,
                                      "title": admin.admin_title, **access}}


@router.get("/catalog")
def catalog(admin=Depends(admin_required)):
    """The admin areas, grouped as in the sidebar, for building a role."""
    areas = [{k: a[k] for k in ("key", "label", "group", "description")} for a in admin_access.AREAS]
    return {"success": True, "data": areas}


# ---------------------------------------------------------------- members

@router.get("/members")
def list_members(admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Everyone on the admin team, Owners first, with when they last did something."""
    # 1. Each admin's latest action in the Activity log.
    last_actions = dict(db.query(AdminActivity.admin_id, func.max(AdminActivity.created_at))
                        .group_by(AdminActivity.admin_id).all())
    # 2. The team.
    members = [_member_view(db, u, last_actions.get(u.id))
               for u in db.query(User).filter(User.is_admin.is_(True)).order_by(User.name).all()]
    members.sort(key=lambda m: (not m["is_owner"], (m["role"] or "").lower(), (m["name"] or "").lower()))
    return {"success": True, "data": members}


@router.post("/members")
def add_member(body: AddMember, admin=Depends(admin_required), db: Session = Depends(get_db),
               background_tasks: BackgroundTasks = None):
    """Add someone to the team. A new person gets an account and a temporary
    password (shown once, and emailed to them); an existing Lavoo account
    keeps its own password. Either way they get an email saying where to sign in."""
    # 1. The role, which the caller must be allowed to hand out.
    role = _role_or_404(db, body.role_id)
    _may_hand_out(db, admin, role)
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    # 2. An existing account: give it admin access (unless it already has it).
    user = db.query(User).filter(func.lower(User.email) == email).first()
    temporary_password = None
    if user:
        if user.is_admin:
            raise HTTPException(status_code=409, detail=f"{user.name} is already on the team.")
        user.is_admin = True
    # 3. A new person: a new account with a temporary password.
    else:
        temporary_password = _temporary_password()
        hashed = pwd_context.hash(temporary_password)
        user = User(name=body.name.strip(), email=email, password=hashed, confirm_password=hashed, is_admin=True)
        db.add(user)
    # 4. Their role and job title.
    user.admin_role_id = role.id
    user.admin_title = (body.title or "").strip() or None
    db.commit()
    db.refresh(user)
    # 5. Email them where to sign in (after the response, so the page isn't kept waiting).
    if background_tasks is not None:
        background_tasks.add_task(send_team_email, user.email, user.name, role.name, user.admin_title,
                                  temporary_password, admin.name or "An admin")
    return {"success": True, "data": _member_view(db, user, None), "temporary_password": temporary_password,
            "message": f"{user.name} joined the team as {role.name}. We emailed them how to sign in."}


@router.patch("/members/{user_id}")
def change_member(user_id: int, body: ChangeMember, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Change a team member's job title and/or role."""
    target = _member_or_404(db, user_id)
    # 1. A new role: allowed for the caller, and never leaving the team without an Owner.
    if body.role_id is not None and body.role_id != target.admin_role_id:
        _may_change(db, admin, target)
        role = _role_or_404(db, body.role_id)
        _may_hand_out(db, admin, role)
        if not (role.is_system and role.name == OWNER_ROLE):
            _keep_one_owner(db, target)
        target.admin_role_id = role.id
    # 2. A new title (anyone with team.manage may fix a title, even an Owner's).
    if body.title is not None:
        target.admin_title = body.title.strip() or None
    db.commit()
    return {"success": True, "data": _member_view(db, target, None)}


@router.post("/members/{user_id}/reset-password")
def reset_member_password(user_id: int, admin=Depends(admin_required), db: Session = Depends(get_db),
                          background_tasks: BackgroundTasks = None):
    """Give a team member a new temporary password (shown once, and emailed
    to them). For yourself, use Change password instead."""
    target = _member_or_404(db, user_id)
    _may_change(db, admin, target)
    temporary_password = _temporary_password()
    hashed = pwd_context.hash(temporary_password)
    target.password = hashed
    target.confirm_password = hashed
    db.commit()
    # Email it to them too (after the response).
    if background_tasks is not None:
        role = db.get(AdminRole, target.admin_role_id) if target.admin_role_id else None
        background_tasks.add_task(send_team_email, target.email, target.name, role.name if role else OWNER_ROLE,
                                  target.admin_title, temporary_password, admin.name or "An admin", True)
    return {"success": True, "temporary_password": temporary_password,
            "message": f"New temporary password for {target.name}, also emailed to them. They should change it after signing in."}


@router.delete("/members/{user_id}")
def remove_member(user_id: int, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Take away someone's admin access. Their Lavoo account stays; they just
    can't use the admin panel any more (from their very next request)."""
    target = _member_or_404(db, user_id)
    _may_change(db, admin, target)
    _keep_one_owner(db, target)
    target.is_admin = False
    target.admin_role_id = None
    target.admin_title = None
    db.commit()
    return {"success": True, "message": f"{target.name} no longer has admin access."}


# ---------------------------------------------------------------- roles

@router.get("/roles")
def list_roles(admin=Depends(admin_required), db: Session = Depends(get_db)):
    """The roles (Owner first), with how many team members have each."""
    owner = _owner_role(db)
    counts = dict(db.query(User.admin_role_id, func.count(User.id))
                  .filter(User.is_admin.is_(True)).group_by(User.admin_role_id).all())
    # Admins with no role are Owners too.
    counts[owner.id] = counts.get(owner.id, 0) + counts.pop(None, 0)
    roles = db.query(AdminRole).order_by(AdminRole.is_system.desc(), AdminRole.name).all()
    return {"success": True, "data": [_role_view(r, counts.get(r.id, 0)) for r in roles]}


def _check_role_body(db: Session, admin, body: RoleBody, role_id: int | None = None) -> tuple[str, list[str]]:
    """A clean name (unique) and permissions within the caller's own access."""
    name = body.name.strip()
    clash = db.query(AdminRole).filter(func.lower(AdminRole.name) == name.lower())
    if role_id is not None:
        clash = clash.filter(AdminRole.id != role_id)
    if clash.first():
        raise HTTPException(status_code=409, detail=f"A role called {name} already exists.")
    permissions = admin_access.clean_permissions(body.permissions)
    if not _within_my_access(admin_access.access_of(db, admin), permissions):
        raise HTTPException(status_code=403, detail="A role can only include access you have yourself.")
    return name, permissions


@router.post("/roles")
def create_role(body: RoleBody, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Create a role."""
    admin_access.ensure_default_roles(db)
    name, permissions = _check_role_body(db, admin, body)
    role = AdminRole(name=name, description=(body.description or "").strip() or None, permissions=permissions)
    db.add(role)
    db.commit()
    db.refresh(role)
    return {"success": True, "data": _role_view(role, 0), "message": f"Role {name} created."}


@router.patch("/roles/{role_id}")
def change_role(role_id: int, body: RoleBody, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Change a role's name, description and permissions. Takes effect for
    everyone with the role on their next request. The Owner role is fixed."""
    role = _role_or_404(db, role_id)
    if role.is_system:
        raise HTTPException(status_code=400, detail="The Owner role always has full access and can't be changed.")
    # Your own role: changing it could lock you out of this page.
    if admin.admin_role_id == role.id:
        raise HTTPException(status_code=400, detail="You can't change your own role. Ask another Owner.")
    name, permissions = _check_role_body(db, admin, body, role_id)
    role.name = name
    role.description = (body.description or "").strip() or None
    role.permissions = permissions
    db.commit()
    members = db.query(User).filter(User.is_admin.is_(True), User.admin_role_id == role.id).count()
    return {"success": True, "data": _role_view(role, members), "message": f"Role {name} saved."}


@router.delete("/roles/{role_id}")
def delete_role(role_id: int, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Delete a role nobody has (move its members to another role first)."""
    role = _role_or_404(db, role_id)
    if role.is_system:
        raise HTTPException(status_code=400, detail="The Owner role can't be deleted.")
    holders = db.query(User).filter(User.admin_role_id == role.id).count()
    if holders:
        raise HTTPException(status_code=400, detail=f"{holders} team member(s) have this role. Give them another role first.")
    db.delete(role)
    db.commit()
    return {"success": True, "message": f"Role {role.name} deleted."}
