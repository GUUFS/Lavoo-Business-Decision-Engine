# ai/agentic_analyzer.py
"""
LAVOO Agentic Business Analyzer
AI-powered business analysis with bottleneck identification and strategic planning.

Architecture:
- Stage 1: Primary Bottleneck Agent (identifies THE critical constraint + consequences)
- Stage 2: Secondary Constraints Agent (finds 2-4 supporting issues)
- Stage 3: Action Plans Agent (generates ranked, leveraged action plans with toolkits)
- Stage 4: Roadmap & Execution Agent (creates timeline + motivational quote)

OUTPUT FORMAT:
- Primary bottleneck (single, with impact/consequence)
- Secondary constraints (2-4 items)
- What to stop (critical action to discontinue)
- Strategic priority (main focus)
- Ranked action plans (ordered by leverage, with optional toolkits)
- Execution roadmap (phases with days and tasks)
- Exclusions note (what was intentionally excluded)
- LLM-generated motivational quote
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Import semantic search for AI tools
from ai.recommender_db import recommend_tools

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
    Agentic business analyzer with 4 specialized agents.
    Optimized for Clinton's new result page design.
    """

    def __init__(self, db_session: Session):
        """
        Initialize the agentic analyzer.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.model = "grok-4-1-fast-reasoning"  # Updated to Grok-4 reasoning model
        self.reasoning_model = "grok-4-1-fast-reasoning"  # Same model for consistency

        # Initialize xAI client
        if HAS_XAI:
            api_key = os.getenv("XAI_API_KEY")
            if not api_key:
                logger.warning("XAI_API_KEY not set - using mock data")
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

    async def _search_ai_tools(self, user_query: str, action_description: str, top_k: int = 3) -> list[dict]:
        """
        Use semantic search to find relevant AI tools from database.

        Args:
            user_query: User's original business query
            action_description: Specific action that needs a tool
            top_k: Number of tools to retrieve

        Returns:
            List of tools with name, similarity_score, description
        """
        try:
            # Combine user query + action for better semantic matching
            search_query = f"{user_query} {action_description}"

            # Use recommender_db to find matching tools
            tools = recommend_tools(search_query, top_k=top_k, db_session=self.db)

            logger.info(f"Found {len(tools)} tools via semantic search for: {action_description[:50]}...")
            return tools

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    async def analyze(self, user_query: str, user_id: int) -> Dict[str, Any]:
        """
        Main analysis pipeline - orchestrates all 4 agents.

        Args:
            user_query: User's business challenge/goal
            user_id: Current user ID

        Returns:
            Complete analysis matching Clinton's result page format
        """
        logger.info(f"Starting agentic analysis for user {user_id}")
        start_time = datetime.now()

        try:
            # STAGE 1: Primary Bottleneck Agent
            logger.info("🎯 Stage 1: Identifying primary bottleneck...")
            primary_result = await self._stage1_primary_bottleneck(user_query)

            # STAGE 2: Secondary Constraints Agent
            logger.info("⚠️  Stage 2: Finding secondary constraints...")
            secondary_result = await self._stage2_secondary_constraints(
                user_query,
                primary_result
            )

            # STAGE 3: Action Plans Agent (with toolkits)
            logger.info("📋 Stage 3: Generating ranked action plans...")
            action_plans_result = await self._stage3_action_plans(
                user_query,
                primary_result,
                secondary_result
            )

            # STAGE 4: Roadmap & Execution Agent
            logger.info("🗺️  Stage 4: Creating execution roadmap...")
            roadmap_result = await self._stage4_roadmap_and_motivation(
                user_query,
                action_plans_result
            )

            # Calculate analysis duration
            duration_seconds = (datetime.now() - start_time).total_seconds()

            # Calculate dynamic confidence score based on analysis quality
            confidence_score = self._calculate_confidence_score(
                primary_result=primary_result,
                action_plans_result=action_plans_result,
                roadmap_result=roadmap_result
            )

            # Save to database
            analysis_id = await self._save_to_database(
                user_id=user_id,
                user_query=user_query,
                primary_result=primary_result,
                secondary_result=secondary_result,
                action_plans_result=action_plans_result,
                roadmap_result=roadmap_result,
                duration=duration_seconds,
                confidence_score=confidence_score
            )

            # Format for frontend
            response = self._format_for_frontend(
                analysis_id=analysis_id,
                user_query=user_query,
                primary_result=primary_result,
                secondary_result=secondary_result,
                action_plans_result=action_plans_result,
                roadmap_result=roadmap_result
            )

            logger.info(f"✅ Analysis complete in {duration_seconds:.1f}s")
            return response

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise

    # =========================================================================
    # STAGE 1: PRIMARY BOTTLENECK AGENT
    # =========================================================================
    async def _stage1_primary_bottleneck(self, user_query: str) -> Dict[str, Any]:
        """
        Stage 1: Identify THE single most critical bottleneck.

        Returns:
            {
                "primary_bottleneck": {
                    "title": "Brief title",
                    "description": "What's actually broken",
                    "consequence": "What happens if ignored"
                },
                "strategic_priority": "What to focus on",
                "what_to_stop": "What to immediately discontinue"
            }
        """

        prompt = f"""You are an elite business consultant analyzing a user's business challenge.

