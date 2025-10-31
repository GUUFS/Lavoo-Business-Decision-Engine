# ai/utils/comparison.py
import pandas as pd
import logging
from typing import Dict, Any
import sys
import os

# Set up logging (cloud-friendly: logs to stdout instead of file)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Output to console/stdout for cloud platforms
    ]
)
logger = logging.getLogger(__name__)

# Get the absolute path to the CSV file
# Go up two directories from utils/ to get to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH = os.path.join(BASE_DIR, "ai", "data", "ai_tools.csv")

# Load CSV
try:
    df = pd.read_csv(CSV_PATH)
    logger.info(f"Loaded CSV for comparison from {CSV_PATH}")
except Exception as e:
    logger.error(f"Error loading CSV for comparison: {str(e)}")
    raise

def get_tool(tool_name: str) -> Dict[str, Any]:
    """Get tool details by name from CSV."""
    tool_row = df[df['name'].str.contains(tool_name, case=False, na=False)]
    if tool_row.empty:
        logger.warning(f"Tool '{tool_name}' not found")
        return {}
    row = tool_row.iloc[0]
    
    # Parse ratings safely: Extract number after "Rated" (e.g., "Rated 4.5 out of 5" → 4.5)
    ratings_str = row['ratings']
    ratings_value = 0.0
    if ratings_str:
        try:
            # Split and take the second word (after "Rated")
            parts = ratings_str.split()
            if len(parts) >= 2:
                ratings_value = round(float(parts[1]), 1)
        except ValueError as ve:
            logger.warning(f"Failed to parse ratings '{ratings_str}': {ve}. Defaulting to 0.0")
            ratings_value = 0.0
    
    return {
        'name': row['name'],
        'pricing': row['pricing'],
        'ratings': ratings_value,  # Now a float (e.g., 0.0 or 3.857)
        'key_features': row['key_features'],
        'who_should_use': row['who_should_use'],
        'compatibility_integration': row['compatibility_integration'],
        'main_category': row['main_category'],
        'sub_category': row['sub_category']
    }

def infer_feature(key_features: str, keywords: list) -> bool:
    """Infer if tool has a feature based on keywords in key_features (rule-based)."""
    return any(keyword.lower() in key_features.lower() for keyword in keywords)

def compare_tools(tool1: str, tool2: str) -> Dict[str, Dict[str, str]]:
    """Compare two tools side-by-side (pricing, rating, features as ✓/✗)."""
    try:
        details1 = get_tool(tool1)
        details2 = get_tool(tool2)
        if not details1 or not details2:
            logger.error(f"Cannot compare: {tool1} or {tool2} not found")
            raise ValueError("One or both tools not found")

        # Infer features from key_features (matches your screenshot)
        features = {
            'App Integrations': (details1['compatibility_integration'], details2['compatibility_integration']),
            'Workflow Automation': (infer_feature(details1['key_features'], ['automation', 'workflow']), infer_feature(details2['key_features'], ['automation', 'workflow'])),
            'Triggers and Actions': (infer_feature(details1['key_features'], ['triggers', 'actions']), infer_feature(details2['key_features'], ['triggers', 'actions'])),
            'AI-powered Suggestions': (infer_feature(details1['key_features'], ['suggestions', 'recommendations']), infer_feature(details2['key_features'], ['suggestions', 'recommendations'])),
            'AI Writing Assistance': (infer_feature(details1['key_features'], ['writing', 'content']), infer_feature(details2['key_features'], ['writing', 'content'])),
            'Database Management': (infer_feature(details1['key_features'], ['database', 'data']), infer_feature(details2['key_features'], ['database', 'data'])),
            'Project Tracking': (infer_feature(details1['key_features'], ['project', 'track']), infer_feature(details2['key_features'], ['project', 'track'])),
            'Team Collaboration': (infer_feature(details1['key_features'], ['team', 'collaboration']), infer_feature(details2['key_features'], ['team', 'collaboration']))
        }

        comparison = {
            tool1: {
                'pricing': details1['pricing'],
                'rating': details1['ratings'],
                'technical_level': 'Intermediate',  # Hardcoded; add to CSV later if needed
                'use_cases': f"{details1['main_category']}, {details1['sub_category']}, {details1['who_should_use']}",
                **{k: '✓' if v[0] else '✗' for k, v in features.items()}
            },
            tool2: {
                'pricing': details2['pricing'],
                'rating': details2['ratings'],
                'technical_level': 'Intermediate',
                'use_cases': f"{details2['main_category']}, {details2['sub_category']}, {details2['who_should_use']}",
                **{k: '✓' if v[1] else '✗' for k, v in features.items()}
            }
        }
        logger.info(f"Compared {tool1} vs {tool2}: {list(comparison.keys())}")
        return comparison
    except Exception as e:
        logger.error(f"Comparison error: {str(e)}")
        raise
