# backend.py - Run this file directly with: python backend.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

print("🚀 Starting Reviews API...")

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./reviews.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

print("✅ Database connection established")

# Database Models
class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, default=1)
    business_name = Column(String, index=True)
    review_title = Column(String)
    rating = Column(Integer)
    review_text = Column(Text)
    date_submitted = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="under-review")
    category = Column(String, default="General")
    helpful = Column(Integer, default=0)
    verified = Column(Boolean, default=False)
    
    conversations = relationship("Conversation", back_populates="review", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    sender_type = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    
    review = relationship("Review", back_populates="conversations")

# Create tables
Base.metadata.create_all(bind=engine)
print("✅ Database tables created")

# Pydantic Models
class ReviewCreate(BaseModel):
    business_name: str
    review_title: str
    rating: int
    review_text: str
    category: Optional[str] = "General"

class ReviewResponse(BaseModel):
    id: int
    business_name: str
    review_title: str
    rating: int
    review_text: str
    date_submitted: datetime
    status: str
    category: str
    helpful: int
    verified: bool
    admin_response: bool
    conversation_count: int
    unread_messages: int
    has_conversation: bool

    class Config:
        from_attributes = True

class ConversationCreate(BaseModel):
    review_id: int
    sender_type: str
    message: str

class ConversationResponse(BaseModel):
    id: int
    review_id: int
    sender_type: str
    message: str
    timestamp: datetime
    is_read: bool

    class Config:
        from_attributes = True

class UnreadCountResponse(BaseModel):
    total_unread: int
    reviews_with_unread: int

# FastAPI App
app = FastAPI(title="Reviews API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("✅ CORS middleware configured")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function
def format_review_response(review: Review, db: Session) -> dict:
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
@app.get("/")
async def root():
    return {
        "message": "Reviews API is running!",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/api/reviews", response_model=ReviewResponse)
async def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    """Submit a new review"""
    print(f"📝 Creating review for: {review.business_name}")
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
        print(f"✅ Review created with ID: {db_review.id}")
        
        return format_review_response(db_review, db)
    except Exception as e:
        print(f"❌ Error creating review: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating review: {str(e)}")

@app.get("/api/reviews", response_model=List[ReviewResponse])
async def get_reviews(db: Session = Depends(get_db)):
    """Get all reviews for the current user"""
    print("📖 Fetching all reviews...")
    try:
        user_id = 1
        reviews = db.query(Review).filter(Review.user_id == user_id).order_by(Review.date_submitted.desc()).all()
        print(f"✅ Found {len(reviews)} reviews")
        
        return [format_review_response(review, db) for review in reviews]
    except Exception as e:
        print(f"❌ Error fetching reviews: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching reviews: {str(e)}")

@app.get("/api/reviews/conversations", response_model=List[ReviewResponse])
async def get_reviews_with_conversations(db: Session = Depends(get_db)):
    """Get only reviews that have conversations"""
    print("💬 Fetching reviews with conversations...")
    try:
        user_id = 1
        reviews = db.query(Review).filter(Review.user_id == user_id).all()
        
        reviews_with_conversations = []
        for review in reviews:
            conversation_count = db.query(Conversation).filter(Conversation.review_id == review.id).count()
            if conversation_count > 0:
                reviews_with_conversations.append(format_review_response(review, db))
        
        print(f"✅ Found {len(reviews_with_conversations)} conversations")
        return reviews_with_conversations
    except Exception as e:
        print(f"❌ Error fetching conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")

@app.get("/api/reviews/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(db: Session = Depends(get_db)):
    """Get total unread message count"""
    print("🔔 Checking unread count...")
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
        
        print(f"✅ Unread count: {total_unread}")
        return {
            "total_unread": total_unread,
            "reviews_with_unread": reviews_with_unread
        }
    except Exception as e:
        print(f"❌ Error fetching unread count: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching unread count: {str(e)}")

@app.get("/api/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: int, db: Session = Depends(get_db)):
    """Get a specific review"""
    print(f"📖 Fetching review ID: {review_id}")
    try:
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        return format_review_response(review, db)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching review: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching review: {str(e)}")

@app.get("/api/reviews/{review_id}/conversations", response_model=List[ConversationResponse])
async def get_conversations(review_id: int, db: Session = Depends(get_db)):
    """Get all conversations for a review"""
    print(f"💬 Fetching conversations for review ID: {review_id}")
    try:
        conversations = db.query(Conversation).filter(
            Conversation.review_id == review_id
        ).order_by(Conversation.timestamp.asc()).all()
        
        print(f"✅ Found {len(conversations)} messages")
        return conversations
    except Exception as e:
        print(f"❌ Error fetching conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")

@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation(conversation: ConversationCreate, db: Session = Depends(get_db)):
    """Add a message to a conversation"""
    print(f"💬 Creating conversation message for review ID: {conversation.review_id}")
    try:
        db_conversation = Conversation(
            review_id=conversation.review_id,
            sender_type=conversation.sender_type,
            message=conversation.message
        )
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        
        print(f"✅ Message created with ID: {db_conversation.id}")
        return db_conversation
    except Exception as e:
        print(f"❌ Error creating conversation: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

@app.put("/api/conversations/{review_id}/mark-read")
async def mark_conversations_read(review_id: int, db: Session = Depends(get_db)):
    """Mark all admin messages in a review as read"""
    print(f"✅ Marking messages as read for review ID: {review_id}")
    try:
        conversations = db.query(Conversation).filter(
            Conversation.review_id == review_id,
            Conversation.sender_type == "admin",
            Conversation.is_read == False
        ).all()
        
        for conversation in conversations:
            conversation.is_read = True
        
        db.commit()
        
        print(f"✅ Marked {len(conversations)} messages as read")
        return {"message": "Conversations marked as read", "count": len(conversations)}
    except Exception as e:
        print(f"❌ Error marking conversations: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error marking conversations: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🚀 Starting FastAPI server...")
    print("="*60)
    print("📍 Server URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("💚 Health Check: http://localhost:8000/health")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")