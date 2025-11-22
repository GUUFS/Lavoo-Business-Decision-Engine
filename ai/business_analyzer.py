# ai/business_analyzer.py
"""
AI Business Analyzer - Dynamic Tool Recommender
Uses Cohere Command R 7B (December 2024) for cost-effective business analysis.

Workflow:
User Query → Intent Analysis → Tool Discovery → Combination Logic → Roadmap Generation → Response
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load environment variables from .env.local
load_dotenv('.env.local')

# Import Cohere SDK
try:
    import cohere

    HAS_COHERE = True
except ImportError:
    HAS_COHERE = False
    print("Warning: cohere package not installed. Install with: uv add cohere")

logger = logging.getLogger(__name__)


class BusinessAnalyzer:
    """
    Dynamic AI-powered business analyzer that:
    1. Analyzes user goals using Cohere Command 7B
    2. Discovers relevant tools from database (no hardcoding)
    3. Suggests 2-3 tool combinations with synergies
    4. Generates custom actionable roadmaps
    """

    def __init__(self, db_session: Session):
        """
        Initialize the analyzer.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.model = "command-r7b-12-2024"  # Cohere Command R 7B (December 2024)

        # Initialize Cohere client from environment
        if HAS_COHERE:
            api_key = os.getenv("COHERE_API_KEY")
            if not api_key:
                logger.warning("COHERE_API_KEY not set in environment variables")
                self.client = None
            else:
                self.client = cohere.Client(api_key)
                logger.info("Cohere client initialized successfully")
        else:
            self.client = None
            logger.warning("Cohere SDK not installed, using fallback methods")

    async def analyze(self, user_goal: str, user_id: int) -> Dict:
        """
        Main analysis function - follows the simplified workflow.

        Args:
            user_goal: User's business goal (e.g., "Grow AI newsletter to 10k subs")
            user_id: Current user ID

        Returns:
            Complete analysis with intent, tool combos, and roadmap
        """
        logger.info(f"Starting analysis for user {user_id}: {user_goal[:100]}")

        try:
            # STEP 1: Intent Analysis (AI)
            intent_analysis = await self._analyze_intent(user_goal)
            logger.info(f"Intent analyzed: {intent_analysis['objective']}")

            # STEP 2: Tool Discovery (Database Query)
            relevant_tools = await self._discover_tools(intent_analysis)
            logger.info(f"Found {len(relevant_tools)} relevant tools")

            # STEP 3: Combination Logic (AI)
            tool_combinations = await self._suggest_combinations(intent_analysis, relevant_tools)
            logger.info(f"Generated {len(tool_combinations)} tool combinations")

            # STEP 4: Roadmap Generation (AI)
            roadmap = await self._generate_roadmap(intent_analysis, tool_combinations)
            logger.info(f"Generated roadmap with {len(roadmap)} stages")

            # STEP 5: Generate ROI Projections (AI)
            roi_projections = await self._generate_roi_projections(
                intent_analysis, tool_combinations, roadmap
            )
            logger.info("Generated ROI projections")

            # STEP 6: Save to Database
            analysis_id = await self._save_analysis(
                user_id=user_id,
                user_goal=user_goal,
                intent_analysis=intent_analysis,
                tool_combinations=tool_combinations,
                roadmap=roadmap,
                roi_projections=roi_projections,
            )

            # STEP 7: Format Response
            return {
                "analysis_id": analysis_id,
                "business_goal": user_goal,
                "intent_analysis": intent_analysis,
                "tool_combinations": tool_combinations,
                "roadmap": roadmap,
                "roi_projections": roi_projections,
                "estimated_cost": sum(combo["total_monthly_cost"] for combo in tool_combinations)
                / len(tool_combinations),  # Average cost
                "timeline_weeks": sum(stage["duration_weeks"] for stage in roadmap),
                "created_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise

    async def _analyze_intent(self, user_goal: str) -> Dict:
        """
        STEP 1: Extract objective, capabilities needed, stages, and metrics.

        Args:
            user_goal: User's business goal

        Returns:
            {
                "objective": "Grow newsletter to 10k subscribers",
                "bottlenecks": ["limited email automation", "manual content creation", "no analytics tracking"],
                "stages": ["Setup", "Growth", "Engagement", "Monetization"],
                "success_metrics": ["subscriber count", "open rate", "click-through rate"]
            }
        """
        system_prompt = """You are a business analyst. Extract structured information from user goals.

Return a valid JSON object with these exact keys:
- objective: string (clear, specific goal)
- bottlenecks: list of strings (specific problems, pain points, or obstacles the user is facing)
- stages: list of strings (implementation phases)
- success_metrics: list of strings (measurable KPIs)

Be specific and actionable. For bottlenecks, identify actual problems/obstacles, not capabilities.
Examples: "manual data entry taking 10 hours/week", "no automated email follow-up", "cart abandonment rate at 70%"
Your response must be valid JSON only, no additional text."""

        user_prompt = f"Analyze this business goal and identify the bottlenecks/problems: {user_goal}"

        if HAS_COHERE and self.client:
            try:
                # Cohere Chat API call
                response = self.client.chat(
                    model=self.model,
                    message=user_prompt,
                    preamble=system_prompt,
                    temperature=0.3,  # Lower temperature for focused responses
                )

                # Extract text response
                response_text = response.text.strip()

                # Parse JSON from response
                # Cohere sometimes wraps JSON in markdown, so we clean it
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                return json.loads(response_text)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Cohere JSON response: {e}")
                logger.debug(f"Raw response: {response_text}")
                # Fall through to fallback
            except Exception as e:
                logger.error(f"Cohere API error: {e}")
                # Fall through to fallback

        # Fallback: Basic keyword extraction
        return self._fallback_intent_analysis(user_goal)

    def _fallback_intent_analysis(self, user_goal: str) -> Dict:
        """Fallback intent analysis without AI"""
        return {
            "objective": user_goal,
            "bottlenecks": [
                "manual processes",
                "lack of automation",
                "time constraints",
                "limited resources",
            ],
            "stages": ["Setup", "Implementation", "Optimization", "Scale"],
            "success_metrics": [
                "engagement rate",
                "conversion rate",
                "time saved",
                "revenue growth",
            ],
        }

    async def _discover_tools(self, intent_analysis: Dict) -> List[Dict]:
        """
        STEP 2: Query database for tools matching needed capabilities.
        NO HARDCODING - dynamic discovery based on AI analysis.

        Args:
            intent_analysis: Result from _analyze_intent

        Returns:
            List of relevant tools from database
        """
        from db.pg_models import AITool

        bottlenecks = intent_analysis.get("bottlenecks", [])

        # Build search queries from bottlenecks
        search_terms = []
        for bottleneck in bottlenecks:
            search_terms.extend(bottleneck.lower().split())

        # Remove duplicates and common words
        common_words = {"the", "a", "an", "and", "or", "but", "for", "with"}
        search_terms = [term for term in set(search_terms) if term not in common_words]

        # Query database for matching tools
        tools = []

        # Search in description, key_features, and who_should_use
        for term in search_terms[:5]:  # Limit to top 5 search terms
            results = (
                self.db.query(AITool)
                .filter(
                    (AITool.description.ilike(f"%{term}%"))
                    | (AITool.key_features.ilike(f"%{term}%"))
                    | (AITool.who_should_use.ilike(f"%{term}%"))
                )
                .limit(10)
                .all()
            )

            for tool in results:
                if tool.id not in [t["id"] for t in tools]:
                    tools.append(
                        {
                            "id": tool.id,
                            "name": tool.name,
                            "description": tool.description,
                            "main_category": tool.main_category,
                            "pricing": tool.pricing,
                            "ratings": tool.ratings,
                            "key_features": tool.key_features,
                            "compatibility_integration": tool.compatibility_integration,
                        }
                    )

        # If no results, get popular tools from relevant categories
        if not tools:
            logger.warning("No tools found via search, using category fallback")
            results = self.db.query(AITool).limit(15).all()

            for tool in results:
                tools.append(
                    {
                        "id": tool.id,
                        "name": tool.name,
                        "description": tool.description,
                        "main_category": tool.main_category,
                        "pricing": tool.pricing,
                        "ratings": tool.ratings,
                        "key_features": tool.key_features,
                        "compatibility_integration": tool.compatibility_integration,
                    }
                )

        logger.info(f"Discovered {len(tools)} tools: {[t['name'] for t in tools[:5]]}")
        return tools[:15]  # Limit to 15 tools to reduce AI context size

    async def _suggest_combinations(self, intent_analysis: Dict, tools: List[Dict]) -> List[Dict]:
        """
        STEP 3: AI suggests 2-3 tool combinations with synergies.

        Args:
            intent_analysis: Parsed user intent
            tools: List of relevant tools from database

        Returns:
            List of 2-3 tool combinations with synergy analysis
        """
        system_prompt = """You are a tech integration specialist. Given a business objective and available tools, suggest 2-3 optimal tool combinations.

For each combination:
1. Select 2-4 tools that work together synergistically
2. Explain how they integrate (data flow, automation triggers)
3. Calculate synergy score (0-100 based on how well they complement each other)
4. Estimate setup difficulty (Easy/Medium/Hard)
5. Calculate total monthly cost
6. Explain why this combo works
7. Describe expected outcome

Return JSON:
{
  "combinations": [
    {
      "combo_name": "string",
      "tools": [{"id": int, "name": "string", "role": "string"}],
      "synergy_score": float,
      "integration_flow": {"description": "string", "data_flow": ["step1", "step2"]},
      "setup_difficulty": "Easy|Medium|Hard",
      "total_monthly_cost": float,
      "why_this_combo": "string",
      "expected_outcome": "string"
    }
  ]
}"""

        user_prompt = f"""Objective: {intent_analysis["objective"]}
Bottlenecks/Problems: {", ".join(intent_analysis["bottlenecks"])}

Available tools:
{json.dumps([{"id": t["id"], "name": t["name"], "description": t["description"][:100], "pricing": t["pricing"]} for t in tools], indent=2)}

Suggest 2-3 tool combinations that work together to solve these bottlenecks. Focus on integration and synergy. Return only valid JSON."""

        if HAS_COHERE and self.client:
            try:
                response = self.client.chat(
                    model=self.model,
                    message=user_prompt,
                    preamble=system_prompt,
                    temperature=0.5,  # Balanced creativity and consistency
                )

                response_text = response.text.strip()

                # Clean markdown wrapper if present
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                result = json.loads(response_text)
                return result.get("combinations", [])[:3]  # Max 3 combinations

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Cohere JSON response: {e}")
                logger.debug(f"Raw response: {response_text}")
                # Fall through to fallback
            except Exception as e:
                logger.error(f"Cohere combination error: {e}")
                # Fall through to fallback

        # Fallback: Create basic combinations
        return self._fallback_combinations(tools)

    def _fallback_combinations(self, tools: List[Dict]) -> List[Dict]:
        """Fallback tool combinations without AI"""
        if len(tools) < 2:
            return []

        # Create simple combination from top 3 tools
        combo_tools = tools[:3]

        return [
            {
                "combo_name": "Essential Toolkit",
                "tools": [
                    {"id": t["id"], "name": t["name"], "role": "Core tool"} for t in combo_tools
                ],
                "synergy_score": 75.0,
                "integration_flow": {
                    "description": "Tools work together to achieve your goal",
                    "data_flow": [
                        f"Use {combo_tools[0]['name']} for primary tasks",
                        f"Integrate with {combo_tools[1]['name']} for automation",
                        f"Monitor results with {combo_tools[2]['name']}"
                        if len(combo_tools) > 2
                        else "",
                    ],
                },
                "setup_difficulty": "Medium",
                "total_monthly_cost": 50.0,
                "why_this_combo": "These tools complement each other and cover your main needs",
                "expected_outcome": "Streamlined workflow with integrated automation",
            }
        ]

    async def _generate_roadmap(
        self, intent_analysis: Dict, combinations: List[Dict]
    ) -> List[Dict]:
        """
        STEP 4: Generate actionable implementation roadmap.

        Args:
            intent_analysis: Parsed user intent
            combinations: Recommended tool combinations

        Returns:
            List of roadmap stages with tasks, deliverables, metrics
        """
        system_prompt = """You are a project manager. Create a detailed implementation roadmap.

Break down into stages:
- Stage 1: Setup & Foundation (tools setup, initial config)
- Stage 2: Implementation & Integration (connect tools, workflows)
- Stage 3: Optimization & Scale (analyze, refine, expand)

For each stage, include:
- duration_weeks: int
- tasks: list of specific action items
- deliverables: list of outputs
- metrics: list of KPIs to track
- cost_this_stage: float (tool costs for this period)

Return JSON:
{
  "stages": [
    {
      "stage_number": 1,
      "stage_name": "string",
      "duration_weeks": int,
      "tasks": ["task1", "task2"],
      "deliverables": ["deliverable1", "deliverable2"],
      "metrics": ["metric1", "metric2"],
      "cost_this_stage": float
    }
  ]
}"""

        # Use first combination for roadmap
        primary_combo = combinations[0] if combinations else {}

        user_prompt = f"""Objective: {intent_analysis["objective"]}
Success metrics: {", ".join(intent_analysis["success_metrics"])}

Tools to implement:
{json.dumps([t["name"] for t in primary_combo.get("tools", [])], indent=2)}

Create a 3-stage implementation roadmap. Be specific and actionable. Return only valid JSON."""

        if HAS_COHERE and self.client:
            try:
                response = self.client.chat(
                    model=self.model,
                    message=user_prompt,
                    preamble=system_prompt,
                    temperature=0.4,
                )

                response_text = response.text.strip()

                # Clean markdown wrapper if present
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                result = json.loads(response_text)
                return result.get("stages", [])

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Cohere JSON response: {e}")
                logger.debug(f"Raw response: {response_text}")
                # Fall through to fallback
            except Exception as e:
                logger.error(f"Cohere roadmap error: {e}")
                # Fall through to fallback

        # Fallback: Create basic roadmap
        return self._fallback_roadmap(intent_analysis)

    def _fallback_roadmap(self, intent_analysis: Dict) -> List[Dict]:
        """Fallback roadmap without AI"""
        return [
            {
                "stage_number": 1,
                "stage_name": "Setup & Foundation",
                "duration_weeks": 2,
                "tasks": [
                    "Set up tool accounts and workspaces",
                    "Configure initial settings",
                    "Connect integrations",
                    "Import existing data",
                ],
                "deliverables": [
                    "All tools configured and connected",
                    "Initial workflows established",
                    "Team training completed",
                ],
                "metrics": intent_analysis["success_metrics"][:2],
                "cost_this_stage": 50.0,
            },
            {
                "stage_number": 2,
                "stage_name": "Implementation & Execution",
                "duration_weeks": 4,
                "tasks": [
                    "Launch first campaigns/workflows",
                    "Monitor and collect data",
                    "Refine based on early results",
                    "Scale successful processes",
                ],
                "deliverables": [
                    "Active campaigns running",
                    "Data collection systems operational",
                    "Initial optimization completed",
                ],
                "metrics": intent_analysis["success_metrics"],
                "cost_this_stage": 100.0,
            },
            {
                "stage_number": 3,
                "stage_name": "Optimization & Scale",
                "duration_weeks": 6,
                "tasks": [
                    "Analyze performance data",
                    "Optimize underperforming areas",
                    "Expand successful strategies",
                    "Automate repetitive processes",
                ],
                "deliverables": [
                    "Optimized workflows",
                    "Automated systems",
                    f"Achieved: {intent_analysis['objective']}",
                ],
                "metrics": intent_analysis["success_metrics"],
                "cost_this_stage": 150.0,
            },
        ]

    async def _generate_roi_projections(
        self, intent_analysis: Dict, combinations: List[Dict], roadmap: List[Dict]
    ) -> Dict:
        """
        Generate ROI projections based on tool costs and expected outcomes.

        Args:
            intent_analysis: Parsed user intent
            combinations: Recommended tool combinations
            roadmap: Implementation roadmap stages

        Returns:
            Dictionary with ROI metrics, time savings, revenue projections, break-even analysis
        """
        system_prompt = """You are a financial analyst specializing in ROI calculations for business tools.

Given a business objective, tool costs, and implementation timeline, calculate ROI projections.

Return JSON with:
{
  "total_investment": float,
  "monthly_recurring_cost": float,
  "break_even_months": int,
  "time_savings_per_week": float,
  "time_savings_value_monthly": float,
  "efficiency_gain_percent": int,
  "revenue_impact": {
    "month_3": float,
    "month_6": float,
    "month_12": float
  },
  "cost_benefit_analysis": {
    "year_1_cost": float,
    "year_1_benefit": float,
    "year_1_net_roi": float,
    "roi_percentage": int
  },
  "key_value_drivers": [
    "driver1",
    "driver2"
  ],
  "risk_factors": [
    "risk1",
    "risk2"
  ]
}

Be realistic and conservative with projections."""

        # Calculate actual costs
        total_implementation_cost = sum(stage.get("cost_this_stage", 0) for stage in roadmap)
        avg_monthly_cost = (
            sum(combo.get("total_monthly_cost", 0) for combo in combinations) / len(combinations)
            if combinations
            else 0
        )

        user_prompt = f"""Business Objective: {intent_analysis["objective"]}
Bottlenecks Being Solved: {", ".join(intent_analysis["bottlenecks"])}

Tool Costs:
- Total Implementation Cost: ${total_implementation_cost}
- Average Monthly Tool Cost: ${avg_monthly_cost}
- Implementation Timeline: {sum(stage.get('duration_weeks', 0) for stage in roadmap)} weeks

Success Metrics: {", ".join(intent_analysis["success_metrics"])}

Calculate realistic ROI projections. Focus on time savings, efficiency gains, and potential revenue impact based on solving the bottlenecks. Return only valid JSON."""

        if HAS_COHERE and self.client:
            try:
                response = self.client.chat(
                    model=self.model,
                    message=user_prompt,
                    preamble=system_prompt,
                    temperature=0.3,  # Low temperature for consistent numbers
                )

                response_text = response.text.strip()

                # Clean markdown wrapper if present
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                result = json.loads(response_text)
                return result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Cohere JSON response: {e}")
                logger.debug(f"Raw response: {response_text}")
                # Fall through to fallback
            except Exception as e:
                logger.error(f"Cohere ROI generation error: {e}")
                # Fall through to fallback

        # Fallback: Calculate basic ROI
        return self._fallback_roi_projections(total_implementation_cost, avg_monthly_cost, roadmap)

    def _fallback_roi_projections(
        self, total_implementation_cost: float, monthly_cost: float, roadmap: List[Dict]
    ) -> Dict:
        """Fallback ROI projections without AI"""
        timeline_weeks = sum(stage.get("duration_weeks", 0) for stage in roadmap)
        timeline_months = timeline_weeks / 4.0

        # Conservative estimates
        time_savings_hours_week = 10  # Assume 10 hours saved per week
        hourly_rate = 50  # Assume $50/hour value
        time_savings_value_monthly = time_savings_hours_week * 4 * hourly_rate

        year_1_cost = total_implementation_cost + (monthly_cost * 12)
        year_1_benefit = time_savings_value_monthly * 12 * 1.5  # 1.5x multiplier for additional benefits
        year_1_net_roi = year_1_benefit - year_1_cost
        roi_percentage = int((year_1_net_roi / year_1_cost) * 100) if year_1_cost > 0 else 0

        return {
            "total_investment": total_implementation_cost,
            "monthly_recurring_cost": monthly_cost,
            "break_even_months": int(year_1_cost / time_savings_value_monthly) if time_savings_value_monthly > 0 else 12,
            "time_savings_per_week": time_savings_hours_week,
            "time_savings_value_monthly": time_savings_value_monthly,
            "efficiency_gain_percent": 35,  # Conservative 35% efficiency gain
            "revenue_impact": {
                "month_3": time_savings_value_monthly * 3 * 0.5,  # 50% of value realized
                "month_6": time_savings_value_monthly * 6 * 0.75,  # 75% of value realized
                "month_12": time_savings_value_monthly * 12,  # Full value realized
            },
            "cost_benefit_analysis": {
                "year_1_cost": year_1_cost,
                "year_1_benefit": year_1_benefit,
                "year_1_net_roi": year_1_net_roi,
                "roi_percentage": roi_percentage,
            },
            "key_value_drivers": [
                "Time savings from automation",
                "Improved efficiency and productivity",
                "Reduced manual errors",
                "Better data-driven decision making",
            ],
            "risk_factors": [
                "Implementation time may vary",
                "Team adoption and learning curve",
                "Integration complexity",
                "Ongoing maintenance requirements",
            ],
        }

    async def _save_analysis(
        self,
        user_id: int,
        user_goal: str,
        intent_analysis: Dict,
        tool_combinations: List[Dict],
        roadmap: List[Dict],
        roi_projections: Dict = None,
    ) -> int:
        """
        Save complete analysis to database.

        Returns:
            analysis_id
        """
        from db.pg_models import BusinessAnalysis, ToolCombination, RoadmapStage

        # Calculate totals
        avg_cost = (
            sum(combo.get("total_monthly_cost", 0) for combo in tool_combinations)
            / len(tool_combinations)
            if tool_combinations
            else 0
        )

        total_weeks = sum(stage.get("duration_weeks", 0) for stage in roadmap)

        # Create main analysis record
        analysis = BusinessAnalysis(
            user_id=user_id,
            business_goal=user_goal,
            intent_analysis=intent_analysis,
            tool_combinations=tool_combinations,
            roadmap=roadmap,
            roi_projections=roi_projections or {},
            estimated_cost=avg_cost,
            timeline_weeks=total_weeks,
            status="completed",
            ai_model_used=self.model,
        )

        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        # Save tool combinations
        for combo in tool_combinations:
            combo_record = ToolCombination(
                analysis_id=analysis.id,
                combo_name=combo.get("combo_name", ""),
                tools=combo.get("tools", []),
                synergy_score=combo.get("synergy_score", 0),
                integration_flow=combo.get("integration_flow", {}),
                setup_difficulty=combo.get("setup_difficulty", "Medium"),
                total_monthly_cost=combo.get("total_monthly_cost", 0),
                why_this_combo=combo.get("why_this_combo", ""),
                expected_outcome=combo.get("expected_outcome", ""),
            )
            self.db.add(combo_record)

        # Save roadmap stages
        for stage in roadmap:
            stage_record = RoadmapStage(
                analysis_id=analysis.id,
                stage_number=stage.get("stage_number", 0),
                stage_name=stage.get("stage_name", ""),
                duration_weeks=stage.get("duration_weeks", 0),
                tasks=stage.get("tasks", []),
                deliverables=stage.get("deliverables", []),
                metrics=stage.get("metrics", []),
                cost_this_stage=stage.get("cost_this_stage", 0),
            )
            self.db.add(stage_record)

        self.db.commit()

        logger.info(f"Analysis saved with ID: {analysis.id}")
        return analysis.id


# Convenience function
async def analyze_business(user_goal: str, user_id: int, db: Session) -> Dict:
    """
    Quick function to analyze business goal.

    Args:
        user_goal: User's business objective
        user_id: Current user ID
        db: Database session

    Returns:
        Complete analysis response
    """
    analyzer = BusinessAnalyzer(db)
    return await analyzer.analyze(user_goal, user_id)
