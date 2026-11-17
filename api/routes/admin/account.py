"""
Admin account: an admin changes their own password from the admin panel.

  POST /api/control/account/password   {current_password, new_password, confirm_password}

The same rules as the password reset (api/routes/auth/forgot_password.py):
at least 8 characters, typed twice the same. The current password must be
right. Both stored hashes (password and confirm_password) are updated, as the
reset does. The change is stamped in the admin Activity log by the
middleware (api/services/admin_activity.py); the passwords themselves are
never logged.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.routes.auth.login import pwd_context
from api.routes.dependencies import admin_required
from database.pg_connections import get_db

router = APIRouter(prefix="/control/account", tags=["admin-account"])


class ChangeOwnPassword(BaseModel):
    """What the admin types in the Change password box."""
    current_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=8, max_length=200)
    confirm_password: str = Field(..., min_length=8, max_length=200)


@router.post("/password")
def change_own_password(body: ChangeOwnPassword, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Change the logged-in admin's password."""
    # 1. The new password, typed twice the same.
    if body.new_password != body.confirm_password:
        raise HTTPException(status_code=400, detail="The two new passwords don't match")
    # 2. The current password must be right (400, not 401, so the admin stays logged in).
    if not admin.password or not pwd_context.verify(body.current_password, admin.password):
        raise HTTPException(status_code=400, detail="Your current password is wrong")
    # 3. It must actually change.
    if pwd_context.verify(body.new_password, admin.password):
        raise HTTPException(status_code=400, detail="The new password is the same as the current one")
    # 4. Save it (both hashes, as the password reset does).
    hashed = pwd_context.hash(body.new_password)
    admin.password = hashed
    admin.confirm_password = hashed
    db.commit()
    return {"success": True, "message": "Password changed. Use the new one next time you sign in."}
