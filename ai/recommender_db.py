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
import pickle
import os
from datetime import datetime, timedelta
import hashlib

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
    Includes caching for embeddings to improve performance.
    """
    
    # Cache settings
    CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
    EMBEDDINGS_CACHE_FILE = os.path.join(CACHE_DIR, "tool_embeddings.pkl")
    CACHE_VALIDITY_HOURS = 24  # Refresh cache every 24 hours
    
    def __init__(self, db_session: Session, use_cache: bool = True):
        """
        Initialize recommender with database session.
        
        Args:
            db_session: SQLAlchemy database session
            use_cache: Whether to use cached embeddings (default: True)
        """
        self.db = db_session
        self.tools_df = None
        self.embeddings = None
        self.use_cache = use_cache
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        
        self._load_tools()
    
    def _get_data_hash(self, tools_data: List[Dict]) -> str:
        """
        Generate hash of tool data to detect changes.
        
        Args:
            tools_data: List of tool dictionaries
            
        Returns:
            MD5 hash of the data
        """
        # Create a stable string representation of the data
        data_str = str(sorted([(t['id'], t['name'], t['description'][:50]) for t in tools_data]))
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _is_cache_valid(self) -> bool:
        """
        Check if cached embeddings are still valid.
        
        Returns:
            True if cache exists and is not expired
        """
        if not os.path.exists(self.EMBEDDINGS_CACHE_FILE):
            return False
        
        # Check file age
        cache_time = datetime.fromtimestamp(os.path.getmtime(self.EMBEDDINGS_CACHE_FILE))
        age = datetime.now() - cache_time
        
        if age > timedelta(hours=self.CACHE_VALIDITY_HOURS):
            logger.info(f"Cache expired (age: {age.total_seconds()/3600:.1f} hours)")
            return False
        
        logger.info(f"Cache is valid (age: {age.total_seconds()/3600:.1f} hours)")
        return True
    
    def _load_from_cache(self):
        """
        Load embeddings from cache file.
        
        Returns:
            Tuple of (tools_df, embeddings, data_hash) or None if cache invalid
        """
        try:
            with open(self.EMBEDDINGS_CACHE_FILE, 'rb') as f:
                cache_data = pickle.load(f)
            
            logger.info(f"✅ Loaded embeddings from cache ({len(cache_data['embeddings'])} tools)")
            return cache_data['tools_df'], cache_data['embeddings'], cache_data['data_hash']
        
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return None
    
    def _save_to_cache(self, tools_df, embeddings, data_hash):
        """
        Save embeddings to cache file.
        
        Args:
            tools_df: DataFrame of tools
            embeddings: Numpy array of embeddings
            data_hash: Hash of the data
        """
        try:
            cache_data = {
                'tools_df': tools_df,
                'embeddings': embeddings,
                'data_hash': data_hash,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.EMBEDDINGS_CACHE_FILE, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.info(f"💾 Saved embeddings to cache ({len(embeddings)} tools)")
        
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _load_tools(self):
        """
        Load tools from database and generate/load embeddings.
        Uses caching to avoid regenerating embeddings on every restart.
        """
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
            
            tools_df = pd.DataFrame(tools_data)
            logger.info(f"Loaded {len(tools_df)} tools from database")
            
            # Calculate data hash to detect changes
            current_hash = self._get_data_hash(tools_data)
            
            # Try to use cache if enabled
            if self.use_cache and self._is_cache_valid():
                cached_data = self._load_from_cache()
                
                if cached_data is not None:
                    cached_df, cached_embeddings, cached_hash = cached_data
                    
                    # Verify data hasn't changed
                    if cached_hash == current_hash and len(cached_df) == len(tools_df):
                        self.tools_df = tools_df  # Use fresh data from DB
                        self.embeddings = cached_embeddings  # Use cached embeddings
                        logger.info("🚀 Using cached embeddings (data unchanged)")
                        return
                    else:
                        logger.info("Data changed, regenerating embeddings...")
            
            # Generate new embeddings (cache miss or disabled)
            logger.info("Generating embeddings... (this may take a moment)")
            descriptions = tools_df['description'].tolist()
            embeddings = model.encode(descriptions, convert_to_tensor=False, show_progress_bar=True)
            
            self.tools_df = tools_df
            self.embeddings = embeddings
            
            logger.info(f"✅ Generated embeddings for {len(embeddings)} tools")
            
            # Save to cache for next time
            if self.use_cache:
                self._save_to_cache(tools_df, embeddings, current_hash)
            
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
    
    def refresh(self, clear_cache: bool = True):
        """
        Refresh tools from database (call after adding new tools).
        
        Args:
            clear_cache: Whether to clear the embedding cache (default: True)
        """
        logger.info("Refreshing tool data from database...")
        
        if clear_cache and os.path.exists(self.EMBEDDINGS_CACHE_FILE):
            os.remove(self.EMBEDDINGS_CACHE_FILE)
            logger.info("Cleared embedding cache")
        
        self._load_tools()
    
    def clear_cache(self):
        """Manually clear the embedding cache."""
        if os.path.exists(self.EMBEDDINGS_CACHE_FILE):
            os.remove(self.EMBEDDINGS_CACHE_FILE)
            logger.info("✅ Embedding cache cleared")
        else:
            logger.info("No cache to clear")


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
