"""
Multimodal Handler Module

Main orchestrator for multimodal analysis. Combines image and document parsing
with Cohere LLM to provide enhanced business problem analysis.

Workflow:
    1. User submits text query + optional image/document
    2. Extract text from image/document
    3. Combine with user query
    4. Send to Cohere LLM for business analysis
    5. Return comprehensive business insights

Integration Points:
    - Cohere Command R 7B (model: command-r7b-12-2024) for analysis
    - Existing agentic_analyzer.py for business problem detection
    - Existing recommender_db.py for tool recommendations
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
from io import BytesIO
import base64

try:
    from xai_sdk import Client
    from xai_sdk.chat import user, image, system
    XAI_AVAILABLE = True
except ImportError:
    XAI_AVAILABLE = False
    logging.warning("xai-sdk not installed. Install with: uv add xai-sdk")

from .image_parser import ImageParser
from .document_parser import DocumentParser
from .config import EXTRACTION_CONFIG

logger = logging.getLogger(__name__)


class MultimodalHandler:
    """
    Handles multimodal business problem analysis.
    
    Combines text, images, and documents to provide comprehensive
    business insights using Grok LLM and Grok Vision.
    
    Attributes:
        image_parser (ImageParser): Image text extraction handler
        document_parser (DocumentParser): Document text extraction handler
        xai_client (Client): xAI SDK client for Grok models
    """
    
    def __init__(
        self, 
        xai_api_key: Optional[str] = None,
        ocr_lang: str = "eng",
        prefer_pdfplumber: bool = True,
        use_vision_for_images: bool = True
    ):
        """
        Initialize MultimodalHandler.
        
        Args:
            xai_api_key (str, optional): xAI API key for Grok LLM/Vision analysis
            ocr_lang (str): Language for OCR (default: 'eng')
            prefer_pdfplumber (bool): Prefer pdfplumber for PDF parsing
            use_vision_for_images (bool): Use Grok Vision instead of OCR for images
        """
        # Initialize parsers
        self.use_vision_for_images = use_vision_for_images
        
        try:
            self.image_parser = ImageParser(ocr_lang=ocr_lang)
            logger.info("ImageParser initialized successfully")
        except ImportError as e:
            logger.warning(f"ImageParser unavailable: {e}")
            self.image_parser = None
        
        try:
            self.document_parser = DocumentParser(prefer_pdfplumber=prefer_pdfplumber)
            logger.info("DocumentParser initialized successfully")
        except Exception as e:
            logger.warning(f"DocumentParser initialization issue: {e}")
            self.document_parser = DocumentParser(prefer_pdfplumber=False)
        
        # Initialize xAI client (for Grok LLM and Grok Vision)
        self.xai_client = None
        if xai_api_key and XAI_AVAILABLE:
            try:
                self.xai_client = Client(
                    api_key=xai_api_key,
                    timeout=3600  # Long timeout for reasoning models
                )
                logger.info("xAI Grok client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize xAI client: {e}")
        
        logger.info("MultimodalHandler initialized")
    
    def process_multimodal_query(
        self,
        user_query: str,
        image_files: Optional[List[Union[str, Path]]] = None,
        document_files: Optional[List[Union[str, Path]]] = None,
        image_bytes_list: Optional[List[tuple]] = None,  # [(bytes, filename), ...]
        document_bytes_list: Optional[List[tuple]] = None,  # [(bytes, filename), ...]
        enhance_with_llm: bool = False
    ) -> Dict:
        """
        Process a multimodal business query.
        
        Args:
            user_query (str): User's text query about business problem
            image_files (list, optional): List of image file paths
            document_files (list, optional): List of document file paths
            image_bytes_list (list, optional): List of (bytes, filename) tuples for images
            document_bytes_list (list, optional): List of (bytes, filename) tuples for docs
            enhance_with_llm (bool): Whether to enhance with Cohere LLM analysis
            
        Returns:
            dict: {
                'success': bool,
                'user_query': str (original query),
                'extracted_content': dict (from images/docs),
                'combined_context': str (query + extracted text),
                'llm_analysis': dict (if enhance_with_llm=True),
                'errors': list (any errors encountered)
            }
        """
        logger.info("Processing multimodal query")
        
        result = {
            "success": False,
            "user_query": user_query,
            "extracted_content": {
                "images": [],
                "documents": []
            },
            "combined_context": "",
            "llm_analysis": None,
            "errors": []
        }
        
        # Extract text from images
        if image_files or image_bytes_list:
            if self.use_vision_for_images and self.xai_client:
                # Use Grok Vision for image understanding
                result["extracted_content"]["images"] = self._process_images_with_vision(
                    image_files, image_bytes_list, user_query
                )
            elif not self.image_parser:
                result["errors"].append("ImageParser not available (install PIL and pytesseract)")
            else:
                result["extracted_content"]["images"] = self._process_images(
                    image_files, image_bytes_list
                )
        
        # Extract text from documents
        if document_files or document_bytes_list:
            result["extracted_content"]["documents"] = self._process_documents(
                document_files, document_bytes_list
            )
        
        # Combine all text context
        result["combined_context"] = self._combine_context(
            user_query,
            result["extracted_content"]
        )
        
        # Enhance with LLM if requested
        if enhance_with_llm:
            if not self.xai_client:
                result["errors"].append("xAI client not initialized (provide API key)")
            else:
                llm_result = self._analyze_with_llm(result["combined_context"])
                result["llm_analysis"] = llm_result
                # Add 'analysis' key for easier access to the actual analysis text
                if llm_result and llm_result.get("success"):
                    result["analysis"] = llm_result.get("analysis", "")
                else:
                    result["analysis"] = ""
        
        # Determine overall success
        result["success"] = len(result["combined_context"]) > 0 and len(result["errors"]) == 0
        
        logger.info(f"Multimodal processing complete: {len(result['combined_context'])} chars extracted")
        return result
    
    def _process_images(
        self,
        image_files: Optional[List[Union[str, Path]]],
        image_bytes_list: Optional[List[tuple]]
    ) -> List[Dict]:
        """Process all image inputs."""
        results = []
        
        # Process file paths
        if image_files:
            for img_path in image_files:
                try:
                    extraction = self.image_parser.extract_text_from_file(img_path)
                    results.append(extraction)
                    if not extraction["success"]:
                        logger.warning(f"Image extraction failed: {extraction.get('error')}")
                except Exception as e:
                    logger.error(f"Error processing image {img_path}: {e}")
                    results.append({"success": False, "error": str(e), "source": str(img_path)})
        
        # Process bytes
        if image_bytes_list:
            for img_bytes, filename in image_bytes_list:
                try:
                    extraction = self.image_parser.extract_text_from_bytes(img_bytes, filename)
                    results.append(extraction)
                    if not extraction["success"]:
                        logger.warning(f"Image bytes extraction failed: {extraction.get('error')}")
                except Exception as e:
                    logger.error(f"Error processing image bytes {filename}: {e}")
                    results.append({"success": False, "error": str(e), "source": filename})
        
        return results
    
    def _process_images_with_vision(
        self,
        image_files: Optional[List[Union[str, Path]]],
        image_bytes_list: Optional[List[tuple]],
        user_query: str = ""
    ) -> List[Dict]:
        """
        Process images using Grok Vision for direct image understanding.
        
        Args:
            image_files: List of image file paths
            image_bytes_list: List of (bytes, filename) tuples
            user_query: User's business query for context
            
        Returns:
            List of analysis results from Grok Vision
        """
        results = []
        
        # Process file paths
        if image_files:
            for img_path in image_files:
                try:
                    # Read image as base64
                    with open(img_path, "rb") as f:
                        img_bytes = f.read()
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    
                    # Analyze with Grok Vision
                    analysis = self._analyze_image_with_grok_vision(
                        img_base64,
                        Path(img_path).name,
                        user_query
                    )
                    results.append(analysis)
                except Exception as e:
                    logger.error(f"Error processing image {img_path} with Vision: {e}")
                    results.append({
                        "success": False,
                        "error": str(e),
                        "source": str(img_path),
                        "method": "grok-vision"
                    })
        
        # Process bytes
        if image_bytes_list:
            for img_bytes, filename in image_bytes_list:
                try:
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    analysis = self._analyze_image_with_grok_vision(
                        img_base64,
                        filename,
                        user_query
                    )
                    results.append(analysis)
                except Exception as e:
                    logger.error(f"Error processing image bytes {filename} with Vision: {e}")
                    results.append({
                        "success": False,
                        "error": str(e),
                        "source": filename,
                        "method": "grok-vision"
                    })
        
        return results
    
    def _analyze_image_with_grok_vision(
        self,
        image_base64: str,
        filename: str,
        user_query: str = ""
    ) -> Dict:
        """
        Analyze a single image using Grok Vision.
        
        Args:
            image_base64: Base64-encoded image
            filename: Image filename
            user_query: User's query for context
            
        Returns:
            dict: Analysis result from Grok Vision
        """
        if not self.xai_client:
            return {
                "success": False,
                "error": "xAI client not initialized",
                "source": filename
            }
        
        try:
            # Craft vision prompt
            vision_prompt = f"""Analyze this business-related image and extract all relevant information.

