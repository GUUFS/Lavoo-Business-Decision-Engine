import logging

from ai.recommender import recommend_tools

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestRecommender:
    """Standard pytest tests for AI tool recommender."""

    def test_recommend_tools_travel(self):
        """Test travel query returns MagicTrips as #1."""
        result = recommend_tools("travel planning tool", top_k=3)
        assert len(result) == 3
        assert result[0]["tool_name"] == "MagicTrips"
        assert 0.0 <= result[0]["similarity_score"] <= 1.0
        logger.info(
            f"✅ Travel test: {result[0]['tool_name']} (score: {result[0]['similarity_score']:.3f})"
        )

    def test_recommend_tools_empty_query(self):
        """Test empty query returns 3 results."""
        result = recommend_tools("", top_k=3)
        assert len(result) == 3
        assert all(0.0 <= r["similarity_score"] <= 1.0 for r in result)
        logger.info(f"✅ Empty query: {len(result)} results")

    def test_recommend_tools_top_k_variation(self):
        """Test different top_k values (1, 5)."""
        result1 = recommend_tools("AI tool", top_k=1)
        result5 = recommend_tools("AI tool", top_k=5)
        assert len(result1) == 1
        assert len(result5) == 5
        logger.info(f"✅ Top-k test: 1={len(result1)}, 5={len(result5)}")

    def test_recommend_tools_business_query(self):
        """Test business query returns relevant tools."""
        result = recommend_tools("business planning tool", top_k=3)
        business_tools = ["Anaplan", "AutoGPT", "MagicTrips"]
        assert any(tool in [r["tool_name"] for r in result] for tool in business_tools)
        logger.info(f"✅ Business test: {[r['tool_name'] for r in result]}")
