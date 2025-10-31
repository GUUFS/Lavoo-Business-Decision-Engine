# ai/recommender_db.py
"""
AI Tool Recommender using PostgreSQL database.
This replaces the CSV-based recommender with database queries.
"""

import pandas as pd
import logging
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import sys
from sqlalchemy.orm import Session
from typing import List, Dict

# Set up logging (cloud-friendly: logs to stdout)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize the sentence-transformers model
try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("SentenceTransformer model initialized")
except Exception as e:
    logger.error(f"Error initializing SentenceTransformer: {e}")
    raise


class AIToolRecommender:
    """
    AI Tool recommendation engine using PostgreSQL.
    Generates embeddings and finds similar tools based on semantic similarity.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize recommender with database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.tools_df = None
        self.embeddings = None
        self._load_tools()
    
    def _load_tools(self):
        """Load tools from database and generate embeddings."""
        from db.pg_models import AITool
        
        try:
            # Query all tools from database
            tools = self.db.query(AITool).all()
            
            if not tools:
                logger.warning("No tools found in database. Run migration script first.")
                self.tools_df = pd.DataFrame()
                self.embeddings = np.array([])
                return
            
            # Convert to DataFrame for easier processing
            tools_data = []
            for tool in tools:
                tools_data.append({
                    'id': tool.id,
                    'name': tool.name,
                    'description': tool.description,
                    'main_category': tool.main_category,
                    'sub_category': tool.sub_category,
                    'pricing': tool.pricing,
                    'ratings': tool.ratings,
                    'key_features': tool.key_features,
                    'pros': tool.pros,
                    'cons': tool.cons,
                    'who_should_use': tool.who_should_use,
                    'compatibility_integration': tool.compatibility_integration,
                })
            
            self.tools_df = pd.DataFrame(tools_data)
            logger.info(f"Loaded {len(self.tools_df)} tools from database")
            
            # Generate embeddings
            descriptions = self.tools_df['description'].tolist()
            self.embeddings = model.encode(descriptions, convert_to_tensor=False)
            logger.info(f"Generated embeddings for {len(self.embeddings)} tools")
            
        except Exception as e:
            logger.error(f"Error loading tools from database: {e}")
            raise
    
    def recommend(self, user_query: str, top_k: int = 5) -> List[Dict]:
        """
        Recommend top_k AI tools based on cosine similarity with user query.
        
        Args:
            user_query: User input describing their needs
            top_k: Number of recommendations to return
            
        Returns:
            List of dicts with tool_name, similarity_score, and description
        """
        try:
            if self.tools_df.empty:
                logger.warning("No tools available for recommendations")
                return []
            
            # Generate embedding for user query
            query_embedding = model.encode([user_query], convert_to_tensor=False)[0]
            
            # Compute cosine similarity
            similarities = cosine_similarity([query_embedding], self.embeddings)[0]
            
            # Get top_k indices and scores
            top_indices = np.argsort(similarities)[::-1][:top_k]
            top_scores = [float(score) for score in similarities[top_indices]]
            
            # Map to tool details
            recommendations = []
            for idx, i in enumerate(top_indices):
                tool = self.tools_df.iloc[i]
                recommendations.append({
                    "tool_name": tool["name"],
                    "similarity_score": top_scores[idx],
                    "description": tool["description"]
                })
            
            logger.info(f"Generated {len(recommendations)} recommendations for: '{user_query}'")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in recommend: {e}")
            raise
    
    def refresh(self):
        """Refresh tools from database (call after adding new tools)."""
        logger.info("Refreshing tool data from database...")
        self._load_tools()


# Global recommender instance (initialized when first needed)
_recommender_instance = None


def get_recommender(db_session: Session) -> AIToolRecommender:
    """
    Get or create recommender instance.
    Uses singleton pattern to avoid reloading embeddings.
    
    Args:
        db_session: Database session
        
    Returns:
        AIToolRecommender instance
    """
    global _recommender_instance
    
    if _recommender_instance is None:
        _recommender_instance = AIToolRecommender(db_session)
    
    return _recommender_instance


def recommend_tools(user_query: str, top_k: int = 5, db_session: Session = None) -> List[Dict]:
    """
    Convenience function for tool recommendations.
    
    Args:
        user_query: User input describing their needs
        top_k: Number of recommendations
        db_session: Database session (required)
        
    Returns:
        List of tool recommendations
    """
    if db_session is None:
        raise ValueError("Database session is required")
    
    recommender = get_recommender(db_session)
    return recommender.recommend(user_query, top_k)


# Example usage
if __name__ == "__main__":
    from db.pg_connections import SessionLocal
    
    print("Testing AI Tool Recommender with PostgreSQL...")
    
    session = SessionLocal()
    try:
        # Test recommendation
        query = "I need a travel planning tool"
        recs = recommend_tools(query, top_k=3, db_session=session)
        
        print(f"\nRecommendations for: '{query}'")
        print("-" * 70)
        for rec in recs:
            print(f"\n🔹 {rec['tool_name']}")
            print(f"   Score: {rec['similarity_score']:.4f}")
            print(f"   {rec['description'][:100]}...")
    
    finally:
        session.close()
