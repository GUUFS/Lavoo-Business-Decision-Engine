# ai/analyst_db.py
"""
Business Analyst using PostgreSQL database.
Generates SWOT analysis from tool data in the database.
"""

import pandas as pd
import logging
from typing import Dict, List
import sys
from sqlalchemy.orm import Session

# Set up logging (cloud-friendly)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def analyze_business_needs(user_role: str, db_session: Session) -> Dict[str, List[str]]:
    """
    Generate business insights (SWOT) based on user role and tool data from database.
    
    Args:
        user_role: User's role, industry, or need (e.g., "entrepreneur", "Technology")
        db_session: Database session
    
    Returns:
        dict: SWOT analysis with lists of points
    """
    from db.pg_models import AITool
    
    try:
        # Query tools from database with flexible search
        # Search across multiple columns for better matching
        search_pattern = f"%{user_role}%"
        
        relevant_tools = db_session.query(AITool).filter(
            (AITool.who_should_use.ilike(search_pattern)) |
            (AITool.main_category.ilike(search_pattern)) |
            (AITool.sub_category.ilike(search_pattern)) |
            (AITool.description.ilike(search_pattern))
        ).limit(10).all()  # Limit to 10 tools
        
        # If no matches, get top general tools
        if not relevant_tools:
            logger.warning(f"No exact matches for '{user_role}', using general AI tools")
            relevant_tools = db_session.query(AITool).limit(10).all()
        
        # Convert to DataFrame for easier processing
        tools_data = []
        for tool in relevant_tools:
            tools_data.append({
                'name': tool.name,
                'main_category': tool.main_category,
                'who_should_use': tool.who_should_use,
                'pros': tool.pros,
                'cons': tool.cons,
            })
        
        df = pd.DataFrame(tools_data)
        
        # Initialize SWOT
        swot = {
            "Strengths": [],
            "Weaknesses": [],
            "Opportunities": [],
            "Threats": []
        }
        
        # Analyze pros and cons (limit to first 8 tools)
        for _, row in df.head(8).iterrows():
            # Strengths from pros (take first 2 per tool)
            pros_list = [p.strip() for p in str(row["pros"]).split("|") if p.strip()][:2]
            swot["Strengths"].extend([f"{row['name']}: {p}" for p in pros_list])
            
            # Weaknesses from cons (take first 2 per tool)
            cons_list = [c.strip() for c in str(row["cons"]).split("|") if c.strip()][:2]
            swot["Weaknesses"].extend([f"{row['name']}: {c}" for c in cons_list])
            
            # Opportunities from category and use cases
            swot["Opportunities"].append(
                f"Leverage {row['name']} for {row['main_category']} - ideal for {str(row['who_should_use'])[:100]}"
            )
            
            # Threats from cons
            if cons_list:
                swot["Threats"].append(f"{row['name']} limitation: {cons_list[0]}")
        
        # Remove duplicates and limit length
        for key in swot:
            unique_items = list(dict.fromkeys([s.strip() for s in swot[key] if s.strip()]))[:5]
            swot[key] = unique_items
        
        logger.info(f"Generated SWOT for '{user_role}': {len(swot['Strengths'])} strengths")
        return swot
        
    except Exception as e:
        logger.error(f"Error in analyze_business_needs: {e}")
        raise


# Example usage
if __name__ == "__main__":
    from db.pg_connections import SessionLocal
    
    print("Testing Business Analyst with PostgreSQL...")
    
    session = SessionLocal()
    try:
        role = "entrepreneur"
        analysis = analyze_business_needs(role, session)
        
        print(f"\nSWOT Analysis for: '{role}'")
        print("=" * 70)
        for category, points in analysis.items():
            print(f"\n{category}:")
            for point in points:
                print(f"  • {point}")
    
    finally:
        session.close()
