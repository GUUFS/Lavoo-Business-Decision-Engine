# api/routes/ai.py
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from ai.recommender import recommend_tools
from ai.analyst import analyze_business_needs
from ai.utils.comparison import compare_tools, get_tool, infer_feature

import logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/recommend")
async def get_recommendations(query: str, top_k: int = 3):
    """Get top_k AI tool recommendations based on a user query.
    
    Args:
        query (str): User input describing their needs
        top_k (int): Number of recommendations (default: 3)
    
    Returns:
        list: List of dicts with tool_name, similarity_score, and description
    """
    try:
        recommendations = recommend_tools(query, top_k)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/analyze", response_model=Dict[str, List[str]])
async def get_business_analysis(user_role: str):
    """Get business insights (SWOT) based on user role.
    
    Args:
        user_role (str): User’s role or need (e.g., "entrepreneur")
    
    Returns:
        dict: SWOT analysis with lists of points
    """
    try:
        analysis = analyze_business_needs(user_role)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/compare", response_model=Dict[str, Dict[str, Any]])
async def get_tool_comparison(tools: str):
    """Compare up to 4 AI tools side-by-side (pricing, rating, features as ✓/✗).
    
    Args:
        tools (str): Comma-separated tool names (e.g., 'MagicTrips,Monica,Anaplan' for 3 tools).
                     Min 2, max 4; case-insensitive lookup.
    
    Returns:
        dict: {tool_name: {pricing: str, rating: float, use_cases: str, App Integrations: '✓' or '✗', ...}}
    
    Raises:
        HTTPException: 400 if <2 or >4 tools, 404 if any tool missing, 500 for other errors
    """
    try:
        # Split and clean tools
        tool_list = [t.strip() for t in tools.split(',') if t.strip()]
        num_tools = len(tool_list)
        if num_tools < 2 or num_tools > 4:
            logger.warning(f"Invalid tool count: {num_tools} (must be 2-4)")
            raise HTTPException(status_code=400, detail=f"Select 2-4 tools (got {num_tools})")

        # Compare all (grid-style: each tool gets its own features dict)
        comparison = {}
        for tool_name in tool_list:
            details = get_tool(tool_name)
            if not details:
                logger.warning(f"Tool '{tool_name}' not found in comparison")
                raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
            
            # Infer features for this tool (same as before)
            features = {
                'App Integrations': 'Yes' if details['compatibility_integration'] else 'No',
                'Workflow Automation': 'Yes' if infer_feature(details['key_features'], ['automation', 'workflow']) else 'No',
                'Triggers and Actions': 'Yes' if infer_feature(details['key_features'], ['triggers', 'actions']) else 'No',
                'AI-powered Suggestions': 'Yes' if infer_feature(details['key_features'], ['suggestions', 'recommendations']) else 'No',
                'AI Writing': 'Yes' if infer_feature(details['key_features'], ['writing', 'content']) else 'No',
                'Database': 'Yes' if infer_feature(details['key_features'], ['database', 'data']) else 'No',
                'Project Tracking': 'Yes' if infer_feature(details['key_features'], ['project', 'track']) else 'No',
                'Team Collaboration': 'Yes' if infer_feature(details['key_features'], ['team', 'collaboration']) else 'No'
            }
            
            comparison[details['name']] = {
                'Pricing': details['pricing'],  # Capitalized to match frontend
                'Rating': details['ratings'],
                'Technical Level': 'Intermediate',  # Hardcoded; extend CSV later
                'Use Cases': f"{details['main_category']}, {details['sub_category']}, {details['who_should_use']}",
                **features
            }
        
        logger.info(f"API comparison: {num_tools} tools - Success: {list(comparison.keys())}")
        return comparison
    except HTTPException:
        raise  # Re-raise HTTP errors
    except Exception as e:
        logger.error(f"API comparison error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")