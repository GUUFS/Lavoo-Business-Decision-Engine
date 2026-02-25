"""
Test Script for Multimodal Feature with Grok Vision & Grok LLM

Tests the multimodal analysis functionality using:
- Grok Vision (grok-vision) for image understanding
- Grok LLM (grok-4-1-fast-non-reasoning) for business analysis

Usage:
    python -m ai.multimodal.test_grok_integration

Prerequisites:
    - XAI_API_KEY environment variable set
    - Test images/documents in ai/multimodal/ folder (optional)
"""

import logging
import os
from pathlib import Path
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_grok_vision():
    """Test #1: Grok Vision image analysis"""
    print("\n" + "="*70)
    print("TEST 1: GROK VISION - Image Understanding")
    print("="*70)
    
    from decision_engine.multimodal import MultimodalHandler
    
    # Get API key
    xai_api_key = os.getenv("XAI_API_KEY")
    if not xai_api_key:
        print("❌ XAI_API_KEY not set. Cannot test Grok Vision.")
        print("   Set it with: export XAI_API_KEY='your-key-here'")
        return False
    
    # Initialize handler with vision enabled
    handler = MultimodalHandler(
        xai_api_key=xai_api_key,
        use_vision_for_images=True  # Enable Grok Vision
    )
    
    # Check if test image exists
    test_image = Path("ai/multimodal/test_image.png")
    if not test_image.exists():
        print(f"⚠️  No test image found at {test_image}")
        print("   Create a sample business image (chart, metrics, etc.) to test.")
        print("   Skipping image test...")
        return True
    
    # Test Grok Vision
    query = "Analyze the business metrics and insights from this image."
    
    try:
        result = handler.process_multimodal_query(
            user_query=query,
            image_files=[str(test_image)],
            enhance_with_llm=False  # Just test vision, not LLM
        )
        
        if result["success"]:
            print("✅ Grok Vision analyzed image successfully!")
            print(f"\n--- Vision Analysis (first 300 chars) ---")
            
            if result['extracted_content']['images']:
                img_result = result['extracted_content']['images'][0]
                if img_result.get('success'):
                    print(img_result['text'][:300])
                    print(f"\n   Model: {img_result['metadata']['model']}")
                    print(f"   Method: {img_result.get('method', 'unknown')}")
                else:
                    print(f"❌ Vision failed: {img_result.get('error')}")
                    return False
            
            return True
        else:
            print(f"❌ Processing failed: {result.get('errors')}")
            return False
            
    except Exception as e:
        logger.error(f"Grok Vision test failed: {e}", exc_info=True)
        print(f"❌ Exception: {e}")
        return False


def test_grok_llm():
    """Test #2: Grok LLM business analysis"""
    print("\n" + "="*70)
    print("TEST 2: GROK LLM - Business Problem Analysis")
    print("="*70)
    
    from decision_engine.multimodal import MultimodalHandler
    
    xai_api_key = os.getenv("XAI_API_KEY")
    if not xai_api_key:
        print("❌ XAI_API_KEY not set. Cannot test Grok LLM.")
        return False
    
    handler = MultimodalHandler(
        xai_api_key=xai_api_key,
        use_vision_for_images=False  # Disable vision for this test
    )
    
    # Test business query
    test_query = """
    I'm a SaaS founder with a B2B product. We have 100 users but struggling to grow.
    Current metrics:
    - Monthly churn: 8%
    - Conversion rate: 2%
    - Average deal size: $200/mo
    - Customer acquisition cost: $500
    
    What are my main bottlenecks and how do I fix them?
    """
    
    try:
        result = handler.process_multimodal_query(
            user_query=test_query,
            enhance_with_llm=True  # Test LLM analysis
        )
        
        if result["success"] and result["llm_analysis"]:
            llm_result = result["llm_analysis"]
            
            if llm_result.get("success"):
                print("✅ Grok LLM analysis successful!")
                print(f"\n--- LLM Analysis (first 500 chars) ---")
                print(llm_result['analysis'][:500])
                print(f"\n   Model: {llm_result['model']}")
                return True
            else:
                print(f"❌ LLM analysis failed: {llm_result.get('error')}")
                return False
        else:
            print(f"❌ Processing failed: {result.get('errors')}")
            return False
            
    except Exception as e:
        logger.error(f"Grok LLM test failed: {e}", exc_info=True)
        print(f"❌ Exception: {e}")
        return False


