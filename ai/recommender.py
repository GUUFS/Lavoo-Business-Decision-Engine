# ai/recommender.py
import pandas as pd
import logging
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import sys
import os

# Set up logging (cloud-friendly: logs to stdout instead of file)
# This works on Render, Heroku, Railway, etc.
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
    logger.info("Successfully loaded ai_tools.csv")
except FileNotFoundError:
    logger.error("ai_tools.csv not found in ai/data/")
    raise
except Exception as e:
    logger.error(f"Error loading CSV: {str(e)}")
    raise

# Initialize the sentence-transformers model
try:
    model = SentenceTransformer("all-MiniLM-L6-v2")  # Lightweight, fine-tunable
    logger.info("SentenceTransformer model initialized")
except Exception as e:
    logger.error(f"Error initializing SentenceTransformer: {str(e)}")
    raise

# Generate embeddings
try:
    descriptions = df["description"].tolist()
    embeddings = model.encode(descriptions, convert_to_tensor=False)
    logger.info(f"Generated embeddings for {len(embeddings)} descriptions")
except Exception as e:
    logger.error(f"Error generating embeddings: {str(e)}")
    raise

# Recommendation function
def recommend_tools(user_query, top_k=4):
    """Recommend top_k AI tools based on cosine similarity with user query.
    
    Args:
        user_query (str): User input (e.g., "I need a travel planning tool")
        top_k (int): Number of recommendations to return (default: 4)
    
    Returns:
        list: List of dicts with tool_name, similarity_score, and description
    """
    try:
        # Generate embedding for user query
        query_embedding = model.encode([user_query], convert_to_tensor=False)[0]
        
        # Compute cosine similarity
        similarities = cosine_similarity([query_embedding], embeddings)[0]
        
        # Get top_k indices and scores
        top_indices = np.argsort(similarities)[::-1][:top_k]
        top_scores = [float(score) for score in similarities[top_indices]]
        
        # Map to tool details as dictionaries
        recommendations = [
            {
                "tool_name": df.iloc[i]["name"],
                "similarity_score": top_scores[idx],
                "description": df.iloc[i]["description"]
            }
            for idx, i in enumerate(top_indices)
        ]
        logger.info(f"Recommended tools for query '{user_query}': {recommendations}")
        return recommendations
    except Exception as e:
        logger.error(f"Error in recommend_tools: {str(e)}")
        raise

# Example usage
if __name__ == "__main__":
    # Test with a sample query
    query = "I need a travel planning tool"
    recs = recommend_tools(query)
    for rec in recs:
        print(f"Tool: {rec['tool_name']}, Similarity: {rec['similarity_score']:.4f}, "
              f"Description: {rec['description'][:50]}...")