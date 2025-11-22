
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from db.pg_connections import get_db
from db.pg_models import User, Ticket, TicketMessage, TicketCreate, MessageCreate, TicketResponse, MessageResponse
from api.routes.login import get_current_user

from typing import Optional

router = APIRouter(prefix="/api/customer-service", tags=["customer-service"])

def extract_user_id(current_user):
    """Helper function to extract user_id from current_user"""
    if isinstance(current_user, dict):
        if "user" in current_user:
            user_data = current_user["user"]
            if isinstance(user_data, dict):
                return user_data.get("id") or user_data.get("user_id")
            elif hasattr(user_data, 'id'):
                return user_data.id
            else:
                return user_data
        else:
            return current_user.get("id") or current_user.get("user_id") or current_user.get("sub")
    else:
        return current_user.id

# USER ENDPOINTS

@router.post("/tickets/create")
async def create_ticket(
    ticket_data: TicketCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    print(f"Current user: {current_user}")
    print(f"User ID: {extract_user_id(current_user)}")
    """
    Create a new support ticket
    """
    try:
        user_id = extract_user_id(current_user)
        
        if not ticket_data.issue.strip():
            raise HTTPException(status_code=400, detail="Issue description is required")
        
        # Create ticket
        new_ticket = Ticket(
            user_id=user_id,
            issue=ticket_data.issue.strip(),
            category=ticket_data.category,
            status="open",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_ticket)
        db.commit()
        db.refresh(new_ticket)
        
        # Create initial message from user
        initial_message = TicketMessage(
            ticket_id=new_ticket.id,
            sender_id=user_id,
            sender_role="user",
            message=ticket_data.issue.strip(),
            is_read=True,  # User's own message is marked as read
            created_at=datetime.utcnow()
        )
        
        db.add(initial_message)
        db.commit()
        
        return {
            "message": "Ticket created successfully",
            "ticket_id": new_ticket.id
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Error creating ticket: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tickets/my-tickets")
async def get_my_tickets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all tickets for the current user with unread message counts
    """
    try:
        user_id = extract_user_id(current_user)
        
        tickets = db.query(Ticket).filter(
            Ticket.user_id == user_id
        ).order_by(Ticket.updated_at.desc()).all()
        
        result = []
        for ticket in tickets:
            # Get unread message count (messages from admin that user hasn't read)
            unread_count = db.query(TicketMessage).filter(
                TicketMessage.ticket_id == ticket.id,
                TicketMessage.sender_role == "admin",
                TicketMessage.is_read == False
            ).count()
            
            # Get last message
            last_message = db.query(TicketMessage).filter(
                TicketMessage.ticket_id == ticket.id
            ).order_by(TicketMessage.created_at.desc()).first()
            
            result.append({
                "id": ticket.id,
                "user_id": ticket.user_id,
                "issue": ticket.issue,
                "category": ticket.category,
                "status": ticket.status,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
                "unread_count": unread_count,
                "last_message": last_message.message if last_message else None,
                "last_message_at": last_message.created_at if last_message else None
            })
        
        return {"tickets": result}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tickets/{ticket_id}/messages")
async def get_ticket_messages( ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get all messages for a specific ticket
    """
    try:
        user_id = extract_user_id(current_user)
        print(f"Loading messages for ticket {ticket_id}, user {user_id}")  # Debug log
        
        # Verify ticket belongs to user
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.user_id == user_id
        ).first()
        
        if not ticket:
            print(f"Ticket {ticket_id} not found for user {user_id}")  # Debug log
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Get all messages
        messages = db.query(TicketMessage).filter(
            TicketMessage.ticket_id == ticket_id
        ).order_by(TicketMessage.created_at.asc()).all()
        
        print(f"Found {len(messages)} messages")  # Debug log
        
        # Mark admin messages as read
        try:
            for message in messages:
                if message.sender_role == "admin" and not message.is_read:
                    message.is_read = True
                    print(f"Marking message {message.id} as read")  # Debug log
            
            db.commit()
        except Exception as e:
            print(f"Error marking messages as read: {str(e)}")  # Debug log
            db.rollback()
            # Don't fail the request if we can't mark as read
        
        # Format messages with sender info
        result = []
        for msg in messages:
            try:
                sender = db.query(User).filter(User.id == msg.sender_id).first()
                if sender:
                    # Try these in order: full_name, name, email
                    sender_name = (
                        getattr(sender, 'full_name', None) or 
                        getattr(sender, 'name', None) or 
                        getattr(sender, 'email', 'Admin')
                    )
                else:
                    sender_name = "Admin"
                
                result.append({
                    "id": msg.id,
                    "ticket_id": msg.ticket_id,
                    "sender_id": msg.sender_id,
                    "sender_name": sender_name,
                    "sender_role": msg.sender_role,
                    "message": msg.message,
                    "is_read": msg.is_read,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                })
            except Exception as e:
                print(f"Error formatting message {msg.id}: {str(e)}")  # Debug log
                # Skip malformed messages
                continue
        
        return {
            "ticket": {
                "id": ticket.id,
                "issue": ticket.issue,
                "status": ticket.status,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None
            },
            "messages": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_ticket_messages: {str(e)}")  # Debug log
        import traceback
        traceback.print_exc()  # Print full traceback
        raise HTTPException(status_code=400, detail=f"Error loading messages: {str(e)}")

@router.post("/tickets/{ticket_id}/reply")
async def reply_to_ticket( ticket_id: int, message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    User replies to a ticket
    """
    try:
        user_id = extract_user_id(current_user)
        
        # Verify ticket belongs to user
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.user_id == user_id
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        if not message_data.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Create message
        new_message = TicketMessage(
            ticket_id=ticket_id,
            sender_id=user_id,
            sender_role="user",
            message=message_data.message.strip(),
            is_read=True,  # User's own message
            created_at=datetime.utcnow()
        )
        
        db.add(new_message)
        
        # Update ticket updated_at
        ticket.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "Reply sent successfully"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# ADMIN ENDPOINTS

@router.get("/admin/tickets")
async def get_all_tickets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None
):
    """
    Get all tickets (admin only)
    """
    try:
        user_id = extract_user_id(current_user)
        
        # Check if user is admin
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Query tickets
        query = db.query(Ticket)
        if status:
            query = query.filter(Ticket.status == status)
        
        tickets = query.order_by(Ticket.updated_at.desc()).all()
        
        result = []
        for ticket in tickets:
            # Get user info
            ticket_user = db.query(User).filter(User.id == ticket.user_id).first()
            
            # Get unread message count (messages from user that admin hasn't read)
            unread_count = db.query(TicketMessage).filter(
                TicketMessage.ticket_id == ticket.id,
                TicketMessage.sender_role == "user",
                TicketMessage.is_read == False
            ).count()
            
            # Get last message
            last_message = db.query(TicketMessage).filter(
                TicketMessage.ticket_id == ticket.id
            ).order_by(TicketMessage.created_at.desc()).first()
            
            result.append({
                "id": ticket.id,
                "user_id": ticket.user_id,
                "user_name": ticket_user.full_name if ticket_user else "Unknown",
                "user_email": ticket_user.email if ticket_user else "Unknown",
                "issue": ticket.issue,
                "category": ticket.category,
                "status": ticket.status,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
                "unread_count": unread_count,
                "last_message": last_message.message if last_message else None,
                "last_message_at": last_message.created_at if last_message else None
            })
        
        return {"tickets": result}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/admin/tickets/{ticket_id}/reply")
async def admin_reply_to_ticket(
    ticket_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin replies to a ticket
    """
    try:
        user_id = extract_user_id(current_user)
        
        # Check if user is admin
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Verify ticket exists
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        if not message_data.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Create message
        new_message = TicketMessage(
            ticket_id=ticket_id,
            sender_id=user_id,
            sender_role="admin",
            message=message_data.message.strip(),
            is_read=False,  # Not read by user yet
            created_at=datetime.utcnow()
        )
        
        db.add(new_message)
        
        # Update ticket status to in_progress if it's open
        if ticket.status == "open":
            ticket.status = "in_progress"
        
        ticket.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "Reply sent successfully"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/admin/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: int,
    status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update ticket status (admin only)
    """
    try:
        user_id = extract_user_id(current_user)
        
        # Check if user is admin
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Validate status
        valid_statuses = ["open", "in_progress", "resolved", "closed"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        # Update ticket
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        ticket.status = status
        ticket.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": f"Ticket status updated to {status}"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))