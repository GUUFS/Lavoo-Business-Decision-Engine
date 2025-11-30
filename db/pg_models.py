# db/pg_models.py
"""
PostgreSQL database models - works with both PostgreSQL and SQLite.
This file contains all ORM models for the application.
"""

from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, ForeignKey, JSON, Boolean, DECIMAL, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import VARCHAR
from datetime import datetime
from decimal import Decimal

from .pg_connections import Base

import enum
from uuid import uuid4
from typing import Optional, List

class User(Base):
    """
    User model for authentication and user management.
    Stores user account information.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)  # Hashed password
    confirm_password = Column(String(255), nullable=False)  # For validation
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_admin = Column(Boolean, default=False)
    subscription_status = Column(String, default="Free")
    subscription_plan = Column(String, nullable=True)

    subscriptions = relationship("Subscriptions", back_populates="user")
    tickets = relationship("Ticket", back_populates="user")


class AITool(Base):
    """
    AI Tool model for storing the catalog of AI tools.
    This replaces the CSV file with database storage.
    """

    __tablename__ = "ai_tools"

    id = Column(Integer, primary_key=True, index=True)

    # Basic Information
    name = Column(String(255), unique=True, index=True, nullable=False)
    url = Column(String(500))
    description = Column(Text, nullable=False)
    summary = Column(Text)

    # Categorization
    main_category = Column(String(255), index=True)
    sub_category = Column(String(255), index=True)
    ai_categories = Column(Text)  # JSON string of categories

    # Pricing and Ratings
    pricing = Column(Text)
    ratings = Column(Float, default=0.0)

    # Features
    key_features = Column(Text)  # JSON string of features
    pros = Column(Text)  # Pipe-separated list
    cons = Column(Text)  # Pipe-separated list

    # Usage Information
    who_should_use = Column(Text)  # JSON string of use cases
    compatibility_integration = Column(Text)  # JSON string of integrations

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BusinessAnalysis(Base):
    """
    Stores complete business analysis results from AI analyzer.
    Each analysis contains goals, capabilities, tool recommendations, and roadmap.
    """

    __tablename__ = "business_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Original user input
    business_goal = Column(Text, nullable=False)  # Original user query

    # AI Analysis Results (JSON fields)
    intent_analysis = Column(JSON)  # Objective, capabilities, stages, metrics
    tool_combinations = Column(JSON)  # 2-3 recommended tool combos with synergies
    roadmap = Column(JSON)  # Actionable plan with timeline
    roi_projections = Column(JSON)  # ROI calculations, break-even, revenue impact
    ai_tools_data = Column(JSON)  # Generated AI efficiency tools with LLM processing
    estimated_cost = Column(Float)  # Monthly cost estimate
    timeline_weeks = Column(Integer)  # Implementation timeline

    # Metadata
    status = Column(String(50), default="completed")  # pending, completed, failed
    ai_model_used = Column(String(100), default="gpt-4o-mini")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="business_analyses")


class ToolCombination(Base):
    """
    Stores recommended tool combinations for a business analysis.
    Each combination represents a set of 2+ tools that work together.
    """

    __tablename__ = "tool_combinations"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("business_analyses.id"), nullable=False)

    # Combination details
    combo_name = Column(String(255))  # e.g., "Email Growth Stack"
    tools = Column(JSON)  # List of tool IDs and names
    synergy_score = Column(Float)  # AI-calculated synergy (0-100)

    # Integration details
    integration_flow = Column(JSON)  # How tools connect (data flow)
    setup_difficulty = Column(String(50))  # Easy, Medium, Hard
    total_monthly_cost = Column(Float)

    # AI reasoning
    why_this_combo = Column(Text)  # AI explanation
    expected_outcome = Column(Text)  # What user can achieve

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    analysis = relationship("BusinessAnalysis", backref="combinations")


class RoadmapStage(Base):
    """
    Individual stages in the implementation roadmap.
    Each analysis has multiple stages (setup, execution, optimization).
    """

    __tablename__ = "roadmap_stages"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("business_analyses.id"), nullable=False)

    # Stage details
    stage_number = Column(Integer, nullable=False)  # 1, 2, 3...
    stage_name = Column(String(255))  # Setup, Execute, Optimize
    duration_weeks = Column(Integer)

    # Tasks and deliverables
    tasks = Column(JSON)  # List of action items
    deliverables = Column(JSON)  # Expected outputs
    metrics = Column(JSON)  # KPIs to track

    # Cost breakdown
    cost_this_stage = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    analysis = relationship("BusinessAnalysis", backref="roadmap_stages")


# Pydantic models for API validation and serialization


class ShowUser(BaseModel):
    """Pydantic model for user login request"""

    email: str
    password: str


class UserResponse(BaseModel):
    """Pydantic model for user response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class AIToolBase(BaseModel):
    """Base Pydantic model for AI Tool"""

    name: str
    description: str
    main_category: str | None = None
    sub_category: str | None = None
    pricing: str | None = None
    ratings: float | None = 0.0
    url: str | None = None