User's Business Context: {user_query if user_query else 'General business analysis'}

Please provide:
1. What you see in the image (charts, metrics, diagrams, text, etc.)
2. Key data points, numbers, or metrics visible
3. Business insights or patterns you observe
4. Any text content in the image

Be detailed and specific."""

            logger.info(f"Analyzing image {filename} with Grok Vision")
            
            # Create chat session with Grok Vision model
            # Using grok-4-1-fast-reasoning which supports vision
            chat = self.xai_client.chat.create(
                model="grok-4-1-fast-reasoning"  # Supports vision + reasoning
            )
            
            # Append user message with image
            # xai-sdk format: user(text, image(image_url=..., detail="high"))
            chat.append(
                user(
                    vision_prompt,
                    image(
                        image_url=f"data:image/jpeg;base64,{image_base64}",
                        detail="high"
                    )
                )
            )
            
            # Get response from Grok Vision
            response = chat.sample()
            vision_analysis = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"Grok Vision analysis complete for {filename}: {len(vision_analysis)} chars")
            
            return {
                "success": True,
                "text": vision_analysis,
                "method": "grok-vision",
                "metadata": {
                    "filename": filename,
                    "model": "grok-vision",
                    "char_count": len(vision_analysis)
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"Grok Vision analysis failed for {filename}: {e}", exc_info=True)
            return {
                "success": False,
                "text": "",
                "method": "grok-vision",
                "error": f"Vision analysis failed: {str(e)}",
                "metadata": {"filename": filename}
            }
    
    def _process_documents(
        self,
        document_files: Optional[List[Union[str, Path]]],
        document_bytes_list: Optional[List[tuple]]
    ) -> List[Dict]:
        """Process all document inputs."""
        results = []
        
        # Process file paths
        if document_files:
            for doc_path in document_files:
                try:
                    extraction = self.document_parser.extract_text_from_file(doc_path)
                    results.append(extraction)
                    if not extraction["success"]:
                        logger.warning(f"Document extraction failed: {extraction.get('error')}")
                except Exception as e:
                    logger.error(f"Error processing document {doc_path}: {e}")
                    results.append({"success": False, "error": str(e), "source": str(doc_path)})
        
        # Process bytes
        if document_bytes_list:
            for doc_bytes, filename in document_bytes_list:
                try:
                    extraction = self.document_parser.extract_text_from_bytes(doc_bytes, filename)
                    results.append(extraction)
                    if not extraction["success"]:
                        logger.warning(f"Document bytes extraction failed: {extraction.get('error')}")
                except Exception as e:
                    logger.error(f"Error processing document bytes {filename}: {e}")
                    results.append({"success": False, "error": str(e), "source": filename})
        
        return results
    
    def _combine_context(self, user_query: str, extracted_content: Dict) -> str:
        """
        Combine user query with extracted content into a single context string.
        
        Args:
            user_query (str): Original user query
            extracted_content (dict): Extracted text from images/documents
            
        Returns:
            str: Combined context for LLM analysis
        """
        context_parts = []
        
        # Add user query
        context_parts.append(f"# User Query\n{user_query}\n")
        
        # Add extracted image text
        if extracted_content["images"]:
            context_parts.append("# Extracted from Images")
            for idx, img_result in enumerate(extracted_content["images"], 1):
                if img_result.get("success") and img_result.get("text"):
                    metadata = img_result.get("metadata", {})
                    context_parts.append(
                        f"## Image {idx} ({metadata.get('filename', 'unknown')})\n"
                        f"{img_result['text']}\n"
                    )
        
        # Add extracted document text
        if extracted_content["documents"]:
            context_parts.append("# Extracted from Documents")
            for idx, doc_result in enumerate(extracted_content["documents"], 1):
                if doc_result.get("success") and doc_result.get("text"):
                    metadata = doc_result.get("metadata", {})
                    context_parts.append(
                        f"## Document {idx} ({metadata.get('filename', 'unknown')})\n"
                        f"{doc_result['text']}\n"
                    )
        
        combined = "\n".join(context_parts)
        
        # Truncate if too long (prevent token overflow)
        if len(combined) > EXTRACTION_CONFIG["max_text_length"]:
            logger.warning(f"Combined context too long ({len(combined)} chars), truncating")
            combined = combined[:EXTRACTION_CONFIG["max_text_length"]] + "\n\n... [context truncated]"
        
        return combined
    
    def _analyze_with_llm(self, context: str) -> Optional[Dict]:
        """
        Analyze combined context using Grok LLM.
        
        Args:
            context (str): Combined user query + extracted text
            
        Returns:
            dict: {
                'analysis': str (LLM analysis),
                'bottlenecks': list (detected bottlenecks),
                'recommendations': str (suggested solutions)
            }
        """
        if not self.xai_client:
            logger.error("xAI client not available")
            return None
        
        try:
            # Craft prompt for business analysis
            system_prompt = """You are an expert AI Business Analyst. Analyze the provided business 
