# ai/agentic_analyzer.py
"""
LAVOO Agentic Business Analyzer
A clean, modular agentic workflow for business analysis.

Architecture:
- Stage 1: Intent & Bottleneck Agent (understands user problem)
- Stage 2: Tool Retrieval Agent (finds and ranks best tools)
- Stage 3: Solution Strategy Agent (creates action plans)
- Stage 4: Roadmap Implementation Agent (execution timeline)

No ROI calculations - focuses on actionable insights.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv('.env.local')

# Import OpenAI SDK for xAI Grok API
try:
    from openai import OpenAI
    HAS_XAI = True
except ImportError:
    HAS_XAI = False
    print("Warning: openai package not installed. Install with: uv pip install openai")

logger = logging.getLogger(__name__)


class AgenticAnalyzer:
    """
    Modular agentic business analyzer with 4 specialized agents.
    Each agent has a specific role and passes structured data to the next.
    """

    def __init__(self, db_session: Session):
        """
        Initialize the agentic analyzer.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.model = "grok-3-fast"  # Fast model for production
        self.reasoning_model = "grok-3-mini-fast"  # Mini model for simpler tasks

        # Initialize xAI client
        if HAS_XAI:
            api_key = os.getenv("XAI_API_KEY")
            if not api_key:
                logger.warning("XAI_API_KEY not set")
                self.client = None
            else:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.x.ai/v1",
                    timeout=120.0
                )
                logger.info("xAI Grok client initialized for agentic analysis")
        else:
            self.client = None

    async def analyze(self, user_query: str, user_id: int) -> Dict[str, Any]:
        """
        Main analysis pipeline - orchestrates all 4 agents.

        Args:
            user_query: User's business challenge/goal
            user_id: Current user ID

        Returns:
            Complete analysis matching frontend expectations
        """
        logger.info(f"Starting agentic analysis for user {user_id}")
        start_time = datetime.now()

        try:
            # STAGE 1: Intent & Bottleneck Agent
            logger.info("🔍 Stage 1: Analyzing intent and bottlenecks...")
            intent_result = await self._stage1_intent_agent(user_query)

            # STAGE 2: Tool Retrieval Agent
            logger.info("🛠️ Stage 2: Retrieving and ranking tools...")
            tools_result = await self._stage2_tool_agent(
                intent_result["bottlenecks"],
                user_query
            )

            # STAGE 3: Solution Strategy Agent
            logger.info("💡 Stage 3: Generating solution strategies...")
            strategies_result = await self._stage3_solution_agent(
                intent_result,
                tools_result
            )

            # STAGE 4: Roadmap Implementation Agent
            logger.info("🗺️ Stage 4: Creating implementation roadmap...")
            roadmap_result = await self._stage4_roadmap_agent(
                strategies_result,
                tools_result
            )

            # Calculate analysis duration
            duration_seconds = (datetime.now() - start_time).total_seconds()

            # Save to database
            analysis_id = await self._save_to_database(
                user_id=user_id,
                user_query=user_query,
                intent_result=intent_result,
                tools_result=tools_result,
                strategies_result=strategies_result,
                roadmap_result=roadmap_result,
                duration=duration_seconds
            )

            # Format for frontend
            response = self._format_for_frontend(
                analysis_id=analysis_id,
                user_query=user_query,
                intent_result=intent_result,
                tools_result=tools_result,
                strategies_result=strategies_result,
                roadmap_result=roadmap_result
            )

            logger.info(f"✅ Analysis complete in {duration_seconds:.1f}s")
            return response

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise

    # =========================================================================
    # STAGE 1: INTENT & BOTTLENECK AGENT
    # =========================================================================
    async def _stage1_intent_agent(self, user_query: str) -> Dict[str, Any]:
        """
        Stage 1: Understand the user's intent and identify THE primary bottleneck.

        This agent acts as a business consultant to:
        - Extract the TRUE underlying objective
        - Identify THE ONE most critical bottleneck blocking success
        - Generate supporting evidence/signals

        Returns:
            {
                "objective": "Clear, measurable goal",
                "bottlenecks": [single primary bottleneck],
                "key_evidence": [...],
                "assumptions": [...],
                "reasoning_trace": [...]
            }
        """
        system_prompt = """You are the LAVOO Intent & Bottleneck Agent — a McKinsey-level business diagnostician.

Your job is to:
1. Deeply understand the user's business challenge
2. Extract their TRUE underlying objective (not surface-level)
3. Identify THE SINGLE most critical bottleneck blocking their success
4. Provide key evidence/signals supporting your diagnosis

IMPORTANT: Return ONLY ONE bottleneck - the primary root cause blocking everything else.

OUTPUT FORMAT (strict JSON):
{
    "objective": "One clear, specific, measurable goal that reflects what they REALLY need",
    "bottlenecks": [
        {
            "id": 1,
            "title": "5-8 word diagnostic title",
            "description": "80-120 char description with context and impact",
            "priority": "HIGH",
            "impact": "Specific business impact statement"
        }
    ],
    "key_evidence": [
        {
            "id": 1,
            "type": "Signal|Pattern|Gap|Risk",
            "title": "Evidence title",
            "description": "Why this matters to the diagnosis"
        }
    ],
    "assumptions": [
        "Assumption 1 about missing data or context",
        "Assumption 2..."
    ],
    "reasoning_trace": [
        "Step 1: How you analyzed the problem",
        "Step 2: Key insight discovered",
        "Step 3: Why this diagnosis is correct"
    ],
    "confidence_score": 85
}

BOTTLENECK RULES:
- Title: 5-8 words, punchy, diagnostic (implies risk/leak/constraint)
- Description: Include context, impact, and metric if possible
- Priority: HIGH = blocks everything, MEDIUM = significant friction, LOW = optimization opportunity
- Impact: Specific consequence (revenue, time, growth, etc.)

Be specific. Be actionable. No generic advice."""

        user_prompt = f"""Analyze this business challenge and provide your diagnosis:

USER QUERY: {user_query}

Remember: Output ONLY valid JSON. No markdown, no explanation outside JSON."""

        response = await self._call_llm(system_prompt, user_prompt, self.model)
        return self._parse_json_response(response, "stage1_intent")

    # =========================================================================
    # STAGE 2: TOOL RETRIEVAL AGENT
    # =========================================================================
    async def _stage2_tool_agent(
        self,
        bottlenecks: List[Dict],
        user_query: str
    ) -> Dict[str, Any]:
        """
        Stage 2: Retrieve and rank the best AI tools for each bottleneck.

        Uses:
        - Semantic search (embeddings) for initial retrieval
        - LLM for intelligent ranking and filtering

        Returns:
            {
                "tool_recommendations": [
                    {
                        "bottleneck_id": 1,
                        "tools": [ranked tools with summaries]
                    }
                ]
            }
        """
        from ai.recommender_db import get_recommender
        from db.pg_models import AITool as AIToolModel

        # Get recommender for semantic search
        recommender = get_recommender(self.db)

        tool_recommendations = []

        for bottleneck in bottlenecks:
            # Build search query from bottleneck
            search_query = f"{bottleneck['title']} {bottleneck['description']} {user_query}"

            # Get candidate tools via semantic search
            candidates = recommender.recommend(search_query, top_k=8)

            if not candidates:
                tool_recommendations.append({
                    "bottleneck_id": bottleneck["id"],
                    "tools": []
                })
                continue

            # Get full tool details from database
            candidate_tools = []
            for candidate in candidates:
                tool = self.db.query(AIToolModel).filter(
                    AIToolModel.name == candidate["tool_name"]
                ).first()

                if tool:
                    candidate_tools.append({
                        "name": tool.name,
                        "description": tool.description[:300] if tool.description else "",
                        "pricing": tool.pricing or "Contact for pricing",
                        "key_features": tool.key_features or "",
                        "pros": tool.pros or "",
                        "cons": tool.cons or "",
                        "similarity_score": candidate["similarity_score"]
                    })

            # Use LLM to rank and select best 3-4 tools
            ranked_tools = await self._rank_tools_with_llm(
                bottleneck=bottleneck,
                candidate_tools=candidate_tools,
                user_query=user_query
            )

            tool_recommendations.append({
                "bottleneck_id": bottleneck["id"],
                "bottleneck_title": bottleneck["title"],
                "tools": ranked_tools
            })

        return {"tool_recommendations": tool_recommendations}

    async def _rank_tools_with_llm(
        self,
        bottleneck: Dict,
        candidate_tools: List[Dict],
        user_query: str
    ) -> List[Dict]:
        """Use LLM to intelligently rank and summarize tools."""

        if not candidate_tools:
            return []

        system_prompt = """You are a Tool Selection Expert. Given a bottleneck and candidate tools,
select and rank the TOP 3 most relevant tools.

For each selected tool, provide:
1. A concise 2-sentence description of what it does
2. A simplified pricing summary (e.g., "Free tier available, Pro from $29/mo")
3. 3-4 key features most relevant to the bottleneck
4. 2-3 pros specific to this use case
5. 1-2 cons to be aware of
6. Relevance score (1-10) for this specific bottleneck

OUTPUT FORMAT (strict JSON array):
[
    {
        "rank": 1,
        "name": "Tool Name",
        "description": "Concise 2-sentence description",
        "price": "Simplified pricing",
        "rating": "4.5/5",
        "features": ["Feature 1", "Feature 2", "Feature 3"],
        "pros": ["Pro 1", "Pro 2"],
        "cons": ["Con 1"],
        "website": "https://tool-website.com",
        "relevance_score": 9,
        "why_recommended": "One sentence on why this tool fits"
    }
]

Return ONLY the JSON array. No markdown."""

        tools_context = "\n".join([
            f"- {t['name']}: {t['description'][:200]}... | Pricing: {t['pricing'][:100]}"
            for t in candidate_tools[:8]
        ])

        user_prompt = f"""BOTTLENECK: {bottleneck['title']}
Description: {bottleneck['description']}

USER CONTEXT: {user_query[:300]}

CANDIDATE TOOLS:
{tools_context}

Select and rank the TOP 3 most relevant tools for solving this bottleneck."""

        response = await self._call_llm(system_prompt, user_prompt, self.reasoning_model)
        ranked = self._parse_json_response(response, "tool_ranking", default=[])

        # Ensure we have valid structure
        if not isinstance(ranked, list):
            return []

        return ranked[:4]  # Max 4 tools

    # =========================================================================
    # STAGE 3: SOLUTION STRATEGY AGENT
    # =========================================================================
    async def _stage3_solution_agent(
        self,
        intent_result: Dict,
        tools_result: Dict
    ) -> Dict[str, Any]:
        """
        Stage 3: Generate actionable solution strategies for each bottleneck.

        Creates prioritized action plans that combine:
        - Strategic approach
        - Tool recommendations
        - Execution steps
        - Expected impact

        Returns:
            {
                "strategies": [
                    {
                        "id": 1,
                        "bottleneck_id": 1,
                        "title": "Strategy title",
                        "description": "How to execute",
                        "effort": "LOW|MEDIUM|HIGH",
                        "eta": "24-48 hours",
                        "execution_steps": [...],
                        "expected_impact": "..."
                    }
                ]
            }
        """
        system_prompt = """You are the LAVOO Strategy Agent — an expert at turning bottlenecks into action plans.

Given bottlenecks and recommended tools, create 3-5 PRIORITIZED strategies.

Each strategy should be:
- Actionable (specific steps, not vague advice)
- Time-bound (realistic ETAs)
- Effort-rated (so user can prioritize)

OUTPUT FORMAT (strict JSON):
{
    "strategies": [
        {
            "id": 1,
            "bottleneck_id": 1,
            "title": "Clear action-oriented title",
            "description": "2-3 sentence strategy overview",
            "effort": "LOW|MEDIUM|HIGH",
            "effort_label": "LOW (IMMEDIATE)|MEDIUM (MOST LEVERAGE)|HIGH (COMPREHENSIVE)",
            "eta": "24 hours|7-14 days|2-4 weeks",
            "execution_steps": [
                "Step 1: Specific action",
                "Step 2: Next action",
                "Step 3: Follow-up action",
                "Step 4: Validation step"
            ],
            "expected_impact": "Specific outcome (e.g., 'Reduce time spent by 50%')",
            "success_metric": "How to measure success",
            "first_signal": "When you'll see first results"
        }
    ]
}

PRIORITIZATION RULES:
- Priority 1: Highest leverage, addresses primary bottleneck
- Priority 2-3: Quick wins or supporting actions
- Priority 4-5: Optimization or scaling actions

Return ONLY valid JSON."""

        # Build context
        bottlenecks_ctx = json.dumps(intent_result.get("bottlenecks", []), indent=2)
        tools_ctx = json.dumps(tools_result.get("tool_recommendations", []), indent=2)

        user_prompt = f"""OBJECTIVE: {intent_result.get('objective', 'Business improvement')}

BOTTLENECKS:
{bottlenecks_ctx}

RECOMMENDED TOOLS:
{tools_ctx}

Create 3-5 prioritized strategies to solve these bottlenecks using the recommended tools."""

        response = await self._call_llm(system_prompt, user_prompt, self.model)
        return self._parse_json_response(response, "stage3_solution", default={"strategies": []})

    # =========================================================================
    # STAGE 4: ROADMAP IMPLEMENTATION AGENT
    # =========================================================================
    async def _stage4_roadmap_agent(
        self,
        strategies_result: Dict,
        tools_result: Dict
    ) -> Dict[str, Any]:
        """
        Stage 4: Create a comprehensive implementation roadmap.

        Converts strategies into a timeline-based execution plan with:
        - Phased implementation
        - Tool integration steps
        - Dependencies and prerequisites

        Returns:
            {
                "roadmap": [
                    {
                        "phase": 1,
                        "title": "Foundation Setup",
                        "timeline": "Days 1-3",
                        "tasks": [...],
                        "tools_to_setup": [...],
                        "milestone": "What success looks like"
                    }
                ]
            }
        """
        system_prompt = """You are the LAVOO Roadmap Agent — a project manager creating implementation timelines.

Convert strategies into a phased roadmap (4-6 phases).

OUTPUT FORMAT (strict JSON):
{
    "roadmap": [
        {
            "phase": 1,
            "title": "Phase title (e.g., 'Foundation Setup')",
            "timeline": "Days 1-3|Week 1|Days 1-7",
            "difficulty": "Easy|Medium|Hard",
            "description": "What happens in this phase",
            "tasks": [
                "Specific task 1",
                "Specific task 2",
                "Specific task 3"
            ],
            "tools_to_setup": ["Tool 1", "Tool 2"],
            "milestone": "Clear deliverable/outcome",
            "dependencies": "What must be done first (or 'None')"
        }
    ],
    "total_timeline": "2-4 weeks",
    "quick_wins": [
        "Thing you can do in 24 hours",
        "Another immediate action"
    ]
}

PHASE GUIDELINES:
- Phase 1: Foundation/Setup (tools, accounts, basics)
- Phase 2: Configuration/Customization
- Phase 3: Integration/Connection
- Phase 4: Execution/Launch
- Phase 5: Optimization/Iteration
- Phase 6: Scale (optional)

Return ONLY valid JSON."""

        strategies_ctx = json.dumps(strategies_result.get("strategies", []), indent=2)
        tools_ctx = json.dumps(tools_result.get("tool_recommendations", []), indent=2)

        user_prompt = f"""STRATEGIES TO IMPLEMENT:
{strategies_ctx}

TOOLS AVAILABLE:
{tools_ctx}

Create a phased implementation roadmap (4-6 phases) for executing these strategies."""

        response = await self._call_llm(system_prompt, user_prompt, self.model)
        return self._parse_json_response(response, "stage4_roadmap", default={"roadmap": []})

    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str
    ) -> str:
        """Call the LLM and return the response text."""
        if not self.client:
            raise RuntimeError("LLM client not initialized. Check XAI_API_KEY.")

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_json_response(
        self,
        response: str,
        stage: str,
        default: Any = None
    ) -> Any:
        """Parse JSON from LLM response, handling common issues."""
        if not response:
            logger.warning(f"{stage}: Empty response")
            return default if default is not None else {}

        # Clean response
        text = response.strip()

        # Remove markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        # Try to find JSON in response
        try:
            # Try direct parse first
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            import re
            json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            logger.warning(f"{stage}: Failed to parse JSON: {text[:200]}")
            return default if default is not None else {}

    async def _save_to_database(
        self,
        user_id: int,
        user_query: str,
        intent_result: Dict,
        tools_result: Dict,
        strategies_result: Dict,
        roadmap_result: Dict,
        duration: float
    ) -> int:
        """Save analysis results to database."""
        from db.pg_models import BusinessAnalysis

        try:
            analysis = BusinessAnalysis(
                user_id=user_id,
                business_goal=user_query,
                objective=intent_result.get("objective", ""),
                bottlenecks=json.dumps(intent_result.get("bottlenecks", [])),
                business_strategies=json.dumps(strategies_result.get("strategies", [])),
                ai_tools=json.dumps(self._extract_all_tools(tools_result)),
                roadmap=json.dumps(roadmap_result.get("roadmap", [])),
                key_evidence=json.dumps(intent_result.get("key_evidence", [])),
                assumptions=json.dumps(intent_result.get("assumptions", [])),
                reasoning_trace=json.dumps(intent_result.get("reasoning_trace", [])),
                confidence_score=intent_result.get("confidence_score", 85),
                duration=duration,
                analysis_type="agentic_v2"
            )

            self.db.add(analysis)
            self.db.commit()
            self.db.refresh(analysis)

            logger.info(f"Saved analysis ID: {analysis.id}")
            return analysis.id

        except Exception as e:
            logger.error(f"Failed to save analysis: {e}")
            self.db.rollback()
            raise

    def _extract_all_tools(self, tools_result: Dict) -> List[Dict]:
        """Extract flat list of all recommended tools."""
        all_tools = []
        for rec in tools_result.get("tool_recommendations", []):
            for tool in rec.get("tools", []):
                tool["bottleneck_id"] = rec.get("bottleneck_id", 1)
                all_tools.append(tool)
        return all_tools

    def _format_for_frontend(
        self,
        analysis_id: int,
        user_query: str,
        intent_result: Dict,
        tools_result: Dict,
        strategies_result: Dict,
        roadmap_result: Dict
    ) -> Dict[str, Any]:
        """Format analysis results for frontend consumption."""

        # Map tools to strategies for frontend
        all_tools = self._extract_all_tools(tools_result)
        strategies = strategies_result.get("strategies", [])

        # Build ai_tools array matching frontend expectations
        ai_tools_formatted = []
        for i, tool in enumerate(all_tools[:5]):  # Max 5 tools
            ai_tools_formatted.append({
                "id": i + 1,
                "bottleneckId": tool.get("bottleneck_id", 1),
                "title": tool.get("name", "Unknown Tool"),
                "description": tool.get("description", ""),
                "price": tool.get("price", "Contact for pricing"),
                "rating": tool.get("rating", "4.5/5"),
                "features": tool.get("features", []),
                "pros": tool.get("pros", []),
                "cons": tool.get("cons", []),
                "website": tool.get("website", "#"),
                "comparison": {
                    "pricing": tool.get("price", "Varies"),
                    "easeOfUse": "8/10",
                    "learningCurve": "Medium",
                    "integration": "Good"
                },
                "implementation": {
                    "timeframe": "1-2 weeks",
                    "difficulty": "Medium",
                    "steps": tool.get("features", [])[:4],
                    "requirements": ["Account setup", "API access"]
                }
            })

        # Format bottlenecks for frontend
        bottlenecks_formatted = []
        for bn in intent_result.get("bottlenecks", []):
            bottlenecks_formatted.append({
                "id": bn.get("id", 1),
                "title": bn.get("title", ""),
                "description": bn.get("description", ""),
                "priority": bn.get("priority", "MEDIUM"),
                "impact": bn.get("impact", "")
            })

        # Format strategies for frontend
        strategies_formatted = []
        for strat in strategies:
            strategies_formatted.append({
                "id": strat.get("id", 1),
                "bottleneckId": strat.get("bottleneck_id", 1),
                "title": strat.get("title", ""),
                "description": ". ".join(strat.get("execution_steps", [])),
                "features": strat.get("execution_steps", [])
            })

        return {
            "success": True,
            "data": {
                "analysis_id": analysis_id,
                "business_goal": user_query,
                "objective": intent_result.get("objective", ""),
                "bottlenecks": bottlenecks_formatted,
                "business_strategies": strategies_formatted,
                "ai_tools": ai_tools_formatted,
                "roadmap": roadmap_result.get("roadmap", []),
                "key_evidence": intent_result.get("key_evidence", []),
                "assumptions": intent_result.get("assumptions", []),
                "reasoning_trace": intent_result.get("reasoning_trace", []),
                "ai_confidence_score": intent_result.get("confidence_score", 85),
                "created_at": datetime.now().isoformat(),
                "roi_metrics": None  # Explicitly no ROI
            }
        }


# Factory function for easy instantiation
def create_analyzer(db_session: Session) -> AgenticAnalyzer:
    """Create an AgenticAnalyzer instance."""
    return AgenticAnalyzer(db_session)


# Example usage
if __name__ == "__main__":
    import asyncio
    from db.pg_connections import SessionLocal

    async def test():
        session = SessionLocal()
        try:
            analyzer = create_analyzer(session)
            result = await analyzer.analyze(
                user_query="I run a YouTube channel about AI tools with 5k subscribers. I want to monetize but only have 10 hours/week.",
                user_id=1
            )
            print(json.dumps(result, indent=2))
        finally:
            session.close()

    asyncio.run(test())