class AIToolCreate(AIToolBase):
    """Pydantic model for creating AI Tool"""

    key_features: str | None = None
    pros: str | None = None
    cons: str | None = None
    who_should_use: str | None = None
    compatibility_integration: str | None = None


class AIToolResponse(AIToolBase):
    """Pydantic model for AI Tool response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key_features: str | None = None
    pros: str | None = None
    cons: str | None = None
    who_should_use: str | None = None
    compatibility_integration: str | None = None


class ToolRecommendation(BaseModel):
    """Pydantic model for tool recommendation response"""

    tool_name: str
    similarity_score: float
    description: str


class BusinessAnalysisRequest(BaseModel):
    """Request model for business analysis"""

    business_goal: str  # User's goal (e.g., "Grow AI newsletter to 10k subs")


class IntentAnalysis(BaseModel):
    """Parsed intent from user goal"""

    objective: str
    capabilities_needed: list[str]
    stages: list[str]
    success_metrics: list[str]


class ToolComboResponse(BaseModel):
    """Single tool combination recommendation"""

    combo_name: str
    tools: list[dict]  # [{id, name, pricing}]
    synergy_score: float
    integration_flow: dict
    setup_difficulty: str
    total_monthly_cost: float
    why_this_combo: str
    expected_outcome: str


class RoadmapStageResponse(BaseModel):
    """Single roadmap stage"""

    stage_number: int
    stage_name: str
    duration_weeks: int
    tasks: list[str]
    deliverables: list[str]
    metrics: list[str]
    cost_this_stage: float


class BusinessAnalysisResponse(BaseModel):
    """Complete business analysis response"""

    analysis_id: int
    business_goal: str
    intent_analysis: IntentAnalysis
    tool_combinations: list[ToolComboResponse]
    roadmap: list[RoadmapStageResponse]
    estimated_cost: float
    timeline_weeks: int
    created_at: str

class AuthResponse(BaseModel):
    """Pydantic model for authentication token response"""
    access_token: str
    token_type: str
    id: int
    name: str
    email: str
    role: str
    subscription_status: str | None = None
    subscription_plan: str | None = None

# Paypal payment gateway
class CreateOrderRequest(BaseModel):
    amount: str    # e.g. "29.00"
    currency: str = "USD"

class CaptureRequest(BaseModel):
    order_id: str

# Subcriptions table
class Subscriptions(Base):
    """
    Contains information about subscription payments made by customers
    """

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subscription_plan = Column(VARCHAR(50) )
    transaction_id = Column(String(255), nullable=False, unique=True, index=True)
    tx_ref = Column(String, unique=True, index=True, nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(VARCHAR(10), nullable=False)
    status = Column(VARCHAR(20), nullable=False)
    payment_provider = Column(VARCHAR(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="subscriptions")


# Models for the stripe payment gateway
class PaymentIntentCreate(BaseModel):
    amount: float
    plan_type: str  # monthly or yearly
    email: EmailStr
    name: str
    user_id: int

class PaymentIntentResponse(BaseModel):
    clientSecret: str
    paymentIntentId: str
    amount: float
    currency: str

class PaymentVerify(BaseModel):
    payment_intent_id: str
    user_id: int

class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    subscription_plan: str
    transaction_id: str
    tx_ref: str
    amount: Decimal
    currency: str
    status: str
    payment_provider: str
    created_at: datetime
    start_date: datetime
    end_date: datetime

    class Config:
        from_attributes = True


'''Customer Service tables and models
    Tickets for users reports are also included
'''
class TicketCreate(BaseModel):
    issue: str
    category: Optional[str] = "general"

class MessageCreate(BaseModel):
    ticket_id: int
    message: str

class TicketResponse(BaseModel):
    id: int
    user_id: int
    issue: str
    category: str
    status: str
    created_at: datetime
    updated_at: datetime
    unread_count: int = 0
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_id: int
    sender_name: str
    sender_role: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    issue = Column(Text, nullable=False)
    category = Column(String(50), default="general")  # general, technical, billing, etc.
    status = Column(String(50), default="open")  # open, in_progress, resolved, closed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tickets")
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_role = Column(String(20), nullable=False)  # "user" or "admin"
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket = relationship("Ticket", back_populates="messages")
    sender = relationship("User")


'''Customer reviews tables and the information
'''
class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)  # Add user authentication later
    business_name = Column(String, index=True)
    review_title = Column(String)
    rating = Column(Integer)
    review_text = Column(Text)
    date_submitted = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="under-review")  # published, under-review, rejected
    category = Column(String, default="General")
    helpful = Column(Integer, default=0)
    verified = Column(Boolean, default=False)

    conversations = relationship("Conversation", back_populates="review", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    sender_type = Column(String)  # 'admin' or 'user'
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)

    # Relationships
    review = relationship("Review", back_populates="conversations")

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
