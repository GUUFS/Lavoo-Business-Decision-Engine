# api/routes/analyzer_v2.py
"""
Business Analyzer API Routes v2
Uses the new AgenticAnalyzer for clean, modular analysis.
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from db.pg_connections import get_db
from db.pg_models import BusinessAnalysis
from api.routes.login import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/business", tags=["Business Analyzer v2"])


# =========================================================================
# REQUEST/RESPONSE MODELS
# =========================================================================
class AnalyzeRequest(BaseModel):
    """Request model for business analysis."""
    business_goal: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The business challenge or goal to analyze"
    )


class BottleneckResponse(BaseModel):
    """Bottleneck data structure."""
    id: int
    title: str
    description: str
    priority: str  # HIGH, MEDIUM, LOW
    impact: str


class StrategyResponse(BaseModel):
    """Strategy/action plan data structure."""
    id: int
    bottleneckId: int
    title: str
    description: str
    features: List[str] = []


class AIToolResponse(BaseModel):
    """AI tool recommendation data structure."""
    id: int
    bottleneckId: int
    title: str
    description: str
    price: str
    rating: str
    features: List[str] = []
    pros: List[str] = []
    cons: List[str] = []
    website: str


class AnalysisResponse(BaseModel):
    """Full analysis response matching frontend expectations."""
    analysis_id: int
    business_goal: str
    objective: str
    bottlenecks: List[Dict[str, Any]]
    business_strategies: List[Dict[str, Any]]
    ai_tools: List[Dict[str, Any]]
    roadmap: List[Dict[str, Any]]
    ai_confidence_score: int
    created_at: str
    key_evidence: Optional[List[Dict[str, Any]]] = []
    assumptions: Optional[List[str]] = []
    reasoning_trace: Optional[List[str]] = []


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================
def get_user_id(current_user) -> int:
    """Extract user ID from current_user (handles dict or object)."""
    if isinstance(current_user, dict):
        user_obj = current_user.get("user")
        return user_obj.id if user_obj else None
    return current_user.id


def parse_json_field(field_value, default=None):
    """Safely parse JSON field from database."""
    if field_value is None:
        return default if default is not None else []

    if isinstance(field_value, (list, dict)):
        return field_value

    if isinstance(field_value, str):
        try:
            return json.loads(field_value)
        except json.JSONDecodeError:
            return default if default is not None else []

    return default if default is not None else []


def format_analysis_for_frontend(analysis: BusinessAnalysis) -> Dict[str, Any]:
    """Transform database analysis to frontend format."""

    # Parse stored JSON fields
    bottlenecks = parse_json_field(analysis.bottlenecks, [])
    strategies = parse_json_field(analysis.business_strategies, [])
    ai_tools = parse_json_field(analysis.ai_tools, [])
    roadmap = parse_json_field(analysis.roadmap, [])
    key_evidence = parse_json_field(analysis.key_evidence, [])
    assumptions = parse_json_field(analysis.assumptions, [])
    reasoning_trace = parse_json_field(analysis.reasoning_trace, [])

    return {
        "analysis_id": analysis.id,
        "business_goal": analysis.business_goal or "",
        "objective": analysis.objective or "",
        "bottlenecks": bottlenecks,
        "business_strategies": strategies,
        "ai_tools": ai_tools,
        "roadmap": roadmap,
        "key_evidence": key_evidence,
        "assumptions": assumptions,
        "reasoning_trace": reasoning_trace,
        "ai_confidence_score": analysis.confidence_score or 85,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else "",
        "roi_metrics": None  # No ROI in v2
    }


# =========================================================================
# API ENDPOINTS
# =========================================================================
@router.post("/analyze", response_model=dict)
async def analyze_business_goal(
    request: AnalyzeRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyze business goal using the Agentic Analyzer.

    This endpoint triggers a 4-stage AI analysis:
    1. Intent & Bottleneck Analysis
    2. Tool Retrieval & Ranking
    3. Solution Strategy Generation
    4. Implementation Roadmap

    Returns complete analysis matching frontend expectations.
    """
    from ai.agentic_analyzer import create_analyzer

    try:
        user_id = get_user_id(current_user)
        logger.info(f"🚀 Starting agentic analysis for user {user_id}")

        # Create analyzer and run analysis
        analyzer = create_analyzer(db)
        result = await analyzer.analyze(
            user_query=request.business_goal,
            user_id=user_id
        )

        logger.info(f"✅ Analysis completed: ID {result['data']['analysis_id']}")

        return {
            "success": True,
            "message": "Analysis completed successfully",
            "data": result["data"]
        }

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/analyses")
async def get_user_analyses(
    limit: int = 10,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's previous business analyses.

    Query Parameters:
    - limit: Maximum number of analyses to return (default: 10)

    Returns list of analyses in frontend format.
    """
    try:
        user_id = get_user_id(current_user)
        logger.info(f"📋 Fetching analyses for user {user_id}, limit={limit}")

        analyses = (
            db.query(BusinessAnalysis)
            .filter(BusinessAnalysis.user_id == user_id)
            .order_by(BusinessAnalysis.created_at.desc())
            .limit(limit)
            .all()
        )

        logger.info(f"Found {len(analyses)} analyses for user {user_id}")

        # Transform to frontend format
        ui_analyses = []
        for analysis in analyses:
            try:
                ui_data = format_analysis_for_frontend(analysis)
                ui_analyses.append(ui_data)
            except Exception as e:
                logger.warning(f"Failed to format analysis {analysis.id}: {e}")
                continue

        return {
            "success": True,
            "count": len(ui_analyses),
            "data": ui_analyses
        }

    except Exception as e:
        logger.error(f"❌ Failed to fetch analyses: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch analyses: {str(e)}"
        )


@router.get("/analyses/{analysis_id}")
async def get_analysis_detail(
    analysis_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed view of a specific analysis.

    Path Parameters:
    - analysis_id: ID of the analysis to retrieve

    Returns complete analysis in frontend format.
    """
    try:
        user_id = get_user_id(current_user)

        analysis = (
            db.query(BusinessAnalysis)
            .filter(
                BusinessAnalysis.id == analysis_id,
                BusinessAnalysis.user_id == user_id
            )
            .first()
        )

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        ui_data = format_analysis_for_frontend(analysis)

        return {
            "success": True,
            "data": ui_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch analysis {analysis_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch analysis: {str(e)}"
        )


@router.delete("/analyses/{analysis_id}")
async def delete_analysis(
    analysis_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a specific analysis.

    Path Parameters:
    - analysis_id: ID of the analysis to delete
    """
    try:
        user_id = get_user_id(current_user)

        analysis = (
            db.query(BusinessAnalysis)
            .filter(
                BusinessAnalysis.id == analysis_id,
                BusinessAnalysis.user_id == user_id
            )
            .first()
        )

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        db.delete(analysis)
        db.commit()

        logger.info(f"🗑️ Deleted analysis {analysis_id} for user {user_id}")

        return {
            "success": True,
            "message": "Analysis deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete analysis {analysis_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete analysis: {str(e)}"
        )
