# db/pg_models.py
"""
PostgreSQL database models - works with both PostgreSQL and SQLite.
This file contains all ORM models for the application.
"""

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, ForeignKey, JSON, Boolean, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import VARCHAR

from .pg_connections import Base


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
    end_date = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="subscriptions")