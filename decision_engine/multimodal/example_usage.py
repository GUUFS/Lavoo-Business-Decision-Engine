"""
Example Usage Script for Multimodal Analysis

Demonstrates how to use the multimodal feature for business problem analysis.

Usage:
    python -m ai.multimodal.example_usage

Prerequisites:
    1. Install dependencies: uv add pillow pytesseract PyPDF2 pdfplumber python-docx cohere
    2. Install Tesseract OCR: sudo apt-get install tesseract-ocr (Ubuntu/WSL)
    3. Set COHERE_API_KEY environment variable (optional, for LLM enhancement)
"""

import logging
import os
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def example_1_single_image():
    """Example 1: Extract text from a single image."""
    from decision_engine.multimodal import ImageParser
    
    print("\n" + "="*60)
    print("EXAMPLE 1: Extract Text from Image")
    print("="*60)
    
    parser = ImageParser(ocr_lang="eng")
    
    # Example: Process a screenshot of business metrics
    # For testing, create a sample image or use an existing one
    image_path = Path("ai/multimodal/test_image.png")
    
    if not image_path.exists():
        print(f"⚠️  Test image not found: {image_path}")
        print("   Create a sample image with text to test this feature.")
        return
    
    result = parser.extract_text_from_file(image_path)
    
    if result["success"]:
        print(f"✅ Success! Extracted {len(result['text'])} characters")
        print(f"   Metadata: {result['metadata']}")
        print(f"\n--- Extracted Text (first 200 chars) ---")
        print(result['text'][:200])
    else:
        print(f"❌ Failed: {result['error']}")


def example_2_single_document():
    """Example 2: Extract text from a PDF document."""
    from decision_engine.multimodal import DocumentParser
    
    print("\n" + "="*60)
    print("EXAMPLE 2: Extract Text from Document (PDF)")
    print("="*60)
    
    parser = DocumentParser(prefer_pdfplumber=True)
    
    # Example: Process a business report PDF
    doc_path = Path("ai/multimodal/test_document.pdf")
    
    if not doc_path.exists():
        print(f"⚠️  Test document not found: {doc_path}")
        print("   Place a sample PDF in ai/multimodal/ to test this feature.")
        return
    
    result = parser.extract_text_from_file(doc_path)
    
    if result["success"]:
        print(f"✅ Success! Extracted {len(result['text'])} characters")
        print(f"   Metadata: {result['metadata']}")
        print(f"\n--- Extracted Text (first 200 chars) ---")
        print(result['text'][:200])
    else:
        print(f"❌ Failed: {result['error']}")


def example_3_multimodal_query():
    """Example 3: Process a multimodal query (text + image + document)."""
    from decision_engine.multimodal import MultimodalHandler
    
    print("\n" + "="*60)
    print("EXAMPLE 3: Multimodal Business Query")
    print("="*60)
    
    # Get xAI API key from environment
    xai_api_key = os.getenv("XAI_API_KEY")
    
    handler = MultimodalHandler(
        xai_api_key=xai_api_key,
        ocr_lang="eng",
        prefer_pdfplumber=True,
        use_vision_for_images=True  # Use Grok Vision instead of OCR
    )
    
    # Example business query
    user_query = """
    I'm a content creator struggling to scale my YouTube channel.
    My views have plateaued at 5K/video and I spend 10 hours editing each video.
    I've attached a screenshot of my analytics and a PDF of my content plan.
    What bottlenecks do you see and what can I do?
    """
    
    # Example files (use actual paths if available)
    image_files = ["ai/multimodal/test_image.png"] if Path("ai/multimodal/test_image.png").exists() else None
    document_files = ["ai/multimodal/test_document.pdf"] if Path("ai/multimodal/test_document.pdf").exists() else None
    
    if not image_files and not document_files:
        print("⚠️  No test files found. Processing text query only.")
    
    # Process the multimodal query
    result = handler.process_multimodal_query(
        user_query=user_query,
        image_files=image_files,
        document_files=document_files,
        enhance_with_llm=bool(xai_api_key)  # Only enhance if API key available
    )
    
    # Display results
    print(f"\n--- Results ---")
    print(f"Success: {result['success']}")
    print(f"Combined Context Length: {len(result['combined_context'])} chars")
    
    if result['extracted_content']['images']:
        print(f"\nImages Processed: {len(result['extracted_content']['images'])}")
    
    if result['extracted_content']['documents']:
        print(f"Documents Processed: {len(result['extracted_content']['documents'])}")
    
    if result['llm_analysis']:
        print(f"\n--- LLM Analysis ---")
        if result['llm_analysis'].get('success'):
            print(result['llm_analysis']['analysis'][:500])  # First 500 chars
        else:
            print(f"LLM analysis failed: {result['llm_analysis'].get('error')}")
    elif cohere_api_key:
        print("\n⚠️  LLM analysis skipped (xAI API issue?)")
    else:
        print("\n⚠️  LLM analysis skipped (XAI_API_KEY not set)")
    
    if result['errors']:
        print(f"\n❌ Errors encountered:")
        for error in result['errors']:
            print(f"   - {error}")


