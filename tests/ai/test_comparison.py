import pytest
import logging
from ai.utils.comparison import compare_tools, get_tool

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestComparison:
    """Standard pytest tests for tool comparison utility."""
    
    def test_compare_tools_valid_pair(self):
        """Test comparing two valid tools (MagicTrips vs Monica)."""
        result = compare_tools('MagicTrips', 'Monica')
        assert isinstance(result, dict)
        assert 'MagicTrips' in result and 'Monica' in result
        assert 'pricing' in result['MagicTrips']
        assert 'rating' in result['MagicTrips']
        assert isinstance(result['MagicTrips']['rating'], float)
        assert 'App Integrations' in result['MagicTrips']  # ✓/✗ feature
        logger.info(f"✅ Valid pair test: {list(result.keys())}")
    
    def test_compare_tools_single_missing(self):
        """Test error handling when one tool is missing."""
        with pytest.raises(ValueError, match="One or both tools not found"):
            compare_tools('MagicTrips', 'NonExistentTool')
        logger.info("✅ Missing tool test: Raises ValueError")
    
    def test_get_tool_single(self):
        """Test get_tool returns dict for valid tool."""
        result = get_tool('MagicTrips')
        assert isinstance(result, dict)
        assert 'name' in result
        assert 'pricing' in result
        assert isinstance(result['ratings'], float)
        logger.info(f"✅ Get tool test: {result['name']} with rating {result['ratings']}")
    
    def test_get_tool_missing(self):
        """Test get_tool returns empty dict for missing tool."""
        result = get_tool('NonExistentTool')
        assert result == {}
        logger.info("✅ Missing tool lookup: Empty dict")

if __name__ == "__main__":
    pytest.main([__file__, "-s"])