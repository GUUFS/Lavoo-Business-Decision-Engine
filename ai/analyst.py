# ai/analyst.py
import pandas as pd
import logging
from typing import Dict, List

# Set up logging
logging.basicConfig(filename="ai/logs/ai.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load the CSV
try:
    df = pd.read_csv("ai/data/ai_tools.csv")
    logger.info("Successfully loaded ai_tools.csv for analyst")
except FileNotFoundError:
    logger.error("ai_tools.csv not found in ai/data/")
    raise
except Exception as e:
    logger.error(f"Error loading CSV: {str(e)}")
    raise

# Business analyst function
def analyze_business_needs(user_role: str) -> Dict[str, List[str]]:
    """Generate business insights (SWOT) based on user role and tool data.
    
    Args:
        user_role (str): User’s role or need (e.g., "entrepreneur", "student")
    
    Returns:
        dict: SWOT analysis with lists of points
    """
    try:
        # Filter tools relevant to the user role
        relevant_tools = df[df["who_should_use"].str.contains(user_role, case=False, na=False)]
        if relevant_tools.empty:
            logger.warning(f"No tools found for role '{user_role}'")
            return {"Strengths": [], "Weaknesses": [], "Opportunities": [], "Threats": []}

        # Initialize SWOT
        swot = {
            "Strengths": [],
            "Weaknesses": [],
            "Opportunities": [],
            "Threats": []
        }

        # Analyze pros and cons
        for _, row in relevant_tools.iterrows():
            # Strengths from pros
            swot["Strengths"].extend([f"{row['name']}: {p}" for p in row["pros"].split("|") if p])
            # Weaknesses from cons
            swot["Weaknesses"].extend([f"{row['name']}: {c}" for c in row["cons"].split("|") if c])
            # Opportunities from who_should_use (e.g., new markets)
            swot["Opportunities"].append(f"{row['name']} opens opportunities for {row['who_should_use']}")
            # Threats from cons (e.g., limitations)
            swot["Threats"].extend([f"{row['name']} risk: {c}" for c in row["cons"].split("|") if c])

        # Remove duplicates and empty entries
        for key in swot:
            swot[key] = list(dict.fromkeys([s.strip() for s in swot[key] if s.strip()]))

        logger.info(f"Generated SWOT for role '{user_role}': {swot}")
        return swot
    except Exception as e:
        logger.error(f"Error in analyze_business_needs: {str(e)}")
        raise

# Example usage
if __name__ == "__main__":
    # Test with a sample role
    role = "graphic designer"
    analysis = analyze_business_needs(role)
    for category, points in analysis.items():
        print(f"{category}:")
        for point in points:
            print(f"  - {point}")