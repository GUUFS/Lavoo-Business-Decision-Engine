# ai/utils/comparison_db.py
"""
Tool comparison utilities using PostgreSQL database.
Compares AI tools side-by-side from database data.
"""

import logging
import sys
from typing import Any

from sqlalchemy.orm import Session

# Set up logging (cloud-friendly)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def get_tool(tool_name: str, db_session: Session) -> dict[str, Any]:
    """
    Get tool details by name from database.

    Args:
        tool_name: Name of the tool
        db_session: Database session

    Returns:
        dict: Tool details
    """
    from db.pg_models import AITool

    # Case-insensitive search
    tool = db_session.query(AITool).filter(AITool.name.ilike(f"%{tool_name}%")).first()

    if not tool:
        logger.warning(f"Tool '{tool_name}' not found")
        return {}

    return {
        "name": tool.name,
        "pricing": tool.pricing,
        "ratings": tool.ratings,
        "key_features": tool.key_features,
        "who_should_use": tool.who_should_use,
        "compatibility_integration": tool.compatibility_integration,
        "main_category": tool.main_category,
        "sub_category": tool.sub_category,
    }


def infer_feature(key_features: str, keywords: list) -> bool:
    """
    Infer if tool has a feature based on keywords.

    Args:
        key_features: Tool's key features string
        keywords: List of keywords to search for

    Returns:
        bool: True if any keyword found
    """
    if not key_features:
        return False

    return any(keyword.lower() in key_features.lower() for keyword in keywords)


def compare_tools_db(tool_names: list[str], db_session: Session) -> dict[str, dict[str, Any]]:
    """
    Compare multiple tools side-by-side from database.

    Args:
        tool_names: List of tool names (2-4 tools)
        db_session: Database session

    Returns:
        dict: Comparison data for each tool
    """
    try:
        comparison = {}

        for tool_name in tool_names:
            details = get_tool(tool_name, db_session)

            if not details:
                logger.error(f"Tool '{tool_name}' not found for comparison")
                continue

            # Infer features from key_features
            features = {
                "App Integrations": "Yes" if details["compatibility_integration"] else "No",
                "Workflow Automation": "Yes"
                if infer_feature(details["key_features"], ["automation", "workflow"])
                else "No",
                "Triggers and Actions": "Yes"
                if infer_feature(details["key_features"], ["triggers", "actions"])
                else "No",
                "AI-powered Suggestions": "Yes"
                if infer_feature(details["key_features"], ["suggestions", "recommendations"])
                else "No",
                "AI Writing": "Yes"
                if infer_feature(details["key_features"], ["writing", "content"])
                else "No",
                "Database": "Yes"
                if infer_feature(details["key_features"], ["database", "data"])
                else "No",
                "Project Tracking": "Yes"
                if infer_feature(details["key_features"], ["project", "track"])
                else "No",
                "Team Collaboration": "Yes"
                if infer_feature(details["key_features"], ["team", "collaboration"])
                else "No",
            }

            comparison[details["name"]] = {
                "Pricing": details["pricing"] or "N/A",
                "Rating": details["ratings"],
                "Technical Level": "Intermediate",  # Can be enhanced later
                "Use Cases": f"{details['main_category']}, {details['sub_category']}, {details['who_should_use']}",
                **features,
            }

        logger.info(f"Compared {len(comparison)} tools from database")
        return comparison

    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise


# Example usage
if __name__ == "__main__":
    from db.pg_connections import SessionLocal

    print("Testing Tool Comparison with PostgreSQL...")

    session = SessionLocal()
    try:
        tools = ["Monica", "MagicTrips"]
        comparison = compare_tools_db(tools, session)

        print(f"\nComparison of: {', '.join(tools)}")
        print("=" * 70)

        for tool_name, features in comparison.items():
            print(f"\n{tool_name}:")
            for key, value in features.items():
                print(f"  {key}: {value}")

    finally:
        session.close()