problem (which may include text extracted from images/documents) and provide:

1. **Bottlenecks**: Key problems/challenges identified
2. **Solutions**: Practical solutions to address each bottleneck
3. **Roadmap**: Step-by-step action plan (max 3-5 steps)
4. **Tool Recommendations**: Suggest AI tools that could help (if applicable)

Be concise, actionable, and focus on practical business value."""
            
            logger.info("Sending request to Grok LLM (grok-4-1-fast-non-reasoning)")
            
            # Create chat session with Grok LLM
            chat = self.xai_client.chat.create(
                model="grok-4-1-fast-non-reasoning"  # Fast, non-reasoning model
            )
            
            # Add system prompt and user query
            chat.append(system(system_prompt))
            chat.append(user(context))
            
            # Get response from Grok LLM
            response = chat.sample()
            analysis_text = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"LLM analysis complete: {len(analysis_text)} chars")
            
            return {
                "analysis": analysis_text,
                "model": "grok-4-1-fast-non-reasoning",
                "success": True
            }
        
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}", exc_info=True)
            return {
                "analysis": "",
                "model": "grok-4-1-fast-non-reasoning",
                "success": False,
                "error": str(e)
            }
    
    def process_single_file(
        self,
        file_path: Union[str, Path],
        user_query: str = "",
        enhance_with_llm: bool = False
    ) -> Dict:
        """
        Convenience method to process a single file (image or document).
        
        Args:
            file_path (str | Path): Path to file
            user_query (str): Optional user query to combine with extracted text
            enhance_with_llm (bool): Whether to enhance with LLM
            
        Returns:
            dict: Same format as process_multimodal_query()
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        
        # Determine file type
        from .config import SUPPORTED_IMAGE_FORMATS, SUPPORTED_DOC_FORMATS
        
        if suffix in SUPPORTED_IMAGE_FORMATS:
            return self.process_multimodal_query(
                user_query=user_query,
                image_files=[file_path],
                enhance_with_llm=enhance_with_llm
            )
        elif suffix in SUPPORTED_DOC_FORMATS:
            return self.process_multimodal_query(
                user_query=user_query,
                document_files=[file_path],
                enhance_with_llm=enhance_with_llm
            )
        else:
            return {
                "success": False,
                "user_query": user_query,
                "error": f"Unsupported file format: {suffix}",
                "extracted_content": {"images": [], "documents": []},
                "combined_context": ""
            }
