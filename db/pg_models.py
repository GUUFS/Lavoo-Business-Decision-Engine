# db/pg_models.py
"""
PostgreSQL database models - works with both PostgreSQL and SQLite.
This file contains all ORM models for the application.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import Column, DateTime, Float, Integer, String, Numeric, Text, ForeignKey, JSON, Boolean, DECIMAL, Enum, Index, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import VARCHAR
from datetime import datetime
from decimal import Decimal
from sqlalchemy.dialects.postgresql import JSONB, INET, UUID

from .pg_connections import Base

import enum
from uuid import uuid4
from typing import Optional, List

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    
    # General
    site_name = Column(String, default="AI Business Intelligence Analyst")
    support_email = Column(String, default="support@aianalyst.com")
    default_language = Column(String, default="en")
    timezone = Column(String, default="UTC")
    
    # User Limits
    max_analyses_basic = Column(Integer, default=10)
    max_analyses_pro = Column(Integer, default=50)
    max_analyses_premium = Column(Integer, default=200)

    # AI Configuration
    primary_ai_model = Column(String, default="gpt-4")
    analysis_timeout = Column(Integer, default=300)
    max_tokens = Column(Integer, default=4000)
    temperature = Column(Float, default=0.7)
    
    # AI Features (Checkboxes)
    enable_predictive_analytics = Column(Boolean, default=True)
    generate_recommendations = Column(Boolean, default=True)
    include_confidence_scores = Column(Boolean, default=True)
    enable_experimental_features = Column(Boolean, default=False)
    
    # Security
    require_mfa_admin = Column(Boolean, default=False)
    force_password_reset_90 = Column(Boolean, default=False)
    lock_accounts_after_failed_attempts = Column(Boolean, default=True)
    data_retention_days = Column(Integer, default=365)
    backup_frequency = Column(String, default="daily")
    
    # Billing
    monthly_price = Column(Float, default=29.95)
    yearly_price = Column(Float, default=290.00)
    # subscription_plan_active (maybe not needed here, inferred from user)


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

    # Chops system (Clinton's feature)
    total_chops = Column(Integer, default=0)
    alert_reading_chops = Column(Integer, default=0)
    alert_sharing_chops = Column(Integer, default=0)
    insight_reading_chops = Column(Integer, default=0)
    insight_sharing_chops = Column(Integer, default=0)
    referral_chops = Column(Integer, default=0)
    referral_count = Column(Integer, default=0)

    # Admin and subscription
    # Admin and subscription
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    user_status = Column(String(20), server_default="active", nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    subscription_status = Column(String, default="Free")
    subscription_plan = Column(String, nullable=True)

    # Profile info
    department = Column(String, nullable=True)
    location = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    
    # Security settings
    two_factor_enabled = Column(Boolean, default=False)
    email_notifications = Column(Boolean, default=True)

    # Referral system (Clinton's feature)
    referral_code = Column(String, unique=True, index=True)
    referrer_code = Column(String, nullable=True)

    # Relationships
    subscriptions = relationship("Subscriptions", back_populates="user")
    tickets = relationship("Ticket", back_populates="user")
    user_alerts = relationship("UserAlert", back_populates="user")
    user_insights = relationship("UserInsight", back_populates="user")
    pinned_insights = relationship("UserPinnedInsight", back_populates="user")
    pinned_alerts = relationship("UserPinnedAlert", back_populates="user")
    referrals = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer")
    referred_by = relationship("Referral", foreign_keys="Referral.referred_user_id", back_populates="referred_user")
    commissions_earned = relationship("Commission", foreign_keys="Commission.user_id", back_populates="user")
    payouts = relationship("Payout", back_populates="user")
    payout_account = relationship("PayoutAccount", back_populates="user", uselist=False)
    commission_summaries = relationship("CommissionSummary", back_populates="user")

    # Table Aruguments
    __table_args__ = (
        Index('idx_users_subscription_status', 'subscription_status'),
    )


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    uptime = Column(Numeric(10, 2))
    uptime_percentage = Column(Numeric(5, 2))
    cpu_usage = Column(Numeric(5, 2))

    memory_total_mb = Column(Integer)
    memory_used_mb = Column(Integer)
    memory_percentage = Column(Integer)

    load_average_1m = Column(Numeric(5, 2))
    load_average_5m = Column(Numeric(5, 2))
    load_average_15m = Column(Numeric(5, 2))

    avg_response_time = Column(Integer)
    requests_per_minute = Column(Integer)
    error_rate = Column(Numeric(5, 2))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Table Arguments
    __table_args__ = (
        Index('idx_system_metrics_timestamp', 'timestamp'),
        Index('idx_system_metrics_created_at', 'created_at'),
    )


class ServiceHealth(Base):
    __tablename__ = "service_health"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)

    uptime = Column(Numeric(5, 2))
    response_time = Column(Integer)
    error_count = Column(Integer, default=0)

    last_error = Column(Text)
    last_check = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_service_health_service','service_name'),
        Index('idx_service_health_status','status'),
        Index('idx_service_health_created','created_at'),
    )


class SystemAlert(Base):
    __tablename__ = "system_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(255), unique=True, nullable=False)

    type = Column(String(20), nullable=False)
    service = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)

    status = Column(String(20), nullable=False, default="active")
    details = Column(JSONB)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(String(255))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_system_alerts_status','status'),
        Index('idx_system_alerts_service','service'),
        Index('idx_system_alerts_timestamp','timestamp'),
        Index('idx_system_alerts_type','type'),
    )


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    service = Column(String(100), nullable=False)
    operation = Column(String(100), nullable=False)

    duration = Column(Integer)
    success = Column(Boolean, default=True)

    user_id = Column(String(255))
    ip_address = Column(String(45))  # INET-compatible
    details = Column(JSONB)
    error_message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_activity_logs_service", service),
        Index("idx_activity_logs_operation", operation),
        Index("idx_activity_logs_created", created_at.desc()),
        Index("idx_activity_logs_success", success),
    )


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)

    status_code = Column(Integer)
    response_time = Column(Integer)

    request_size = Column(Integer)
    response_size = Column(Integer)

    user_id = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(Text)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_performance_endpoint", endpoint),
        Index("idx_performance_timestamp", timestamp.desc()),
        Index("idx_performance_status", status_code),
    )


class DatabaseOperation(Base):
    __tablename__ = "database_operations"

    id = Column(Integer, primary_key=True, index=True)
    operation_type = Column(String(50), nullable=False)
    table_name = Column(String(100), nullable=False)

    duration = Column(Integer)
    rows_affected = Column(Integer)

    success = Column(Boolean, default=True)
    error_message = Column(Text)

    query_hash = Column(String(64))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_db_ops_table", table_name),
        Index("idx_db_ops_timestamp", timestamp.desc()),
        Index("idx_db_ops_duration", duration.desc()),
    )


class ErrorTracking(Base):
    __tablename__ = "error_tracking"

    id = Column(Integer, primary_key=True, index=True)

    error_type = Column(String(100))
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text)

    service = Column(String(100))
    endpoint = Column(String(255))
    method = Column(String(10))

    user_id = Column(String(255))
    ip_address = Column(String(45))
    request_body = Column(JSONB)

    environment = Column(String(50))
    severity = Column(String(20))
    sentry_issue_id = Column(String(255))

    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())

    occurrence_count = Column(Integer, default=1)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_errors_type", error_type),
        Index("idx_errors_service", service),
        Index("idx_errors_severity", severity),
        Index("idx_errors_resolved", resolved),
        Index("idx_errors_last_seen", last_seen.desc()),
    )


class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)

    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)

    user_id = Column(String(255))
    api_key_id = Column(String(255))

    request_count = Column(Integer, default=1)
    total_response_time = Column(Integer)
    avg_response_time = Column(Integer)
    error_count = Column(Integer, default=0)

    date = Column(Date, nullable=False)
    hour = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_api_usage_date", date.desc()),
        Index("idx_api_usage_endpoint", endpoint),
        Index("idx_api_usage_user", user_id),
        UniqueConstraint("endpoint", "method", "user_id", "date", "hour",name="idx_api_usage_unique"),
    )


class UptimeRecord(Base):
    __tablename__ = "uptime_records"

    id = Column(Integer, primary_key=True, index=True)

    date = Column(Date, nullable=False)
    total_uptime_seconds = Column(Integer, nullable=False)
    total_downtime_seconds = Column(Integer, nullable=False)
    uptime_percentage = Column(Numeric(5, 2), nullable=False)

    incidents_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_uptime_date", date.desc()),
        Index("idx_uptime_date_unique", date, unique=True),
    )



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
    roi_projections = Column(JSON)  # ROI calculations, break-even, revenue impact (YOUR FIX)
    ai_tools_data = Column(JSON)  # Generated AI efficiency tools with LLM processing (YOUR FIX)
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
    subscription_status: str
    total_chops: int
    alert_reading_chops: int
    alert_sharing_chops: int
    insight_reading_chops: int
    insight_sharing_chops: int
    referral_chops: int
    referral_count: int
    referral_code: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None


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
    referral_code: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    created_at: Optional[datetime] = None


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

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    commission = relationship("Commission", back_populates="subscription", uselist=False)


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
    status = Column(String, default="Submitted")  # published, under-review, rejected (Clinton's)
    category = Column(String, default="General")
    helpful = Column(Integer, default=0)
    verified = Column(Boolean, default=False)
    is_attended = Column(Boolean, default=False)

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
    is_attended: bool = False

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


'''Opportunity Alert Tables and Schema'''
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    time_remaining = Column(String, nullable=False)
    why_act_now = Column(Text, nullable=False)
    potential_reward = Column(Text, nullable=False)
    action_required = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    url = Column(String(500), nullable=True)
    date = Column(String, nullable=False)
    total_views = Column(Integer, default=0)
    total_shares = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_alerts = relationship("UserAlert", back_populates="alert")


class UserAlert(Base):
    __tablename__ = "user_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    alert_id = Column(Integer, ForeignKey("alerts.id"))
    has_viewed = Column(Boolean, default=False)
    has_shared = Column(Boolean, default=False)
    is_attended = Column(Boolean, default=False)
    viewed_at = Column(DateTime, nullable=True)
    shared_at = Column(DateTime, nullable=True)
    chops_earned_from_view = Column(Integer, default=0)
    chops_earned_from_share = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="user_alerts")
    alert = relationship("Alert", back_populates="user_alerts")


'''Referrals Table'''
class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    referred_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chops_awarded = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals")
    referred_user = relationship("User",foreign_keys=[referred_user_id], back_populates="referred_by")

    # Table Arguments
    __table_args__ = (
        Index('idx_referrals_referrer_id', 'referrer_id'),
        Index('idx_referrals_created_at', 'created_at'),
        Index('idx_referrals_referrer_created', 'referrer_id', 'created_at'),
    )

class ReferralResponse(BaseModel):
    id: int
    referred_user_id: int
    referred_user_email: str
    referred_user_name: str
    chops_awarded: int
    created_at: str
    is_active: bool

    class Config:
        from_attributes = True

class ReferralStats(BaseModel):
    total_referrals: int
    total_chops_earned: int
    referrals_this_month: int
    recent_referrals: List[dict]

    class Config:
        from_attributes = True


class ReferralCreate(BaseModel):
    referred_user_id: int
    chops_awarded: int = 0

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    name: str
    email: str
    subscription_status: str = "free"
    referrer_name: Optional[str] = None

class AlertCreate(BaseModel):
    title: str
    category: str
    priority: str
    score: int
    time_remaining: str
    why_act_now: str
    potential_reward: str
    action_required: str
    source: Optional[str] = None
    date: str


class AlertResponse(BaseModel):
    id: int
    title: str
    category: str
    priority: str
    score: int
    time_remaining: str
    why_act_now: str
    potential_reward: str
    action_required: str
    source: Optional[str]
    url: Optional[str] = None
    date: str
    total_views: int
    total_shares: int
    has_viewed: bool = False
    has_shared: bool = False
    is_attended: bool = False
    is_pinned: bool = False

    class Config:
        from_attributes = True

class ViewAlertRequest(BaseModel):
    alert_id: int

class ShareAlertRequest(BaseModel):
    alert_id: int


'''Insights Tables and Schema'''
class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    category = Column(String)
    read_time = Column(String)
    date = Column(String, nullable=False)
    source = Column(String)
    url = Column(String(500), nullable=True)
    what_changed = Column(Text)
    why_it_matters = Column(Text)
    action_to_take = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    total_views = Column(Integer, default=0)
    total_shares = Column(Integer, default=0)

    user_insights = relationship("UserInsight", back_populates="insight")


class UserInsight(Base):
    __tablename__ = "user_insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    insight_id = Column(Integer, ForeignKey("insights.id"))
    has_viewed = Column(Boolean, default=False)
    has_shared = Column(Boolean, default=False)
    is_attended = Column(Boolean, default=False)
    viewed_at = Column(DateTime, nullable=True)
    shared_at = Column(DateTime, nullable=True)
    chops_earned_from_view = Column(Integer, default=0)
    chops_earned_from_share = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="user_insights")
    insight = relationship("Insight", back_populates="user_insights")


class UserPinnedInsight(Base):
    __tablename__ = "user_pinned_insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    insight_id = Column(Integer, ForeignKey("insights.id"))
    pinned_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="pinned_insights")


class UserPinnedAlert(Base):
    __tablename__ = "user_pinned_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    alert_id = Column(Integer, ForeignKey("alerts.id"))
    pinned_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="pinned_alerts")

class InsightItems(BaseModel):
    id: int
    title: str
    category: str
    read_time: str
    time_remaining: str
    why_changed: str
    why_it_matters: str
    action_to_take: str
    source: Optional[str]
    url: Optional[str] = None
    date: str
    total_views: int
    total_shares: int
    has_viewed: bool = False
    has_shared: bool = False
    is_attended: bool = False
    is_pinned: bool = False
    class Config:
        from_attributes = True


class InsightResponse(BaseModel):
    insights: List[InsightItems]
    current_page: int
    total_pages: int
    total_insights: int
    is_pro: bool


class InsightCreate(BaseModel):
    title: str
    category: str
    read_time: str
    what_changed: str
    why_it_matters: str
    action_to_take: str
    source: Optional[str] = None
    date: str


class ViewInsightRequest(BaseModel):
    insight_id: int


class ShareInsightRequest(BaseModel):
    insight_id: int

    class Config:
        extra = "ignore"


class PinInsightRequest(BaseModel):
    insight_id: int


class PinAlertRequest(BaseModel):
    alert_id: int


class ChopsBreakdown(BaseModel):
    total_chops: int
    alert_reading_chops: int
    alert_sharing_chops: int
    insight_reading_chops: int
    insight_sharing_chops: int
    referral_chops: int
    referral_count: int


'''Information for the Earnings, Commissions and Referral Payouts'''
class UserLevelResponse(BaseModel):
    totalChops: int
    referralChops: int
    currentLevel: int
    currentRank: str


class MonthlyData(BaseModel):
    month: str
    revenue: float
    transactions: int


class EarningsSummary(BaseModel):
    totalCommissions: float
    totalPaidReferrals: int
    referralChops: int
    growthRate: float
    totalRevenue: float
    avgOrderValue: float


class Commission(Base):
    """
    Tracks referral commissions earned by users
    """
    __tablename__ = "commissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # The referrer who earns commission
    referred_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # The user who made the payment
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    
    # Commission details
    amount = Column(Numeric(10, 2), nullable=False)  # Commission amount (50% of subscription)
    original_amount = Column(Numeric(10, 2), nullable=False)  # Original subscription amount
    currency = Column(String(10), nullable=False)
    commission_rate = Column(Numeric(5, 2), default=50.00)  # Percentage (50%)
    
    # Status tracking
    status = Column(String(20), nullable=False, default='pending')  # pending, approved, paid, failed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Payout tracking
    payout_id = Column(Integer, ForeignKey("payouts.id"), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="commissions_earned")
    referred_user = relationship("User", foreign_keys=[referred_user_id])
    subscription = relationship("Subscriptions", back_populates="commission")
    payout = relationship("Payout", back_populates="commissions")

     # Indexes
    __table_args__ = (
        Index('idx_commissions_user_status', 'user_id', 'status'),
        Index('idx_commissions_created_at', 'created_at'),
    )


class Payout(Base):
    """
    Tracks payout requests and transactions to users
    """
    __tablename__ = "payouts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Payout details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False)
    payment_method = Column(String(20), nullable=False)  # stripe, flutterwave
    
    # Status
    status = Column(String(20), nullable=False, default='pending')  # pending, processing, completed, failed, cancelled
    
    # Payment provider details
    provider_payout_id = Column(String(255), nullable=True)  # Stripe/Flutterwave payout ID
    provider_response = Column(Text, nullable=True)  # JSON response from provider
    
    # Recipient details (for payout)
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255), nullable=False)
    
    # Bank/account details (encrypted in production)
    account_details = Column(Text, nullable=False)  # Store encrypted bank details
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error tracking
    failure_reason = Column(Text, nullable=False)
    retry_count = Column(Integer, default=0)
    
    # Notes
    admin_notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="payouts")
    commissions = relationship("Commission", back_populates="payout")
    
    # Indexes
    __table_args__ = (
        Index('idx_payouts_user_status', 'user_id', 'status'),
        Index('idx_payouts_requested_at', 'requested_at'),
    )


class PayoutAccount(Base):
    """
    Stores user's payout account information (bank details, etc.)
    """
    __tablename__ = "payout_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Stripe Connect (if using Stripe payouts)
    stripe_account_id = Column(String(255), nullable=True)
    stripe_account_status = Column(String(50), nullable=True)  # pending, verified, rejected
    
    # Flutterwave Transfer (if using Flutterwave payouts)
    flutterwave_recipient_code = Column(String(255), nullable=True)
    
    # Bank details (for Flutterwave or manual payouts)
    bank_name = Column(String(255), nullable=True)
    account_number = Column(String(50), nullable=True)
    account_name = Column(String(255), nullable=True)
    bank_code = Column(String(50), nullable=True)  # Required for Nigerian banks
    
    # PayPal (optional)
    paypal_email = Column(String(255), nullable=True)
    
    # Default payout method
    default_payout_method = Column(String(20), nullable=True)  # stripe, flutterwave, paypal
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="payout_account")


class CommissionSummary(Base):
    """
    Monthly summary of commissions per user (for reporting and analytics)
    """
    __tablename__ = "commission_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Period
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    
    # Summary metrics
    total_commissions = Column(Numeric(10, 2), default=0.00)
    paid_commissions = Column(Numeric(10, 2), default=0.00)
    pending_commissions = Column(Numeric(10, 2), default=0.00)
    commission_count = Column(Integer, default=0)
    
    # Currency
    currency = Column(String(10), nullable=False, default='USD')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="commission_summaries")
    
    # Unique constraint and indexes
    __table_args__ = (
        Index('idx_commission_summary_user_period', 'user_id', 'year', 'month', unique=True),
    )


class PayoutAccountCreate(BaseModel):
    payment_method: str  # stripe, flutterwave, paypal
    
    # Stripe
    stripe_account_id: Optional[str] = None
    
    # Flutterwave
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    bank_code: Optional[str] = None
    
    # PayPal
    paypal_email: Optional[str] = None
    
    class Config:
        from_attributes = True


class PayoutRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to withdraw")
    payment_method: str = Field(..., description="stripe or flutterwave")
    
    class Config:
        from_attributes = True


class CommissionResponse(BaseModel):
    id: int
    amount: float
    currency: str
    status: str
    created_at: datetime
    referred_user_id: int
    subscription_id: int
    
    class Config:
        from_attributes = True


class PayoutResponse(BaseModel):
    id: int
    amount: float
    currency: str
    status: str
    payment_method: str
    requested_at: datetime
    
    class Config:
        from_attributes = True


class ApproveCommissionsRequest(BaseModel):
    payment_method: Optional[str] = None  # Optional filter by payment method   
    amount: Optional[Decimal] = None


'''Security Architecture Tables'''
# User Session Table
class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    ip_address = Column(INET, nullable=False)
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_active", "is_active"),
    )


# Security Event Table
class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    user_id = Column(UUID(as_uuid=True))
    ip_address = Column(INET, nullable=False)
    location = Column(String(255))
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=False)
    details = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_security_events_type", "type"),
        Index("idx_security_events_severity", "severity"),
        Index("idx_security_events_ip", "ip_address"),
        Index("idx_security_events_created", created_at.desc()),
    )


# IP Blacklist Table
class IPBlacklist(Base):
    __tablename__ = "ip_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(INET, unique=True, nullable=False)
    reason = Column(Text, nullable=False)
    email = Column(String(255), nullable=True)  # Email that attempted login from this IP
    is_active = Column(Boolean, default=True)
    blocked_at = Column(DateTime(timezone=True), server_default=func.now())
    blocked_by = Column(UUID(as_uuid=True))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_ip_blacklist_ip", "ip_address"),
        Index("idx_ip_blacklist_active", "is_active"),
    )


# Failed Login Attempt Table
class FailedLoginAttempt(Base):
    __tablename__ = "failed_login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    ip_address = Column(INET, nullable=False)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_failed_logins_email", "email"),
        Index("idx_failed_logins_ip", "ip_address"),
        Index("idx_failed_logins_time", created_at.desc()),
    )


# Firewall Rule Table
class FirewallRule(Base):
    __tablename__ = "firewall_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    status = Column(String(20), default="active")
    is_active = Column(Boolean, default=True)
    priority = Column(String(20), nullable=False)
    description = Column(Text)
    rule_config = Column(JSONB, nullable=False)
    hits = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_firewall_rules_status", "status"),
        Index("idx_firewall_rules_priority", "priority"),
    )


# Vulnerability Scan Table
class VulnerabilityScan(Base):
    __tablename__ = "vulnerability_scans"

    id = Column(Integer, primary_key=True, index=True)
    scan_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    severity = Column(String(20))
    findings = Column(Integer, default=0)
    scan_results = Column(JSONB)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    __table_args__ = (
        Index("idx_vulnerability_scans_status", "status"),
        Index("idx_vulnerability_scans_started", started_at.desc()),
    )


# Audit Log Table
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(255))
    ip_address = Column(INET, nullable=False)
    user_agent = Column(Text)
    changes = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_audit_log_user", "user_id"),
        Index("idx_audit_log_action", "action"),
        Index("idx_audit_log_created", created_at.desc()),
    )


# Password Reset Token Table
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    ip_address = Column(INET, nullable=False)
    used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_password_reset_token", "token"),
        Index("idx_password_reset_user", "user_id"),
    )


# Security Metrics Summary View-Model
class SecurityMetricsSummary(Base):
    """
    ORM Model for the security_metrics_summary view.
    Used for retrieving aggregate security data.
    """
    __tablename__ = "security_metrics_summary"
    
    # Views don't have PKs, but SQLAlchemy requires one
    # Using total_events_24h as a dummy PK since it's likely unique enough for reading
    total_events_24h = Column(Integer, primary_key=True)
    high_severity_events_24h = Column(Integer)
    blocked_attacks_24h = Column(Integer)
    failed_logins_24h = Column(Integer)
    active_blacklisted_ips = Column(Integer)
    active_firewall_rules = Column(Integer)


class SecurityMetricsResponse(BaseModel):
    threatLevel: str
    blockedAttacks: int
    failedLogins: int
    suspiciousActivity: int
    activeFirewallRules: int
    lastSecurityScan: str

    model_config = ConfigDict(from_attributes=True)