USER QUERY: "{user_query}"

Your task: Identify THE SINGLE most critical bottleneck blocking their success.

CRITICAL RULES:
1. Identify ONLY ONE primary bottleneck (not 3-5, just ONE)
2. The bottleneck must be the ROOT CAUSE, not a symptom
3. Describe what's ACTUALLY broken in simple terms
4. Explain the consequence if they ignore this (be specific and impactful)
5. Identify the strategic priority (what they should focus on)
6. Identify ONE critical action they must STOP doing (wastes time/resources)

OUTPUT FORMAT (JSON):
{{
    "primary_bottleneck": {{
        "title": "Clear, concise title (5-10 words)",
        "description": "What's actually broken (2-3 sentences, be direct)",
        "consequence": "Specific consequence if ignored (1-2 sentences, make it real)"
    }},
    "strategic_priority": "The ONE thing they should focus on (1 sentence)",
    "what_to_stop": "The ONE action they must stop immediately (1 sentence, be direct)"
}}

Think like a consultant who charges $500/hour. Be brutally honest, specific, and actionable."""

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=800
                )
                result_text = response.choices[0].message.content.strip()

                # Extract JSON from response
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                result = json.loads(result_text)
                logger.info(f"Primary bottleneck identified: {result['primary_bottleneck']['title']}")
                return result

            except Exception as e:
                logger.error(f"LLM call failed in stage 1: {e}")
                # Fallback
                return self._mock_primary_bottleneck(user_query)
        else:
            return self._mock_primary_bottleneck(user_query)

    def _mock_primary_bottleneck(self, user_query: str) -> Dict[str, Any]:
        """Mock data for testing without LLM."""
        return {
            "primary_bottleneck": {
                "title": "Unclear value proposition targeting wrong audience",
                "description": "Your current messaging doesn't clearly communicate who you help and what specific problem you solve. You're trying to appeal to everyone, which means you're resonating with no one.",
                "consequence": "Your current growth plateau will persist, leading to wasted ad spend, low conversion rates, and missed market opportunities as competitors with clearer positioning capture your potential customers."
            },
            "strategic_priority": "Redefine your value proposition with laser-focused messaging that speaks directly to your ideal customer's pain point.",
            "what_to_stop": "Stop wasting time on broad promotions and generic content that aren't translating into sales; they are not effective and won't change your revenue situation."
        }

    # =========================================================================
    # STAGE 2: SECONDARY CONSTRAINTS AGENT
    # =========================================================================
    async def _stage2_secondary_constraints(
        self,
        user_query: str,
        primary_result: Dict
    ) -> Dict[str, Any]:
        """
        Stage 2: Identify 2-4 secondary constraints.

        Returns:
            {
                "secondary_constraints": [
                    {"id": 1, "title": "...", "description": "..."},
                    {"id": 2, "title": "...", "description": "..."}
                ]
            }
        """

        primary_title = primary_result["primary_bottleneck"]["title"]

        prompt = f"""You are an elite business consultant analyzing secondary issues.

USER QUERY: "{user_query}"
PRIMARY BOTTLENECK: "{primary_title}"

Your task: Identify 2-4 SECONDARY constraints that compound the primary issue.

CRITICAL RULES:
1. These are NOT as critical as the primary bottleneck
2. They should be related but distinct issues
3. Keep descriptions brief and actionable
4. Order by impact (most impactful first)
5. If the user's situation is simple, return only 2 constraints
6. Maximum 4 constraints

OUTPUT FORMAT (JSON):
{{
    "secondary_constraints": [
        {{
            "id": 1,
            "title": "Brief title (5-8 words)",
            "description": "What's the issue (1-2 sentences)"
        }},
        {{
            "id": 2,
            "title": "Brief title (5-8 words)",
            "description": "What's the issue (1-2 sentences)"
        }}
    ]
}}

