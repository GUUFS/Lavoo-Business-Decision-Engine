"""
Community Feature — Channels, Discussions, Events, Leaderboard, Saved Items
"""
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.pg_connections import get_db
from database.pg_models import (
    User,
    CommunityChannel, ChannelMember,
    CommunityDiscussion, DiscussionReply, DiscussionLike,
    CommunityEvent, EventRegistration,
    CommunityActivity, SavedItem,
)
from api.routes.auth.login import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/community", tags=["community"])

# ─── Default seed channels ──────────────────────────────────────────────────

DEFAULT_CHANNELS = [
    {"name": "Business Strategy", "slug": "business-strategy", "description": "Discuss strategic planning, growth, and competitive positioning.", "category": "Strategy", "icon": "📊"},
    {"name": "AI & Technology", "slug": "ai-technology", "description": "Explore AI tools, automation, and emerging tech for business.", "category": "Technology", "icon": "🤖"},
    {"name": "Marketing & Growth", "slug": "marketing-growth", "description": "Share marketing tips, growth hacks, and customer acquisition strategies.", "category": "Marketing", "icon": "📣"},
    {"name": "Finance & Revenue", "slug": "finance-revenue", "description": "Revenue models, pricing, fundraising, and financial management.", "category": "Finance", "icon": "💰"},
    {"name": "Operations", "slug": "operations", "description": "Streamline processes, manage teams, and optimize day-to-day operations.", "category": "Operations", "icon": "⚙️"},
    {"name": "Community", "slug": "community", "description": "General discussions, introductions, and community updates.", "category": "General", "icon": "🌍"},
]


def _seed_channels(db: Session):
    """Seed default channels if the table is empty."""
    count = db.query(CommunityChannel).count()
    if count == 0:
        for ch in DEFAULT_CHANNELS:
            db.add(CommunityChannel(**ch))
        db.commit()
        logger.info("Seeded default community channels")


def _log_activity(db: Session, user_id: int, action_type: str, target_id: Optional[int] = None, target_type: Optional[str] = None, target_name: Optional[str] = None):
    try:
        db.add(CommunityActivity(user_id=user_id, action_type=action_type, target_id=target_id, target_type=target_type, target_name=target_name))
        db.commit()
    except Exception:
        db.rollback()


def _channel_dict(ch: CommunityChannel, user_id: Optional[int] = None, db: Optional[Session] = None) -> dict:
    is_member = False
    if user_id and db:
        is_member = db.query(ChannelMember).filter_by(user_id=user_id, channel_id=ch.id).first() is not None
    return {
        "id": ch.id, "name": ch.name, "slug": ch.slug, "description": ch.description,
        "category": ch.category, "member_count": ch.member_count,
        # Frontend aliases
        "members": ch.member_count,
        "active": True,
        "isJoined": is_member,
        "color": None,
        "post_count": ch.post_count,
        "icon": ch.icon, "is_public": ch.is_public, "is_member": is_member,
        "created_at": ch.created_at.isoformat() if ch.created_at else None,
    }


