"""
AI Tool Recommender using pgvector for fast similarity search.
Uses sentence-transformers (local, free) + PostgreSQL HNSW index.
"""

import logging
import sys

from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.orm import Session

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class VectorToolRecommender:
    """
    AI Tool recommendation engine using pgvector similarity search.

    Features:
    - Uses sentence-transformers for query embeddings (384 dimensions, runs locally)
    - PostgreSQL pgvector with HNSW index for fast similarity search
    - Cosine similarity for ranking
    - No need for caching or API calls - everything is local/database
    """

    EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384-dimensional, runs locally

    def __init__(self, db_session: Session):
        """
        Initialize the recommender.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

        # Initialize sentence-transformers model (runs locally)
        self.model = SentenceTransformer(self.EMBEDDING_MODEL)
        logger.info(f"✅ VectorToolRecommender initialized with sentence-transformers ({self.model.get_sentence_embedding_dimension()}D) + pgvector")

    def _generate_query_embedding(self, query_text: str) -> list[float]:
        """
        Generate embedding for a search query using sentence-transformers.
        Runs locally - no API calls needed!

        Args:
            query_text: The search query text

        Returns:
            384-dimensional embedding vector
        """
        try:
            embedding = self.model.encode(query_text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise

    def recommend_tools(
        self,
        query: str,
        top_k: int = 5,
        category_filter: str = None,
        min_rating: float = None
    ) -> list[dict]:
        """
        Recommend AI tools based on semantic similarity using pgvector.

        Args:
            query: Natural language description of what the user needs
            top_k: Number of recommendations to return (default: 5)
            category_filter: Optional category filter (e.g., "Content Creation")
            min_rating: Optional minimum rating filter (e.g., 4.0)

        Returns:
            List of recommended tools with similarity scores
        """
        logger.info(f"🔍 Searching for tools matching: '{query}' (top {top_k})")

        # Step 1: Generate query embedding
        query_embedding = self._generate_query_embedding(query)

        # Step 2: Convert embedding to PostgreSQL vector format
        # Format: '[0.1, 0.2, 0.3]'
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        # Step 3: Build SQL query with pgvector similarity search
        # Uses cosine distance operator (<=>), HNSW index will be used automatically
        # NOTE: Can't use parameter binding for vector type, must format it directly
        # NOTE: No WHERE embedding IS NOT NULL filter - it prevents HNSW index usage!
        sql_query = text(f"""
            SELECT
                id,
                name,
                url,
                description,
                summary,
                main_category,
                sub_category,
                pricing,
                ratings,
                key_features,
                who_should_use as use_cases,
                1 - (embedding <=> '{embedding_str}'::vector) AS similarity_score
            FROM ai_tools
            WHERE (:category_filter IS NULL OR main_category = :category_filter)
                AND (:min_rating IS NULL OR ratings >= :min_rating)
            ORDER BY embedding <=> '{embedding_str}'::vector
            LIMIT :top_k
        """)

        # Step 4: Execute query
        try:
            result = self.db.execute(
                sql_query,
                {
                    "category_filter": category_filter,
                    "min_rating": min_rating,
                    "top_k": top_k
                }
            )

            # Step 4: Format results
            tools = []
            for row in result:
                tools.append({
                    "id": row.id,
                    "name": row.name,
                    "url": row.url,
                    "description": row.description,
                    "summary": row.summary,
                    "main_category": row.main_category,
                    "sub_category": row.sub_category,
                    "pricing": row.pricing,
                    "ratings": row.ratings,
                    "key_features": row.key_features,
                    "use_cases": row.use_cases,
                    "similarity_score": float(row.similarity_score),
                    "match_percentage": round(float(row.similarity_score) * 100, 1)
                })

            logger.info(f"✅ Found {len(tools)} matching tools")
            return tools

        except Exception as e:
            logger.error(f"Error executing pgvector similarity search: {e}")
            raise

    def find_similar_tools(
        self,
        tool_name: str,
        top_k: int = 5,
        exclude_self: bool = True
    ) -> list[dict]:
        """
        Find tools similar to a given tool (useful for "similar tools" feature).

        Args:
            tool_name: Name of the reference tool
            top_k: Number of similar tools to return
            exclude_self: Whether to exclude the reference tool from results

        Returns:
            List of similar tools with similarity scores
        """
        logger.info(f"🔍 Finding tools similar to: '{tool_name}'")

        # Get the reference tool's embedding
        ref_tool = self.db.execute(
            text("SELECT embedding FROM ai_tools WHERE name = :name AND embedding IS NOT NULL"),
            {"name": tool_name}
        ).first()

        if not ref_tool or not ref_tool.embedding:
            logger.warning(f"Tool '{tool_name}' not found or has no embedding")
            return []

        # Find similar tools using the reference embedding
        sql_query = text("""
            SELECT
                id,
                name,
                url,
                description,
                main_category,
                pricing,
                ratings,
                1 - (embedding <=> :ref_embedding::vector) AS similarity_score
            FROM ai_tools
            WHERE embedding IS NOT NULL
                AND (:exclude_self = FALSE OR name != :tool_name)
            ORDER BY embedding <=> :ref_embedding::vector
            LIMIT :top_k
        """)

        result = self.db.execute(
            sql_query,
            {
                "ref_embedding": str(ref_tool.embedding),
                "tool_name": tool_name,
                "exclude_self": exclude_self,
                "top_k": top_k
            }
        )

        tools = []
        for row in result:
            tools.append({
                "id": row.id,
                "name": row.name,
                "url": row.url,
                "description": row.description,
                "main_category": row.main_category,
                "pricing": row.pricing,
                "ratings": row.ratings,
                "similarity_score": float(row.similarity_score),
                "match_percentage": round(float(row.similarity_score) * 100, 1)
            })

        logger.info(f"✅ Found {len(tools)} similar tools")
        return tools

    def get_tools_by_category(
        self,
        category: str,
        limit: int = 10,
        sort_by: str = "ratings"
    ) -> list[dict]:
        """
        Get tools filtered by category (no embedding needed).

        Args:
            category: Main category to filter by
            limit: Maximum number of tools to return
            sort_by: Field to sort by ("ratings", "name", etc.)

        Returns:
            List of tools in the category
        """
        allowed_sort_fields = ["ratings", "name", "id"]
        if sort_by not in allowed_sort_fields:
            sort_by = "ratings"

        sql_query = text(f"""
            SELECT
                id, name, url, description, summary,
                main_category, sub_category, pricing, ratings,
                key_features, use_cases
            FROM ai_tools
            WHERE main_category = :category
            ORDER BY {sort_by} DESC
            LIMIT :limit
        """)

        result = self.db.execute(sql_query, {"category": category, "limit": limit})

        tools = []
        for row in result:
            tools.append({
                "id": row.id,
                "name": row.name,
                "url": row.url,
                "description": row.description,
                "summary": row.summary,
                "main_category": row.main_category,
                "sub_category": row.sub_category,
                "pricing": row.pricing,
                "ratings": row.ratings,
                "key_features": row.key_features,
                "use_cases": row.use_cases
            })

        return tools