def test_grok_document_parsing():
    """Test #3: Document parsing + Grok LLM"""
    print("\n" + "="*70)
    print("TEST 3: DOCUMENT PARSING + GROK LLM ANALYSIS")
    print("="*70)
    
    from decision_engine.multimodal import MultimodalHandler
    
    xai_api_key = os.getenv("XAI_API_KEY")
    if not xai_api_key:
        print("❌ XAI_API_KEY not set. Skipping Grok test.")
        return True
    
    handler = MultimodalHandler(
        xai_api_key=xai_api_key
    )
    
    # Check for test document
    test_doc = Path("ai/multimodal/test_document.pdf")
    if not test_doc.exists():
        print(f"⚠️  No test document found at {test_doc}")
        print("   Skipping document test...")
        return True
    
    try:
        result = handler.process_multimodal_query(
            user_query="Extract and analyze the key business insights from this document.",
            document_files=[str(test_doc)],
            enhance_with_llm=True
        )
        
        if result["success"]:
            print("✅ Document parsed and analyzed successfully!")
            print(f"\n--- Combined Context (first 200 chars) ---")
            print(result['combined_context'][:200])
            
            if result["llm_analysis"] and result["llm_analysis"].get("success"):
                print(f"\n--- Grok Analysis (first 300 chars) ---")
                print(result["llm_analysis"]["analysis"][:300])
            
            return True
        else:
            print(f"❌ Failed: {result.get('errors')}")
            return False
            
    except Exception as e:
        logger.error(f"Document test failed: {e}", exc_info=True)
        print(f"❌ Exception: {e}")
        return False


def test_combined_multimodal():
    """Test #4: Image + Document + Grok LLM (full pipeline)"""
    print("\n" + "="*70)
    print("TEST 4: FULL MULTIMODAL PIPELINE (Image + Doc + Grok)")
    print("="*70)
    
    from decision_engine.multimodal import MultimodalHandler
    
    xai_api_key = os.getenv("XAI_API_KEY")
    if not xai_api_key:
        print("⚠️  XAI_API_KEY not set. Skipping combined test.")
        return True
    
    handler = MultimodalHandler(
        xai_api_key=xai_api_key,
        use_vision_for_images=True
    )
    
    test_image = Path("ai/multimodal/test_image.png")
    test_doc = Path("ai/multimodal/test_document.pdf")
    
    has_image = test_image.exists()
    has_doc = test_doc.exists()
    
    if not has_image and not has_doc:
        print("⚠️  No test files available. Skipping combined test.")
        return True
    
    query = "Analyze my business situation based on the attached materials."
    
    try:
        result = handler.process_multimodal_query(
            user_query=query,
            image_files=[str(test_image)] if has_image else None,
            document_files=[str(test_doc)] if has_doc else None,
            enhance_with_llm=True
        )
        
        if result["success"]:
            print("✅ Full pipeline executed successfully!")
            print(f"\n📊 Processing Summary:")
            print(f"   - Images processed: {len(result['extracted_content']['images'])}")
            print(f"   - Documents processed: {len(result['extracted_content']['documents'])}")
            print(f"   - Combined context: {len(result['combined_context'])} chars")
            print(f"   - LLM analysis: {'Yes' if result['llm_analysis'] else 'No'}")
            
            if result['llm_analysis'] and result['llm_analysis'].get('success'):
                print(f"\n--- Grok's Business Analysis (first 400 chars) ---")
                print(result['llm_analysis']['analysis'][:400])
            
            return True
        else:
            print(f"❌ Failed: {result.get('errors')}")
            return False
            
    except Exception as e:
        logger.error(f"Combined test failed: {e}", exc_info=True)
        print(f"❌ Exception: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("MULTIMODAL FEATURE - GROK INTEGRATION TESTS")
    print("Testing Grok Vision (image) + Grok LLM (analysis)")
    print("="*70)
    
    # Check prerequisites
    print("\n--- Prerequisites Check ---")
    
    xai_key = os.getenv("XAI_API_KEY")
    if xai_key:
        print(f"✅ XAI_API_KEY found ({xai_key[:8]}...)")
    else:
        print("❌ XAI_API_KEY not set!")
        print("   Set with: export XAI_API_KEY='your-key-here'")
        print("   Cannot run tests without API key.")
        return
    
    try:
        from decision_engine.multimodal import MultimodalHandler
        print("✅ Multimodal module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import multimodal module: {e}")
        return
    
    try:
        from xai_sdk import Client
        print("✅ xai-sdk installed")
    except ImportError:
        print("❌ xai-sdk not installed. Run: uv add xai-sdk")
        return
    
    # Run tests
    results = {}
    
    results["Grok Vision"] = test_grok_vision()
    results["Grok LLM"] = test_grok_llm()
    results["Document + LLM"] = test_grok_document_parsing()
    results["Full Pipeline"] = test_combined_multimodal()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:30s} {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Multimodal feature ready with Grok integration!")
    else:
        print("\n⚠️  Some tests failed. Check logs above for details.")


if __name__ == "__main__":
    main()
