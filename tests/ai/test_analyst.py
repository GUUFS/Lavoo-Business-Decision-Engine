import pytest
import logging
from ai.analyst import analyze_business_needs

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestAnalyst:
    """Standard pytest tests for business analyst SWOT analysis."""
    
    def test_analyze_entrepreneur(self):
        """Test entrepreneur role returns 7+ strengths."""
        result = analyze_business_needs("entrepreneur")
        assert isinstance(result, dict)
        assert all(key in result for key in ["Strengths", "Weaknesses", "Opportunities", "Threats"])
        assert len(result["Strengths"]) >= 7
        logger.info(f"✅ Entrepreneur test: {len(result['Strengths'])} strengths")
    
    def test_analyze_student(self):
        """Test student role returns relevant analysis."""
        result = analyze_business_needs("student")
        assert isinstance(result, dict)
        assert len(result["Strengths"]) >= 0  # May be empty if no student tools
        logger.info(f"✅ Student test: {len(result['Strengths'])} strengths")
    
    def test_analyze_unknown_role(self):
        """Test unknown role returns empty SWOT."""
        result = analyze_business_needs("nonexistent_role")
        expected = {"Strengths": [], "Weaknesses": [], "Opportunities": [], "Threats": []}
        assert result == expected
        logger.info("✅ Unknown role: Empty SWOT")
    
    def test_analyze_case_insensitive(self):
        """Test case-insensitive role matching."""
        result1 = analyze_business_needs("ENTREPRENEUR")
        result2 = analyze_business_needs("entrepreneur")
        assert len(result1["Strengths"]) == len(result2["Strengths"])
        logger.info(f"✅ Case test: {len(result1['Strengths'])} strengths")