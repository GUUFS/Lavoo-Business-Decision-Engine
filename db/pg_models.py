# db/pg_models.py
"""
PostgreSQL database models - works with both PostgreSQL and SQLite.
This file contains all ORM models for the application.
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel, ConfigDict
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
