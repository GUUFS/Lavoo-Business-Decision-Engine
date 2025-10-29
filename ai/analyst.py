# ai/analyst.py
import pandas as pd
import logging
from typing import Dict, List
import sys

# Set up logging (cloud-friendly: logs to stdout instead of file)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Output to console/stdout for cloud platforms
    ]
)
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
        user_role (str): User's role, industry, or need (e.g., "entrepreneur", "Technology", "Marketing")
    
    Returns:
        dict: SWOT analysis with lists of points
    """
    try:
        # Search for tools relevant to the user role across multiple columns
        # This makes it more flexible - works with industry, role, or category
        relevant_tools = df[
            df["who_should_use"].str.contains(user_role, case=False, na=False) |
            df["main_category"].str.contains(user_role, case=False, na=False) |
            df["sub_category"].str.contains(user_role, case=False, na=False) |
            df["description"].str.contains(user_role, case=False, na=False)
        ]
        
        # If still no matches, use top tools by category
        if relevant_tools.empty:
            logger.warning(f"No exact matches for '{user_role}', using general AI tools")
            relevant_tools = df.head(10)  # Use top 10 tools as fallback

        # Initialize SWOT
        swot = {
            "Strengths": [],
            "Weaknesses": [],
            "Opportunities": [],
            "Threats": []
        }

        # Analyze pros and cons (limit to avoid overwhelming output)
        for _, row in relevant_tools.head(8).iterrows():  # Limit to 8 tools
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
            
            # Threats from cons (different angle)
            if cons_list:
                swot["Threats"].append(f"{row['name']} limitation: {cons_list[0]}")

        # Remove duplicates and limit length
        for key in swot:
            # Remove duplicates, empty entries, and limit to 5 items each
            unique_items = list(dict.fromkeys([s.strip() for s in swot[key] if s.strip()]))[:5]
            swot[key] = unique_items

        logger.info(f"Generated SWOT for '{user_role}': {len(swot['Strengths'])} strengths, {len(swot['Weaknesses'])} weaknesses")
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