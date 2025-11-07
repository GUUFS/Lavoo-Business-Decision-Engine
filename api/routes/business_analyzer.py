# api/routes/business_analyzer.py
"""
Business Analyzer API Routes
Handles business goal analysis and roadmap generation
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ai.business_analyzer import analyze_business
from db.pg_connections import get_db
from db.pg_models import BusinessAnalysisRequest, BusinessAnalysisResponse
from api.routes.login import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/business", tags=["Business Analyzer"])


@router.post("/analyze", response_model=dict)
async def analyze_business_goal(
    request: BusinessAnalysisRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze business goal and generate tool recommendations + roadmap.
    
    Workflow:
    1. User Query → Intent Analysis (AI)
    2. Tool Discovery (Database)
    3. Combination Logic (AI)
    4. Roadmap Generation (AI)
    5. Save & Return
    
    Example Request:
    ```json
    {
        "business_goal": "Grow my AI newsletter from 500 to 10,000 subscribers in 3 months"
    }
    ```
    
    Returns:
    - Complete analysis with intent, tool combos, and implementation roadmap
    """
    try:
        logger.info(f"Analyzing business goal for user {current_user.id}")
        
        # Validate input
        if not request.business_goal or len(request.business_goal.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Business goal must be at least 10 characters long"
            )
        
        # Run AI analysis
        analysis = await analyze_business(
            user_goal=request.business_goal,
            user_id=current_user.id,
            db=db
        )
        
        logger.info(f"Analysis completed: ID {analysis['analysis_id']}")
        
        return {
            "success": True,
            "message": "Analysis completed successfully",
            "data": analysis
        }
        
    except Exception as e:
        logger.error(f"Business analysis failed: {e}", exc_info=True)
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
    
    Returns:
    - List of previous analyses with summaries
    """
    from db.pg_models import BusinessAnalysis
    
    try:
        analyses = db.query(BusinessAnalysis).filter(
            BusinessAnalysis.user_id == current_user.id
        ).order_by(
            BusinessAnalysis.created_at.desc()
        ).limit(limit).all()
        
        return {
            "success": True,
            "count": len(analyses),
            "data": [
                {
                    "id": a.id,
                    "business_goal": a.business_goal,
                    "objective": a.intent_analysis.get("objective", ""),
                    "estimated_cost": a.estimated_cost,
                    "timeline_weeks": a.timeline_weeks,
                    "combinations_count": len(a.tool_combinations),
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in analyses
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch analyses: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analyses")


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
    
    Returns:
    - Complete analysis with all details
    """
    from db.pg_models import BusinessAnalysis
    
    try:
        analysis = db.query(BusinessAnalysis).filter(
            BusinessAnalysis.id == analysis_id,
            BusinessAnalysis.user_id == current_user.id
        ).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return {
            "success": True,
            "data": {
                "analysis_id": analysis.id,
                "business_goal": analysis.business_goal,
                "intent_analysis": analysis.intent_analysis,
                "tool_combinations": analysis.tool_combinations,
                "roadmap": analysis.roadmap,
                "estimated_cost": analysis.estimated_cost,
                "timeline_weeks": analysis.timeline_weeks,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch analysis detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysis")