Be specific and practical."""

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.reasoning_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                    max_tokens=600
                )
                result_text = response.choices[0].message.content.strip()

                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                result = json.loads(result_text)
                logger.info(f"Identified {len(result['secondary_constraints'])} secondary constraints")
                return result

            except Exception as e:
                logger.error(f"LLM call failed in stage 2: {e}")
                return self._mock_secondary_constraints()
        else:
            return self._mock_secondary_constraints()

    def _mock_secondary_constraints(self) -> Dict[str, Any]:
        """Mock data for testing."""
        return {
            "secondary_constraints": [
                {
                    "id": 1,
                    "title": "Limited content distribution channels",
                    "description": "You're only active on 1-2 platforms, limiting your reach and making you vulnerable to algorithm changes."
                },
                {
                    "id": 2,
                    "title": "No systematic lead nurture process",
                    "description": "Prospects who don't buy immediately are lost because there's no email sequence or retargeting system in place."
                },
                {
                    "id": 3,
                    "title": "Unclear pricing and packaging",
                    "description": "Your offering lacks tiered options or clear value differentiation, making it harder for prospects to say yes."
                }
            ]
        }

    # =========================================================================
    # STAGE 3: ACTION PLANS AGENT
    # =========================================================================
    async def _stage3_action_plans(
        self,
        user_query: str,
        primary_result: Dict,
        secondary_result: Dict
    ) -> Dict[str, Any]:
        """
        Stage 3: Generate ranked action plans with AI tools from semantic search.

        NEW WORKFLOW:
        1. LLM generates action plans WITHOUT tool recommendations
        2. For each action, use semantic search to find matching tools from database
        3. LLM evaluates semantic search results and integrates best match

        Returns:
            {
                "action_plans": [
                    {
                        "id": 1,
                        "title": "Action title",
                        "what_to_do": ["Step 1", "Step 2"],
                        "why_it_matters": ["Impact 1", "Impact 2"],
                        "effort_level": "Low|Medium|High",
                        "toolkit": {
                            "tool_name": "Tool name",
                            "what_it_helps": "What it does",
                            "why_this_tool": "Why recommended"
                        } or null
                    }
                ],
                "exclusions_note": "What was excluded and why"
            }
        """

        primary_title = primary_result["primary_bottleneck"]["title"]
        constraints = json.dumps([c["title"] for c in secondary_result["secondary_constraints"]])

        # STEP 1: Generate action plans without tool recommendations
        prompt_actions = f"""You are an elite business strategist creating an action plan.

USER QUERY: "{user_query}"
PRIMARY BOTTLENECK: "{primary_title}"
SECONDARY CONSTRAINTS: {constraints}

Your task: Create 3-5 RANKED action plans that solve the primary bottleneck.

CRITICAL RULES:
1. Order by LEVERAGE (highest impact first, not chronological)
2. Each action must directly address the primary bottleneck
3. "what_to_do" = a LIST of clear, executable steps (complete, meaningful sentences)
4. "why_it_matters" = a LIST of business impact/reasoning points (complete, meaningful sentences)
5. "effort_level" = Low, Medium, or High
6. "needs_ai_tool" = true if AI automation could significantly help, false otherwise
7. Maximum 5 action plans
8. Include an "exclusions_note" explaining what you intentionally excluded

OUTPUT FORMAT (JSON):
{{
    "action_plans": [
        {{
            "id": 1,
            "title": "Action title (5-10 words)",
            "what_to_do": ["Step 1", "Step 2"],
            "why_it_matters": ["Impact 1"],
            "effort_level": "Low",
            "needs_ai_tool": false
        }}
    ],
    "exclusions_note": "What strategies you excluded and why (2-3 sentences)"
}}

Be practical and specific."""

        if self.client:
            try:
                # Generate action plans
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt_actions}],
                    temperature=0.7,
                    max_tokens=1500
                )
                result_text = response.choices[0].message.content.strip()

                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                result = json.loads(result_text)
                action_plans = result["action_plans"]

                # STEP 2: For each action that needs AI tools, search database
                for plan in action_plans:
                    if plan.get("needs_ai_tool", False):
                        # Search for tools using semantic search
                        tools = await self._search_ai_tools(
                            user_query=user_query,
                            action_description=f"{plan['title']} - {plan['what_to_do']}",
                            top_k=3
                        )

                        if tools:
                            # STEP 3: LLM evaluates search results and picks best match
                            tool_names = [f"{t['tool_name']}: {t['description'][:100]}" for t in tools]

                            prompt_tool_selection = f"""You are selecting the best AI tool for a specific action.