def example_4_bytes_processing():
    """Example 4: Process uploaded file bytes (simulates API endpoint)."""
    from decision_engine.multimodal import MultimodalHandler
    
    print("\n" + "="*60)
    print("EXAMPLE 4: Process File Bytes (Upload Simulation)")
    print("="*60)
    
    handler = MultimodalHandler()
    
    # Simulate file upload: Read a file as bytes
    test_file = Path("ai/multimodal/test_image.png")
    
    if not test_file.exists():
        print(f"⚠️  Test file not found: {test_file}")
        return
    
    # Read file as bytes (simulates uploaded file)
    with open(test_file, "rb") as f:
        file_bytes = f.read()
    
    # Process bytes
    result = handler.process_multimodal_query(
        user_query="What business metrics are shown in this image?",
        image_bytes_list=[(file_bytes, "uploaded_metrics.png")]
    )
    
    if result["success"]:
        print(f"✅ Successfully processed uploaded file")
        print(f"   Extracted: {len(result['combined_context'])} chars")
    else:
        print(f"❌ Failed to process uploaded file")
        if result['errors']:
            for error in result['errors']:
                print(f"   - {error}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("MULTIMODAL ANALYSIS - USAGE EXAMPLES")
    print("="*60)
    print("\nThese examples demonstrate the multimodal feature for")
    print("parsing images and documents to enhance business queries.")
    print("\nNote: This is a FUTURE FEATURE (not yet integrated with frontend)")
    
    # Check prerequisites
    print("\n--- Checking Prerequisites ---")
    
    try:
        from PIL import Image
        print("✅ PIL/Pillow installed")
    except ImportError:
        print("❌ PIL/Pillow not installed - Run: uv add pillow")
    
    try:
        import pytesseract
        print("✅ pytesseract installed")
        # Check if Tesseract OCR binary is available
        try:
            pytesseract.get_tesseract_version()
            print("   ✅ Tesseract OCR binary found")
        except:
            print("   ❌ Tesseract OCR binary not found - Install: sudo apt-get install tesseract-ocr")
    except ImportError:
        print("❌ pytesseract not installed - Run: uv add pytesseract")
    
    try:
        import PyPDF2
        print("✅ PyPDF2 installed")
    except ImportError:
        print("⚠️  PyPDF2 not installed - Run: uv add PyPDF2 (optional)")
    
    try:
        import docx
        print("✅ python-docx installed")
    except ImportError:
        print("⚠️  python-docx not installed - Run: uv add python-docx (optional)")
    
    if os.getenv("XAI_API_KEY"):
        print("✅ XAI_API_KEY found (Grok LLM/Vision enhancement available)")
    else:
        print("⚠️  XAI_API_KEY not set (Grok LLM/Vision enhancement disabled)")
    
    # Run examples
    try:
        example_1_single_image()
    except Exception as e:
        logger.error(f"Example 1 failed: {e}")
    
    try:
        example_2_single_document()
    except Exception as e:
        logger.error(f"Example 2 failed: {e}")
    
    try:
        example_3_multimodal_query()
    except Exception as e:
        logger.error(f"Example 3 failed: {e}")
    
    try:
        example_4_bytes_processing()
    except Exception as e:
        logger.error(f"Example 4 failed: {e}")
    
    print("\n" + "="*60)
    print("EXAMPLES COMPLETE")
    print("="*60)
    print("\nNext Steps:")
    print("1. Test with real business images/documents")
    print("2. Integrate with FastAPI endpoints when ready")
    print("3. Add frontend upload UI (Clinton's work)")
    print("4. Connect to existing agentic_analyzer.py flow")


if __name__ == "__main__":
    main()
