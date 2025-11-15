
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.pg_connections import get_db
from db.pg_models import User
from api.routes.dependencies import admin_required

router = APIRouter(prefix="/admin", 
                   tags=["admin"])

@router.get("/dashboard")
def admin_dashboard(user=Depends(admin_required), db: Session = Depends(get_db)):
    """Admin dashboard endpoint."""
    return {"message": f"Welcome to the admin dashboard, {user.email}!"}
        