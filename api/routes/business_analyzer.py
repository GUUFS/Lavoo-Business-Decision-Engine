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
    db: Session = Depends(get_db),
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
        # Extract user_id from the current_user dict structure: {"user": User, "role": str}
        logger.debug(f"current_user type: {type(current_user)}, value: {current_user}")
        if isinstance(current_user, dict):
            user_obj = current_user.get("user")
            user_id = user_obj.id if user_obj else None
        else:
            user_id = current_user.id
        logger.info(f"Analyzing business goal for user {user_id}")

        # Validate input
        if not request.business_goal or len(request.business_goal.strip()) < 10:
            raise HTTPException(
                status_code=400, detail="Business goal must be at least 10 characters long"
            )

        # Run AI analysis
        analysis = await analyze_business(
            user_goal=request.business_goal, user_id=user_id, db=db
        )

        logger.info(f"Analysis completed: ID {analysis['analysis_id']}")

        return {"success": True, "message": "Analysis completed successfully", "data": analysis}

    except Exception as e:
        logger.error(f"Business analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/analyses")
async def get_user_analyses(
    limit: int = 10, current_user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get user's previous business analyses with full UI data.

    Query Parameters:
    - limit: Maximum number of analyses to return (default: 10)

    Returns:
    - List of previous analyses in UI format
    """
    from db.pg_models import BusinessAnalysis
    from ai.business_analyzer import BusinessAnalyzer

    try:
        # Extract user_id from the current_user dict structure: {"user": User, "role": str}
        if isinstance(current_user, dict):
            user_obj = current_user.get("user")
            user_id = user_obj.id if user_obj else None
        else:
            user_id = current_user.id

        logger.info(f"Fetching analyses for user {user_id}, limit={limit}")

        analyses = (
            db.query(BusinessAnalysis)
            .filter(BusinessAnalysis.user_id == user_id)
            .order_by(BusinessAnalysis.created_at.desc())
            .limit(limit)
            .all()
        )

        logger.info(f"Found {len(analyses)} analyses for user {user_id}")

        # Transform each analysis to UI format
        analyzer = BusinessAnalyzer(db)
        ui_analyses = []

        for idx, a in enumerate(analyses, 1):
            try:
                logger.info(f"Transforming analysis {idx}/{len(analyses)} (ID: {a.id})")

                # Load AI tools from database if available
                pre_generated_tools = a.ai_tools_data if hasattr(a, 'ai_tools_data') and a.ai_tools_data else None

                ui_data = await analyzer._transform_to_ui_format(
                    db=db,
                    analysis_id=a.id,
                    user_goal=a.business_goal,
                    intent_analysis=a.intent_analysis or {},
                    tool_combinations=a.tool_combinations or [],
                    roadmap=a.roadmap or [],
                    roi_projections=a.roi_projections or {},
                    skip_tool_generation=True,  # Skip slow LLM calls when loading history
                    pre_generated_tools=pre_generated_tools,  # Load from database
                )
                ui_analyses.append(ui_data)
                logger.info(f"✅ Successfully transformed analysis {a.id} (with {len(pre_generated_tools) if pre_generated_tools else 0} tools)")
            except Exception as e:
                logger.error(f"❌ Error transforming analysis {a.id}: {e}", exc_info=True)
                # Continue with other analyses even if one fails
                continue

        return {
            "success": True,
            "count": len(ui_analyses),
            "data": ui_analyses,
        }

    except Exception as e:
        logger.error(f"Failed to fetch analyses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch analyses: {str(e)}")


@router.get("/analyses/{analysis_id}")
async def get_analysis_detail(
    analysis_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get detailed view of a specific analysis.

    Path Parameters:
    - analysis_id: ID of the analysis to retrieve

    Returns:
    - Complete analysis with all details in UI format
    """
    from db.pg_models import BusinessAnalysis
    from ai.business_analyzer import BusinessAnalyzer

    try:
        # Extract user_id from the current_user dict structure: {"user": User, "role": str}
        if isinstance(current_user, dict):
            user_obj = current_user.get("user")
            user_id = user_obj.id if user_obj else None
        else:
            user_id = current_user.id

        analysis = (
            db.query(BusinessAnalysis)
            .filter(BusinessAnalysis.id == analysis_id, BusinessAnalysis.user_id == user_id)
            .first()
        )

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        # Transform to UI format
        analyzer = BusinessAnalyzer(db)

        # Load AI tools from database if available
        pre_generated_tools = analysis.ai_tools_data if hasattr(analysis, 'ai_tools_data') and analysis.ai_tools_data else None

        ui_data = await analyzer._transform_to_ui_format(
            db=db,
            analysis_id=analysis.id,
            user_goal=analysis.business_goal,
            intent_analysis=analysis.intent_analysis or {},
            tool_combinations=analysis.tool_combinations or [],
            roadmap=analysis.roadmap or [],
            roi_projections=analysis.roi_projections or {},
            skip_tool_generation=True,  # Skip slow LLM calls when loading from database
            pre_generated_tools=pre_generated_tools,  # Load from database
        )

        return {
            "success": True,
            "data": ui_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch analysis detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysis")