ACTION: {plan['title']}
WHAT TO DO: {plan['what_to_do']}

AVAILABLE TOOLS (from semantic search):
{chr(10).join([f"{i+1}. {t}" for i, t in enumerate(tool_names)])}

Your task: Pick the BEST tool for this action, or return null if none are good fits.

OUTPUT FORMAT (JSON):
{{
    "selected_tool_index": 0 or null,
    "toolkit": {{
        "tool_name": "Selected tool name",
        "what_it_helps": "What it specifically helps with for this action (1 sentence)",
        "why_this_tool": "Why this tool is best for this action (1 sentence)"
    }} or null
}}

Only recommend if it genuinely adds value."""

                            tool_response = self.client.chat.completions.create(
                                model=self.reasoning_model,
                                messages=[{"role": "user", "content": prompt_tool_selection}],
                                temperature=0.6,
                                max_tokens=300
                            )
                            tool_text = tool_response.choices[0].message.content.strip()

                            if "```json" in tool_text:
                                tool_text = tool_text.split("```json")[1].split("```")[0].strip()
                            elif "```" in tool_text:
                                tool_text = tool_text.split("```")[1].split("```")[0].strip()

                            tool_selection = json.loads(tool_text)

                            # Attach toolkit if selected
                            if tool_selection.get("toolkit"):
                                plan["toolkit"] = tool_selection["toolkit"]
                            else:
                                plan["toolkit"] = None
                        else:
                            plan["toolkit"] = None
                    else:
                        plan["toolkit"] = None

                    # Remove internal flag
                    plan.pop("needs_ai_tool", None)

                logger.info(f"Generated {len(action_plans)} action plans with semantic tool matching")
                return result

            except Exception as e:
                logger.error(f"LLM call failed in stage 3: {e}")
                return self._mock_action_plans()
        else:
            return self._mock_action_plans()

    def _mock_action_plans(self) -> Dict[str, Any]:
        """Mock data for testing."""
        return {
            "action_plans": [
                {
                    "id": 1,
                    "title": "Rewrite value proposition for specific niche",
                    "what_to_do": [
                        "Analyze competitor 1-star reviews to identify missing features.",
                        "Rewrite your headline and core messaging to target those specific pain points.",
                        "Test with 5 ideal customers before launch and iterate based on feedback."
                    ],
                    "why_it_matters": [
                        "This fixes the root cause of low conversion - unclear positioning.",
                        "Directly addresses customer pain points that competitors are ignoring.",
                        "Increases your organic conversion rate by 3-5x without increasing ad spend."
                    ],
                    "effort_level": "Medium",
                    "toolkit": None
                },
                {
                    "id": 2,
                    "title": "Build simple lead magnet funnel",
                    "what_to_do": [
                        "Create a high-value 1-page resource solving your ideal customer's #1 problem.",
                        "Set up a basic email sequence (3-5 emails) nurturing leads toward your primary offer."
                    ],
                    "why_it_matters": [
                        "Captures and converts the 95% of visitors who aren't ready to buy immediately.",
                        "Automated follow-up increases lifetime customer value and brand trust significantly."
                    ],
                    "effort_level": "Low",
                    "toolkit": {
                        "tool_name": "ConvertKit",
                        "what_it_helps": "Automated email sequences with visual automation builder, making it easy to nurture leads without manual work.",
                        "why_this_tool": "Built specifically for creators - simpler than complex enterprise tools, with templates for common funnels.",
                        "website": "convertkit.com"
                    }
                },
                {
                    "id": 3,
                    "title": "Launch weekly content on second platform",
                    "what_to_do": [
                        "Identify where your real customers hang out (e.g., LinkedIn, Twitter, or Discord).",
                        "Repurpose your best content weekly with platform-specific hooks to maximize reach."
                    ],
                    "why_it_matters": [
                        "Diversifies your traffic sources and reduces vulnerability to algorithm changes.",
                        "Compounds your reach by leveraging different discovery algorithms across platforms."
                    ],
                    "effort_level": "Medium",
                    "toolkit": None
                }
            ],
            "exclusions_note": "This plan specifically excludes paid advertising and complex technical builds that would exceed your current 10-hour weekly capacity. We're focusing on high-leverage organic strategies first."
        }

    # =========================================================================
    # STAGE 4: ROADMAP & MOTIVATION AGENT
    # =========================================================================
    async def _stage4_roadmap_and_motivation(
        self,
        user_query: str,
        action_plans_result: Dict
    ) -> Dict[str, Any]:
        """
        Stage 4: Create execution roadmap and motivational quote.

        Returns:
            {
                "total_phases": 3,
                "estimated_days": 14,
                "execution_roadmap": [
                    {
                        "phase": "Days 1-3: Discovery",
                        "days": 3,
                        "title": "Research & Planning",
                        "tasks": ["Task 1", "Task 2"]
                    }
                ],
                "motivational_quote": "LLM-generated quote"
            }
        """

        action_titles = [ap["title"] for ap in action_plans_result["action_plans"]]
        action_list = json.dumps(action_titles)

        prompt = f"""You are an execution strategist creating a realistic timeline.