def _discussion_dict(d: CommunityDiscussion, user_id: Optional[int] = None, db: Optional[Session] = None) -> dict:
    has_liked = False
    if user_id and db:
        has_liked = db.query(DiscussionLike).filter_by(user_id=user_id, discussion_id=d.id).first() is not None
    return {
        "id": d.id, "channel_id": d.channel_id, "title": d.title, "content": d.content,
        "tags": d.tags or [], "like_count": d.like_count, "reply_count": d.reply_count,
        # Frontend aliases
        "likes": d.like_count, "replies": d.reply_count,
        "pinned": d.is_pinned, "hot": False,
        "view_count": d.view_count, "is_pinned": d.is_pinned, "has_liked": has_liked,
        "liked_by_user": has_liked,
        "author": {"id": d.user.id, "name": d.user.name} if d.user else None,
        "channel": {"id": d.channel.id, "name": d.channel.name, "slug": d.channel.slug} if d.channel else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


def _event_dict(ev: CommunityEvent, user_id: Optional[int] = None, db: Optional[Session] = None) -> dict:
    is_registered = False
    if user_id and db:
        is_registered = db.query(EventRegistration).filter_by(user_id=user_id, event_id=ev.id).first() is not None
    # Format scheduled_at for frontend display
    formatted_date = None
    formatted_time = None
    if ev.scheduled_at:
        formatted_date = ev.scheduled_at.strftime("%b %d, %Y")  # e.g. "Feb 27, 2026"
        formatted_time = ev.scheduled_at.strftime("%I:%M %p")    # e.g. "12:00 PM"
    # Map event_type to frontend type (Live/Workshop/Webinar)
    type_map = {"live": "Live", "workshop": "Workshop", "webinar": "Webinar"}
    frontend_type = type_map.get((ev.event_type or "").lower(), ev.event_type or "Live")
    return {
        "id": ev.id, "title": ev.title, "description": ev.description,
        "event_type": ev.event_type,
        # Frontend aliases
        "type": frontend_type,
        "date": formatted_date,
        "time": formatted_time,
        "attendees": ev.attendee_count,
        "registered": is_registered,
        "scheduled_at": ev.scheduled_at.isoformat() if ev.scheduled_at else None,
        "duration_minutes": ev.duration_minutes, "max_attendees": ev.max_attendees,
        "attendee_count": ev.attendee_count, "host_name": ev.host_name,
        "meeting_link": ev.meeting_link, "is_registered": is_registered,
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }


# ─── Pydantic Models ────────────────────────────────────────────────────────

class CreateDiscussionRequest(BaseModel):
    title: str
    content: str
    channel_id: int
    tags: Optional[List[str]] = None


class CreateReplyRequest(BaseModel):
    content: str


class SaveItemRequest(BaseModel):
    item_id: int
    item_type: str


# ─── Stats ──────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_community_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        total_channels = db.query(CommunityChannel).count()
        total_discussions = db.query(CommunityDiscussion).count()
        total_events = db.query(CommunityEvent).filter_by(is_published=True).count()
        total_members = db.query(User).count()
        user_channels = db.query(ChannelMember).filter_by(user_id=current_user.id).count()

        return {"success": True, "data": {
            "total_channels": total_channels,
            "total_discussions": total_discussions,
            "total_events": total_events,
            "total_members": total_members,
            "my_channels": user_channels,
        }}
    except Exception as e:
        logger.error(f"Community stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch community stats")


# ─── Channels ───────────────────────────────────────────────────────────────

@router.get("/channels/my")
async def get_my_channels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        memberships = db.query(ChannelMember).filter_by(user_id=current_user.id).all()
        channels = [_channel_dict(m.channel, current_user.id, db) for m in memberships if m.channel]
        return {"success": True, "data": channels}
    except Exception as e:
        logger.error(f"Get my channels error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch your channels")


@router.get("/channels/{channel_name}")
async def get_channel_by_name(
    channel_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ch = db.query(CommunityChannel).filter_by(slug=channel_name).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"success": True, "data": _channel_dict(ch, current_user.id, db)}


@router.get("/channels")
async def get_channels(
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        _seed_channels(db)
        q = db.query(CommunityChannel).filter_by(is_public=True)
        if category and category.lower() != "all":
            q = q.filter(CommunityChannel.category == category)
        channels = q.order_by(CommunityChannel.member_count.desc()).all()
        return {"success": True, "data": [_channel_dict(ch, current_user.id, db) for ch in channels]}
    except Exception as e:
        logger.error(f"Get channels error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch channels")


@router.post("/channels/{channel_id}/join")
async def join_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ch = db.query(CommunityChannel).filter_by(id=channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    existing = db.query(ChannelMember).filter_by(user_id=current_user.id, channel_id=channel_id).first()
    if existing:
        return {"success": True, "message": "Already a member"}

    db.add(ChannelMember(user_id=current_user.id, channel_id=channel_id))
    ch.member_count = (ch.member_count or 0) + 1
    db.commit()
    _log_activity(db, current_user.id, "joined_channel", channel_id, "channel", ch.name)
    return {"success": True, "message": f"Joined {ch.name}"}


@router.post("/channels/{channel_id}/leave")
async def leave_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    membership = db.query(ChannelMember).filter_by(user_id=current_user.id, channel_id=channel_id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Not a member")

    ch = db.query(CommunityChannel).filter_by(id=channel_id).first()
    db.delete(membership)
    if ch and ch.member_count > 0:
        ch.member_count -= 1
    db.commit()
    return {"success": True, "message": "Left channel"}


# ─── Discussions ─────────────────────────────────────────────────────────────

@router.get("/discussions")
async def get_discussions(
    channel_id: Optional[int] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        q = db.query(CommunityDiscussion)
        if channel_id:
            q = q.filter_by(channel_id=channel_id)
        discussions = q.order_by(CommunityDiscussion.is_pinned.desc(), CommunityDiscussion.created_at.desc()).offset(offset).limit(limit).all()
        return {"success": True, "data": [_discussion_dict(d, current_user.id, db) for d in discussions]}
    except Exception as e:
        logger.error(f"Get discussions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch discussions")


@router.get("/discussions/{discussion_id}")
async def get_discussion(
    discussion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")
    d.view_count = (d.view_count or 0) + 1
    db.commit()

    replies = [{
        "id": r.id, "content": r.content, "like_count": r.like_count,
        "author": {"id": r.user.id, "name": r.user.name} if r.user else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in d.replies]

    data = _discussion_dict(d, current_user.id, db)
    data["replies"] = replies
    return {"success": True, "data": data}


@router.post("/discussions")
async def create_discussion(
    body: CreateDiscussionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ch = db.query(CommunityChannel).filter_by(id=body.channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    d = CommunityDiscussion(
        channel_id=body.channel_id, user_id=current_user.id,
        title=body.title.strip(), content=body.content.strip(),
        tags=body.tags or []
    )
    db.add(d)
    ch.post_count = (ch.post_count or 0) + 1
    current_user.total_chops = (current_user.total_chops or 0) + 10
    db.commit()
    db.refresh(d)
    _log_activity(db, current_user.id, "posted", d.id, "discussion", d.title)
    return {"success": True, "data": _discussion_dict(d, current_user.id, db)}


@router.post("/discussions/{discussion_id}/like")
async def like_discussion(
    discussion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")

    existing = db.query(DiscussionLike).filter_by(user_id=current_user.id, discussion_id=discussion_id).first()
    if existing:
        # Unlike
        db.delete(existing)
        d.like_count = max(0, (d.like_count or 0) - 1)
        db.commit()
        return {"success": True, "liked": False, "like_count": d.like_count}

    db.add(DiscussionLike(user_id=current_user.id, discussion_id=discussion_id))
    d.like_count = (d.like_count or 0) + 1
    db.commit()
    return {"success": True, "liked": True, "like_count": d.like_count}


@router.post("/discussions/{discussion_id}/replies")
async def reply_to_discussion(
    discussion_id: int,
    body: CreateReplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")

    reply = DiscussionReply(discussion_id=discussion_id, user_id=current_user.id, content=body.content.strip())
    db.add(reply)
    d.reply_count = (d.reply_count or 0) + 1
    current_user.total_chops = (current_user.total_chops or 0) + 5
    db.commit()
    db.refresh(reply)

    return {"success": True, "data": {
        "id": reply.id, "content": reply.content, "like_count": 0,
        "author": {"id": current_user.id, "name": current_user.name},
        "created_at": reply.created_at.isoformat() if reply.created_at else None,
    }}


# ─── Events ──────────────────────────────────────────────────────────────────

@router.get("/events/my")
async def get_my_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    regs = db.query(EventRegistration).filter_by(user_id=current_user.id).all()
    events = [_event_dict(r.event, current_user.id, db) for r in regs if r.event]
    return {"success": True, "data": events}


@router.get("/events")
async def get_events(
    type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        q = db.query(CommunityEvent).filter_by(is_published=True)
        if type and type.lower() != "all":
            q = q.filter(CommunityEvent.event_type == type)
        events = q.order_by(CommunityEvent.scheduled_at.asc()).all()
        return {"success": True, "data": [_event_dict(ev, current_user.id, db) for ev in events]}
    except Exception as e:
        logger.error(f"Get events error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch events")


@router.post("/events/{event_id}/register")
async def register_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ev = db.query(CommunityEvent).filter_by(id=event_id, is_published=True).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    if ev.max_attendees and ev.attendee_count >= ev.max_attendees:
        raise HTTPException(status_code=400, detail="Event is fully booked")

    existing = db.query(EventRegistration).filter_by(user_id=current_user.id, event_id=event_id).first()
    if existing:
        return {"success": True, "message": "Already registered"}

    db.add(EventRegistration(user_id=current_user.id, event_id=event_id))
    ev.attendee_count = (ev.attendee_count or 0) + 1
    db.commit()
    _log_activity(db, current_user.id, "registered_event", event_id, "event", ev.title)
    return {"success": True, "message": f"Registered for {ev.title}"}


@router.post("/events/{event_id}/unregister")
async def unregister_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reg = db.query(EventRegistration).filter_by(user_id=current_user.id, event_id=event_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Not registered")

    ev = db.query(CommunityEvent).filter_by(id=event_id).first()
    db.delete(reg)
    if ev and ev.attendee_count > 0:
        ev.attendee_count -= 1
    db.commit()
    return {"success": True, "message": "Unregistered from event"}


# ─── User Activity, Profile, Leaderboard ────────────────────────────────────

@router.get("/activity")
async def get_my_activity(
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    activities = db.query(CommunityActivity).filter_by(user_id=current_user.id)\
        .order_by(CommunityActivity.created_at.desc()).limit(limit).all()
    return {"success": True, "data": [{
        "id": a.id, "action_type": a.action_type, "target_id": a.target_id,
        "target_type": a.target_type, "target_name": a.target_name,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    } for a in activities]}


@router.get("/profile")
async def get_my_community_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    channels_joined = db.query(ChannelMember).filter_by(user_id=current_user.id).count()
    posts_count = db.query(CommunityDiscussion).filter_by(user_id=current_user.id).count()
    events_count = db.query(EventRegistration).filter_by(user_id=current_user.id).count()
    replies_count = db.query(DiscussionReply).filter_by(user_id=current_user.id).count()

    return {"success": True, "data": {
        "user_id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "total_chops": current_user.total_chops or 0,
        "channels_joined": channels_joined,
        "posts": posts_count,
        "replies": replies_count,
        "events_registered": events_count,
    }}


@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = Query(10, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    top_users = db.query(User).filter(User.is_active == True)\
        .order_by(User.total_chops.desc()).limit(limit).all()

    return {"success": True, "data": [{
        "rank": idx + 1,
        "user_id": u.id,
        "name": u.name,
        "total_chops": u.total_chops or 0,
        "referral_count": u.referral_count or 0,
    } for idx, u in enumerate(top_users)]}


# ─── Saved Items ─────────────────────────────────────────────────────────────

@router.get("/saved")
async def get_saved_items(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    items = db.query(SavedItem).filter_by(user_id=current_user.id)\
        .order_by(SavedItem.created_at.desc()).all()
    return {"success": True, "data": [{
        "id": item.id, "item_id": item.item_id, "item_type": item.item_type,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    } for item in items]}


@router.post("/saved")
async def save_item(
    body: SaveItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.query(SavedItem).filter_by(user_id=current_user.id, item_id=body.item_id, item_type=body.item_type).first()
    if existing:
        return {"success": True, "message": "Already saved", "id": existing.id}

    saved = SavedItem(user_id=current_user.id, item_id=body.item_id, item_type=body.item_type)
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return {"success": True, "data": {"id": saved.id, "item_id": saved.item_id, "item_type": saved.item_type}}


@router.delete("/saved/{item_id}")
async def unsave_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    saved = db.query(SavedItem).filter_by(id=item_id, user_id=current_user.id).first()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved item not found")
    db.delete(saved)
    db.commit()
    return {"success": True, "message": "Item unsaved"}
