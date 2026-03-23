"""
Marketplace — tools listing, purchase requests, admin management.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.pg_connections import get_db
from database.pg_models import User, MarketplaceTool, MarketplacePurchase, MarketplaceRequest
from api.routes.auth.login import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# ─── Pydantic models ─────────────────────────────────────────────────────────

class ToolCreate(BaseModel):
    name: str
    author: str
    description: str
    full_description: Optional[str] = None
    category: str = "AI Tools"
    price: float = 0.0
    tags: Optional[list] = None
    features: Optional[list] = None
    icon_name: str = "Cpu"
    color_theme: str = "orange"
    purchase_url: Optional[str] = None


class ToolUpdate(BaseModel):
    name: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    full_description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    tags: Optional[list] = None
    features: Optional[list] = None
    icon_name: Optional[str] = None
    color_theme: Optional[str] = None
    is_active: Optional[bool] = None
    purchase_url: Optional[str] = None


class PurchaseRequest(BaseModel):
    tool_id: int


class CustomRequest(BaseModel):
    title: str
    description: str
    budget: Optional[str] = None
    timeline: Optional[str] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _tool_dict(tool: MarketplaceTool) -> dict:
    return {
        "id": tool.id,
        "name": tool.name,
        "author": tool.author,
        "description": tool.description,
        "full_description": tool.full_description,
        "category": tool.category,
        "price": tool.price,
        "tags": tool.tags or [],
        "features": tool.features or [],
        "icon_name": tool.icon_name,
        "color_theme": tool.color_theme,
        "sales_count": tool.sales_count,
        "rating": tool.rating,
        "review_count": tool.review_count,
        "is_active": tool.is_active,
        "purchase_url": tool.purchase_url,
        "created_at": tool.created_at.isoformat() if tool.created_at else None,
    }


def _require_admin(current_user: User):
    if not getattr(current_user, "is_admin", False) and getattr(current_user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# ─── User endpoints ───────────────────────────────────────────────────────────

@router.get("/tools")
async def list_tools(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active marketplace tools with optional filters."""
    q = db.query(MarketplaceTool).filter(MarketplaceTool.is_active == True)
    if category and category != "All":
        q = q.filter(MarketplaceTool.category == category)
    if search:
        like = f"%{search}%"
        q = q.filter(
            MarketplaceTool.name.ilike(like) |
            MarketplaceTool.description.ilike(like)
        )
    tools = q.order_by(MarketplaceTool.sales_count.desc()).limit(limit).all()

    # Compute stats
    total_tools = db.query(func.count(MarketplaceTool.id)).filter(MarketplaceTool.is_active == True).scalar() or 0
    total_sales = db.query(func.sum(MarketplaceTool.sales_count)).filter(MarketplaceTool.is_active == True).scalar() or 0
    avg_rating = db.query(func.avg(MarketplaceTool.rating)).filter(MarketplaceTool.is_active == True, MarketplaceTool.rating > 0).scalar() or 0

    return {
        "tools": [_tool_dict(t) for t in tools],
        "stats": {
            "active_listings": total_tools,
            "total_sales_volume": 0,  # could sum price*sales if needed
            "total_transactions": int(total_sales),
            "avg_rating": round(float(avg_rating), 1),
        }
    }


@router.get("/tools/{tool_id}")
async def get_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tool = db.query(MarketplaceTool).filter(MarketplaceTool.id == tool_id, MarketplaceTool.is_active == True).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return _tool_dict(tool)


@router.post("/tools/{tool_id}/purchase")
async def request_purchase(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a purchase intent. For paid tools this creates a pending record."""
    tool = db.query(MarketplaceTool).filter(MarketplaceTool.id == tool_id, MarketplaceTool.is_active == True).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    existing = db.query(MarketplacePurchase).filter_by(user_id=current_user.id, tool_id=tool_id).first()
    if existing:
        return {"status": existing.status, "message": "Already purchased/requested"}

    purchase = MarketplacePurchase(
        user_id=current_user.id,
        tool_id=tool_id,
        status="completed" if tool.price == 0 else "pending",
        amount_paid=tool.price,
    )
    db.add(purchase)
    # Bump sales count
    tool.sales_count = (tool.sales_count or 0) + 1
    db.commit()

    return {
        "status": purchase.status,
        "message": "Access granted" if tool.price == 0 else "Purchase request submitted. Our team will reach out.",
        "purchase_url": tool.purchase_url,
    }


@router.post("/requests")
async def submit_custom_request(
    body: CustomRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a custom tool development request."""
    req = MarketplaceRequest(
        user_id=current_user.id,
        title=body.title,
        description=body.description,
        budget=body.budget,
        timeline=body.timeline,
    )
    db.add(req)
    db.commit()
    return {"status": "submitted", "id": req.id, "message": "Your request has been submitted. We'll get back to you within 48 hours."}


# ─── Admin endpoints ──────────────────────────────────────────────────────────

@router.get("/admin/tools")
async def admin_list_tools(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    q = db.query(MarketplaceTool)
    if not include_inactive:
        q = q.filter(MarketplaceTool.is_active == True)
    tools = q.order_by(MarketplaceTool.created_at.desc()).all()
    return {"tools": [_tool_dict(t) for t in tools], "total": len(tools)}


@router.post("/admin/tools")
async def admin_create_tool(
    body: ToolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    tool = MarketplaceTool(
        name=body.name,
        author=body.author,
        description=body.description,
        full_description=body.full_description,
        category=body.category,
        price=body.price,
        tags=body.tags or [],
        features=body.features or [],
        icon_name=body.icon_name,
        color_theme=body.color_theme,
        purchase_url=body.purchase_url,
        created_by=current_user.id,
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    logger.info(f"Admin {current_user.id} created marketplace tool {tool.id}: {tool.name}")
    return _tool_dict(tool)


@router.put("/admin/tools/{tool_id}")
async def admin_update_tool(
    tool_id: int,
    body: ToolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    tool = db.query(MarketplaceTool).filter(MarketplaceTool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    for field, value in body.dict(exclude_unset=True).items():
        setattr(tool, field, value)
    db.commit()
    db.refresh(tool)
    return _tool_dict(tool)


@router.delete("/admin/tools/{tool_id}")
async def admin_delete_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    tool = db.query(MarketplaceTool).filter(MarketplaceTool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    tool.is_active = False  # soft delete
    db.commit()
    return {"status": "deleted"}


@router.get("/admin/requests")
async def admin_list_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    q = db.query(MarketplaceRequest)
    if status:
        q = q.filter(MarketplaceRequest.status == status)
    requests = q.order_by(MarketplaceRequest.created_at.desc()).all()
    result = []
    for r in requests:
        user = db.query(User).filter(User.id == r.user_id).first()
        result.append({
            "id": r.id, "title": r.title, "description": r.description,
            "budget": r.budget, "timeline": r.timeline, "status": r.status,
            "user_name": user.name if user else "Unknown",
            "user_email": user.email if user else "",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return {"requests": result, "total": len(result)}


@router.patch("/admin/requests/{request_id}/status")
async def admin_update_request_status(
    request_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    req = db.query(MarketplaceRequest).filter(MarketplaceRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = body.get("status", req.status)
    db.commit()
    return {"status": "updated", "new_status": req.status}