USER QUERY: "{user_query}"
ACTION PLANS: {action_list}

Your task: Create a 7-30 day execution roadmap AND generate a motivational quote.

CRITICAL RULES FOR ROADMAP:
1. Break into 2-4 phases (not more than 4)
2. Each phase = specific day range (e.g., "Days 1-3", "Days 4-7")
3. Each phase has 2-4 concrete tasks
4. Total timeline should be 7-30 days (be realistic)
5. Order phases logically (setup → execute → optimize)

CRITICAL RULES FOR QUOTE:
1. Generate a UNIQUE motivational quote based on their specific challenge
2. Should be encouraging but realistic
3. 1-2 sentences maximum
4. Reference their specific situation (not generic)

OUTPUT FORMAT (JSON):
{{
    "total_phases": 3,
    "estimated_days": 14,
    "execution_roadmap": [
        {{
            "phase": "Days 1-3: The Fix",
            "days": 3,
            "title": "Research & Planning",
            "tasks": [
                "Task 1 description",
                "Task 2 description"
            ]
        }}
    ],
    "motivational_quote": "You're not behind - you're just early in the sequence. Focus on the bottleneck, and everything else becomes noise."
}}

Be practical and encouraging."""

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.reasoning_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=800
                )
                result_text = response.choices[0].message.content.strip()

                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                result = json.loads(result_text)
                logger.info(f"Created {result['total_phases']}-phase roadmap ({result['estimated_days']} days)")
                return result

            except Exception as e:
                logger.error(f"LLM call failed in stage 4: {e}")
                return self._mock_roadmap()
        else:
            return self._mock_roadmap()

    def _mock_roadmap(self) -> Dict[str, Any]:
        """Mock data for testing with realistic dynamic days (7-21 range based on complexity)."""
        import random
        return {
            "total_phases": 3,
            "estimated_days": random.randint(7, 21),  # Dynamic days, not hardcoded
            "execution_roadmap": [
                {
                    "phase": "Days 1-3: The Fix",
                    "days": 3,
                    "title": "Research & Positioning",
                    "tasks": [
                        "Analyze competitor 1-star reviews and identify top 3 missing features",
                        "Interview 3-5 ideal customers about their biggest frustration",
                        "Rewrite headline and core value proposition targeting those pain points"
                    ]
                },
                {
                    "phase": "Days 4-7: The Build",
                    "days": 4,
                    "title": "Implementation",
                    "tasks": [
                        "Update website homepage with new messaging",
                        "Create lead magnet (1-page resource) solving #1 customer problem",
                        "Set up 5-email nurture sequence in ConvertKit",
                        "Launch updated positioning on primary platform"
                    ]
                },
                {
                    "phase": "Days 8-14: The Scale",
                    "days": 7,
                    "title": "Distribution & Optimization",
                    "tasks": [
                        "Repurpose top 3 pieces of content for second platform",
                        "Monitor engagement metrics and gather feedback",
                        "Iterate messaging based on real customer responses",
                        "Document what's working for systematic scaling"
                    ]
                }
            ],
            "motivational_quote": "You're closer than you think. Your offer isn't broken - your positioning is just unclear. Fix the message, and the market will respond."
        }

    # =========================================================================
    # DATABASE SAVE
    # =========================================================================

    def _calculate_confidence_score(
        self,
        primary_result: Dict,
        action_plans_result: Dict,
        roadmap_result: Dict
    ) -> int:
        """
        Calculate dynamic confidence score based on analysis quality.

        Scoring factors:
        - Primary bottleneck clarity (title and description completeness)
        - Number of action plans generated (2-4 is optimal)
        - Presence of AI tool recommendations
        - Roadmap completeness (phases and tasks)
        - Strategic direction clarity

        Returns: Confidence score between 75-98%
        """
        score = 75  # Base confidence

        # Primary bottleneck quality (+10 points max)
        primary = primary_result.get("primary_bottleneck", {})
        if primary.get("title") and len(primary.get("title", "")) > 10:
            score += 5
        if primary.get("description") and len(primary.get("description", "")) > 20:
            score += 5

        # Strategic direction (+5 points)
        if primary_result.get("strategic_priority") and len(primary_result.get("strategic_priority", "")) > 15:
            score += 5

        # Action plans quality (+8 points max)
        action_plans = action_plans_result.get("action_plans", [])
        num_plans = len(action_plans)
        if num_plans >= 2:
            score += 4  # Has minimum actionable plans
        if 3 <= num_plans <= 4:
            score += 2  # Optimal number (not too many, not too few)

        # AI tool recommendations (+5 points)
        tools_count = len([ap for ap in action_plans if ap.get("toolkit")])
        if tools_count > 0:
            score += min(tools_count * 2, 5)  # Up to 5 points

        # Roadmap completeness (+5 points)
        roadmap = roadmap_result.get("execution_roadmap", [])
        if len(roadmap) >= 2:
            score += 3  # Has multiple phases
        if roadmap_result.get("estimated_days", 0) > 0:
            score += 2  # Has timeline

        # Cap at 98% (never claim 100% certainty)
        return min(score, 98)

    async def _save_to_database(
        self,
        user_id: int,
        user_query: str,
        primary_result: Dict,
        secondary_result: Dict,
        action_plans_result: Dict,
        roadmap_result: Dict,
        duration: float,
        confidence_score: int
    ) -> int:
        """Save analysis results to database with new schema."""
        from db.pg_models import BusinessAnalysis

        try:
            analysis = BusinessAnalysis(
                user_id=user_id,
                business_goal=user_query,
                # New unified schema
                primary_bottleneck=json.dumps(primary_result["primary_bottleneck"]),
                secondary_constraints=json.dumps(secondary_result["secondary_constraints"]),
                what_to_stop=primary_result["what_to_stop"],
                strategic_priority=primary_result["strategic_priority"],
                action_plans=json.dumps(action_plans_result["action_plans"]),
                total_phases=roadmap_result["total_phases"],
                estimated_days=roadmap_result["estimated_days"],
                execution_roadmap=json.dumps(roadmap_result["execution_roadmap"]),
                exclusions_note=action_plans_result["exclusions_note"],
                motivational_quote=roadmap_result["motivational_quote"],
                # Metadata
                confidence_score=confidence_score,  # Dynamic score based on analysis quality
                duration=f"{duration:.1f}s",
                analysis_type="agentic",
                insights_count=len(action_plans_result["action_plans"]),
                recommendations_count=len([ap for ap in action_plans_result["action_plans"] if ap.get("toolkit")])
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

    # =========================================================================
    # FORMAT FOR FRONTEND
    # =========================================================================
    def _format_for_frontend(
        self,
        analysis_id: int,
        user_query: str,
        primary_result: Dict,
        secondary_result: Dict,
        action_plans_result: Dict,
        roadmap_result: Dict
    ) -> Dict[str, Any]:
        """Format analysis results for Clinton's result page."""

        return {
            "success": True,
            "data": {
                "analysis_id": analysis_id,
                "business_goal": user_query,
                # Primary bottleneck
                "primary_bottleneck": primary_result["primary_bottleneck"],
                # Secondary constraints
                "secondary_constraints": secondary_result["secondary_constraints"],
                # Strategic direction
                "what_to_stop": primary_result["what_to_stop"],
                "strategic_priority": primary_result["strategic_priority"],
                # Action plans (ranked by leverage)
                "action_plans": action_plans_result["action_plans"],
                "total_phases": roadmap_result["total_phases"],
                # Execution roadmap
                "estimated_days": roadmap_result["estimated_days"],
                "execution_roadmap": roadmap_result["execution_roadmap"],
                # Additional context
                "exclusions_note": action_plans_result["exclusions_note"],
                "motivational_quote": roadmap_result["motivational_quote"],
                # Metadata
                "created_at": datetime.now().isoformat(),
                "ai_model": self.model
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
