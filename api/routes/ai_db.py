# api/routes/ai_db.py
"""
AI-related API routes using PostgreSQL database.
This replaces the CSV-based routes with database queries.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from ai.recommender_db import recommend_tools
from ai.analyst_db import analyze_business_needs
from ai.utils.comparison_db import compare_tools_db, get_tool
from db.pg_connections import get_db

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/recommend")
async def get_recommendations(
    query: str,
    top_k: int = 3,
    db: Session = Depends(get_db)
):
    """
    Get top_k AI tool recommendations based on user query.
    
    Args:
        query: User input describing their needs
        top_k: Number of recommendations (default: 3)
        db: Database session
    
    Returns:
        list: List of dicts with tool_name, similarity_score, and description
    """
    try:
        recommendations = recommend_tools(query, top_k, db_session=db)
        return recommendations
    except Exception as e:
        logger.error(f"Error in get_recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/analyze", response_model=Dict[str, List[str]])
async def get_business_analysis(
    user_role: str,
    db: Session = Depends(get_db)
):
    """
    Get business insights (SWOT) based on user role.
    
    Args:
        user_role: User's role or industry (e.g., "entrepreneur", "Technology")
        db: Database session
    
    Returns:
        dict: SWOT analysis with lists of points
    """
    try:
        analysis = analyze_business_needs(user_role, db_session=db)
        return analysis
    except Exception as e:
        logger.error(f"Error in get_business_analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/compare", response_model=Dict[str, Dict[str, Any]])
async def get_tool_comparison(
    tools: str,
    db: Session = Depends(get_db)
):
    """
    Compare up to 4 AI tools side-by-side.
    
    Args:
        tools: Comma-separated tool names (e.g., 'Monica,MagicTrips,Jasper')
        db: Database session
    
    Returns:
        dict: {tool_name: {Pricing, Rating, Use Cases, features...}}
    
    Raises:
        HTTPException: 400 if <2 or >4 tools, 404 if any tool missing
    """
    try:
        # Split and clean tool names
        tool_list = [t.strip() for t in tools.split(',') if t.strip()]
        num_tools = len(tool_list)
        
        if num_tools < 2 or num_tools > 4:
            logger.warning(f"Invalid tool count: {num_tools} (must be 2-4)")
            raise HTTPException(
                status_code=400,
                detail=f"Select 2-4 tools (got {num_tools})"
            )
        
        # Get comparison data from database
        comparison = compare_tools_db(tool_list, db_session=db)
        
        if not comparison:
            raise HTTPException(
                status_code=404,
                detail="No tools found for comparison"
            )
        
        logger.info(f"Compared {len(comparison)} tools successfully")
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_tool_comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/tools/search")
async def search_tools(
    query: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Search for tools by name, category, or description.
    
    Args:
        query: Search query
        limit: Maximum results (default: 10)
        db: Database session
    
    Returns:
        list: Matching tools
    """
    from db.pg_models import AITool
    
    try:
        search_pattern = f"%{query}%"
        
        tools = db.query(AITool).filter(
            (AITool.name.ilike(search_pattern)) |
            (AITool.description.ilike(search_pattern)) |
            (AITool.main_category.ilike(search_pattern))
        ).limit(limit).all()
        
        results = []
        for tool in tools:
            results.append({
                "id": tool.id,
                "name": tool.name,
                "description": tool.description,
                "category": tool.main_category,
                "rating": tool.ratings,
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Error in search_tools: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/tools/{tool_id}")
async def get_tool_details(
    tool_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific tool.
    
    Args:
        tool_id: Tool ID
        db: Database session
    
    Returns:
        dict: Tool details
    """
    from db.pg_models import AITool
    
    try:
        tool = db.query(AITool).filter(AITool.id == tool_id).first()
        
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
        
        return {
            "id": tool.id,
            "name": tool.name,
            "url": tool.url,
            "description": tool.description,
            "category": tool.main_category,
            "subcategory": tool.sub_category,
            "pricing": tool.pricing,
            "rating": tool.ratings,
            "features": tool.key_features,
            "pros": tool.pros,
            "cons": tool.cons,
            "who_should_use": tool.who_should_use,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_tool_details: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
