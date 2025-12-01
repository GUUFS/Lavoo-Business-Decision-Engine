
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from db.pg_connections import get_db
from db.pg_models import User, Review, ReviewCreate, Conversation, ReviewResponse, ConversationCreate, ConversationResponse, UnreadCountResponse
from api.routes.login import get_current_user

from typing import Optional, List

router = APIRouter(tags=["reviews"])


# Helper function
def format_review_response(review: Review, db: Session) -> dict:
    """Format review with conversation metadata"""
    conversation_count = db.query(Conversation).filter(Conversation.review_id == review.id).count()
    
    admin_response = db.query(Conversation).filter(
        Conversation.review_id == review.id,
        Conversation.sender_type == "admin"
    ).count() > 0
    
    unread_messages = db.query(Conversation).filter(
        Conversation.review_id == review.id,
        Conversation.sender_type == "admin",
        Conversation.is_read == False
    ).count()
    
    return {
        "id": review.id,
        "business_name": review.business_name,
        "review_title": review.review_title,
        "rating": review.rating,
        "review_text": review.review_text,
        "date_submitted": review.date_submitted,
        "status": review.status,
        "category": review.category,
        "helpful": review.helpful,
        "verified": review.verified,
        "admin_response": admin_response,
        "conversation_count": conversation_count,
        "unread_messages": unread_messages,
        "has_conversation": conversation_count > 0
    }

# API Endpoints

@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Reviews API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@router.post("/api/reviews", response_model=ReviewResponse)
async def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    """Submit a new review"""
    try:
        db_review = Review(
            user_id=1,
            business_name=review.business_name,
            review_title=review.review_title,
            rating=review.rating,
            review_text=review.review_text,
            category=review.category
        )
        db.add(db_review)
        db.commit()
        db.refresh(db_review)
        
        return format_review_response(db_review, db)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating review: {str(e)}")


@router.get("/api/reviews", response_model=List[ReviewResponse])
async def get_reviews(db: Session = Depends(get_db)):
    """Get all reviews for the current user"""
    try:
        user_id = 1
        reviews = db.query(Review).filter(Review.user_id == user_id).order_by(Review.date_submitted.desc()).all()
        
        return [format_review_response(review, db) for review in reviews]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reviews: {str(e)}")


@router.get("/api/reviews/conversations", response_model=List[ReviewResponse])
async def get_reviews_with_conversations(db: Session = Depends(get_db)):
    """Get only reviews that have conversations"""
    try:
        user_id = 1
        reviews = db.query(Review).filter(Review.user_id == user_id).all()
        
        reviews_with_conversations = []
        for review in reviews:
            conversation_count = db.query(Conversation).filter(Conversation.review_id == review.id).count()
            if conversation_count > 0:
                reviews_with_conversations.append(format_review_response(review, db))
        
        return reviews_with_conversations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")


@router.get("/api/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: int, db: Session = Depends(get_db)):
    """Get a specific review"""
    try:
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        return format_review_response(review, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching review: {str(e)}")


@router.get("/api/reviews/{review_id}/conversations", response_model=List[ConversationResponse])
async def get_conversations(review_id: int, db: Session = Depends(get_db)):
    """Get all conversations for a review"""
    try:
        conversations = db.query(Conversation).filter(
            Conversation.review_id == review_id
        ).order_by(Conversation.timestamp.asc()).all()
        
        return conversations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")


@router.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation(conversation: ConversationCreate, db: Session = Depends(get_db)):
    """Add a message to a conversation"""
    try:
        db_conversation = Conversation(
            review_id=conversation.review_id,
            sender_type=conversation.sender_type,
            message=conversation.message
        )
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        
        return db_conversation
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")


@router.put("/api/conversations/{review_id}/mark-read")
async def mark_conversations_read(review_id: int, db: Session = Depends(get_db)):
    """Mark all admin messages in a review as read"""
    try:
        conversations = db.query(Conversation).filter(
            Conversation.review_id == review_id,
            Conversation.sender_type == "admin",
            Conversation.is_read == False
        ).all()
        
        for conversation in conversations:
            conversation.is_read = True
        
        db.commit()
        
        return {"message": "Conversations marked as read", "count": len(conversations)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error marking conversations: {str(e)}")


@router.get("/api/reviews/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(db: Session = Depends(get_db)):
    """Get total unread message count"""
    try:
        user_id = 1
        reviews = db.query(Review).filter(Review.user_id == user_id).all()
        
        total_unread = 0
        reviews_with_unread = 0
        
        for review in reviews:
            unread = db.query(Conversation).filter(
                Conversation.review_id == review.id,
                Conversation.sender_type == "admin",
                Conversation.is_read == False
            ).count()
            
            if unread > 0:
                total_unread += unread
                reviews_with_unread += 1
        
        return {
            "total_unread": total_unread,
            "reviews_with_unread": reviews_with_unread
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching unread count: {str(e)}")

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}