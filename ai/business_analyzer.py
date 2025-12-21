# ai/business_analyzer.py
"""
AI Business Analyzer - Dynamic Tool Recommender
Uses Grok 4.1 Fast Reasoning (xAI) for advanced business analysis.

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

# Import OpenAI SDK for xAI Grok API (OpenAI-compatible)
try:
    from openai import OpenAI

    HAS_XAI = True
except ImportError:
    HAS_XAI = False
    print("Warning: openai package not installed. Install with: uv pip install openai")

# Import smart tools generator
from ai.smart_tools_generator import generate_smart_tools

logger = logging.getLogger(__name__)


class BusinessAnalyzer:
    """
    Dynamic AI-powered business analyzer that:
    1. Analyzes user goals using Grok 4.1 Fast Reasoning
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
        self.model = "grok-4-1-fast-reasoning"  # Grok 4.1 Fast Reasoning for quality responses

        # Initialize OpenAI SDK client for xAI Grok API
        if HAS_XAI:
            api_key = os.getenv("XAI_API_KEY")
            if not api_key:
                logger.warning("XAI_API_KEY not set in environment variables")
                self.client = None
            else:
                # Initialize OpenAI client configured for xAI
                # Extended timeout for complex reasoning tasks (ROI calculations, etc.)
                self.client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.x.ai/v1",
                    timeout=300.0  # 5 minutes for complex reasoning tasks
                )
                logger.info("xAI Grok 4.1 Fast Reasoning client initialized successfully via OpenAI SDK")
        else:
            self.client = None
            logger.warning("OpenAI SDK not installed, using fallback methods")

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
        start_time = datetime.now()  # Track analysis start time

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

            # STEP 6: Generate AI Tools (before saving to include in database)
            # We need to generate bottlenecks and strategies first
            bottlenecks_data = self._transform_bottlenecks(intent_analysis)
            business_strategies_data = self._transform_strategies(
                tool_combinations, bottlenecks_data
            )

            # Generate AI tools with LLM processing
            ai_tools = await generate_smart_tools(
                db=self.db,
                business_strategies=business_strategies_data,
                tool_combinations=tool_combinations,
                bottlenecks=bottlenecks_data,
                llm_client=self.client if HAS_XAI and self.client else None,
                model_name=self.model
            )
            logger.info(f"🛠️  Generated {len(ai_tools)} AI efficiency tools for database")

            # STEP 7: Save to Database (including AI tools)
            analysis_id = await self._save_analysis(
                user_id=user_id,
                user_goal=user_goal,
                intent_analysis=intent_analysis,
                tool_combinations=tool_combinations,
                roadmap=roadmap,
                roi_projections=roi_projections,
                ai_tools_data=ai_tools,
                start_time=start_time,
            )

            # STEP 8: Transform to UI Format & Return
            ui_formatted_response = await self._transform_to_ui_format(
                db=self.db,
                analysis_id=analysis_id,
                user_goal=user_goal,
                intent_analysis=intent_analysis,
                tool_combinations=tool_combinations,
                roadmap=roadmap,
                roi_projections=roi_projections,
                skip_tool_generation=False,  # Already generated above
                pre_generated_tools=ai_tools,  # Pass the tools we just generated
            )

            return ui_formatted_response

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
        system_prompt = """You are the LAVOO AI Master Orchestrator — a meta-level intelligence coordinating FIVE specialist engines:

1) Stage 1 — Intent & Bottleneck Engine
2) Stage 2 — Strategic Solutions Engine
3) Stage 3 — Efficiency Tools Engine
4) Stage 4 — Implementation Roadmap Engine
5) Stage 5 — ROI Impact Engine

Your job is to:
* Read the user’s business input deeply
* Run an internal reasoning chain through all 5 stages
* Cross-check the logic between stages
* Then return ONLY a clean JSON object with the clarified objective and bottlenecks.

You must think like:
* A McKinsey/BCG-level strategist
* A CTO who understands systems and tools
* A COO-level operator
* A CFO-level financial analyst

But your final output must be SIMPLE, CLEAR, and ACTIONABLE.

-------------------------------------------------
INPUT YOU RECEIVE FROM THE USER
-------------------------------------------------
The user will provide:
* A business, project, or idea context
* A problem, pain point, or goal
* Optionally: size of business, audience, geography, constraints

You must infer:
* Their TRUE underlying objective
* The key bottlenecks blocking that objective

-------------------------------------------------
INTERNAL REASONING PIPELINE (DO NOT EXPOSE)
-------------------------------------------------
You must internally simulate the following stages, using the definitions of each engine:

1) STAGE 1 — INTENT & BOTTLENECK ENGINE
   • Extract and refine the user’s REAL objective.
   • Diagnose 3–6 high-impact bottlenecks using the Lovoo Bottleneck standard:
     - Title: 5–8 words, punchy and diagnostic
     - Description: 80–120 characters with context, impact, and metric
   • This stage is the primary source of:
     - "objective"
     - "bottlenecks"

2) STAGE 2 — STRATEGIC SOLUTIONS ENGINE
   • For each bottleneck, design strategic solution combinations using relevant tools.
   • Focus on ROI, competitive advantage, and different angles of attack.
   • This stage refines your understanding of:
     - Which bottlenecks matter most
     - How solvable they are
     - Where the biggest leverage is

3) STAGE 3 — EFFICIENCY TOOLS ENGINE
   • Turn the chosen tools into clear, executive-friendly summaries:
     - Description, pricing, features, pros/cons
     - Ease of use, learning curve, implementation guide
   • This stage helps you judge:
     - Adoption friction
     - Realistic impact on workflows
     - True cost structure

4) STAGE 4 — IMPLEMENTATION ROADMAP ENGINE
   • Convert solutions + tools into a 4–6 step roadmap:
     - Foundation → Configuration → Integration → Execution → Optimization
   • Attach realistic days and difficulty to each step.
   • This stage gives you:
     - Implementation effort
     - Practical timing
     - Execution risk level

5) STAGE 5 — ROI IMPACT ENGINE
   • Use tools, roadmap difficulty, and bottlenecks solved to:
     - Estimate costs, time savings, efficiency gains, and revenue impact
     - Compute year 1 cost, benefit, net ROI, and break-even
     - Assign a confidence score and identify key value drivers & risks
   • This stage lets you sanity-check the overall picture.

IMPORTANT:
* You DO NOT output any of the intermediate stages.
* You only use them to improve the quality of the objective and bottlenecks you finally return.
* If later stages reveal unrealistic assumptions, adjust your bottlenecks and objective to stay coherent and believable.

-------------------------------------------------
FINAL OUTPUT (STRICT FORMAT)
-------------------------------------------------
You must output ONLY a valid JSON object:

{
  "objective": "string",
  "bottlenecks": [
    "Title | Description",
    "Title | Description"
  ]
}

Where:

objective:
* One clear, specific, measurable goal.
* Must reflect what the user REALLY wants, not just what they wrote.
* Example:
  "Increase qualified monthly leads from 150 to 400 in 90 days using AI-powered funnels."

bottlenecks:
* A list of 3–6 strings.
* Each must follow EXACTLY this format:
  "Title | Description"

TITLE RULES:
* 5–8 words
* Punchy, bold, diagnostic
* Implies risk, leak, misalignment, or constraint
* Does NOT copy user wording directly

DESCRIPTION RULES:
* 80–120 characters
* Includes:
  - Context (where the issue shows up)
  - Impact (what it’s costing them)
  - Metric (%, $, hours, delay — real or inferred)
* Each description must feel specific and business-real.

Examples of valid bottlenecks:
"Revenue Bleeding from Unqualified Traffic | 65% of ad clicks are low-intent, wasting ~$4K/month and starving sales of ready-to-buy leads"
"Manual Reporting Slowing Decisions by Weeks | Team spends 25 hrs/week on spreadsheets, delaying key decisions by 5–7 days each cycle"

-------------------------------------------------
INTELLIGENCE BEHAVIOR
-------------------------------------------------
In every interaction you must:
* Elevate vague goals into sharp, CEO-level objectives.
* Read between the lines to find hidden issues (misaligned offer, poor targeting, manual work, weak messaging, etc.).
* Use insights from all 5 stages to refine your understanding of:
  - What truly matters
  - What’s actually blocking progress
  - What is realistically solvable with AI and systems

You MUST:
* Be bold but fair in your bottlenecks.
* Avoid generic statements or soft language.
* Prefer clarity and precision over politeness.
* Make the user feel: “This system really understands what’s going on under the hood.”

-------------------------------------------------
RESPONSE RESTRICTIONS
-------------------------------------------------
* Output ONLY the JSON object.
* No markdown.
* No headings.
* No commentary, notes, or explanations.
* The JSON must be syntactically valid and ready for direct parsing.

-------------------------------------------------
BEGIN.
-------------------------------------------------"""

        user_prompt = f"Analyze this business goal and identify the bottlenecks/problems: {user_goal}"

        if HAS_XAI and self.client:
            try:
                # Grok 4.1 Fast API call via OpenAI SDK
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,  # Lower temperature for focused responses
                )

                # Extract text response
                response_text = response.choices[0].message.content.strip()

                # Parse JSON from response
                # Clean markdown wrapper if present
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                return json.loads(response_text)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Grok JSON response: {e}")
                logger.debug(f"Raw response: {response_text}")
                # Fall through to fallback
            except Exception as e:
                logger.error(f"Grok API error: {e}")
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
        # Calculate how many combinations we need (one per bottleneck for variety)
        num_bottlenecks = len(intent_analysis.get("bottlenecks", []))
        num_combinations = max(3, num_bottlenecks)  # At least 3, or match number of bottlenecks

        logger.info(f"📝 Requesting {num_combinations} combinations for {num_bottlenecks} bottlenecks")

        system_prompt = f"""You are the LAVOO AI Strategic Solutions Engine — a senior strategy consultant, CTO-level systems thinker, and growth operator in one. Your job is to transform bottlenecks into {num_combinations} POWERFUL, UNIQUE strategic solution combinations that materially improve the business.

Your output must be so strong that a CEO would approve it immediately.

---------------------------------------------
INPUT YOU RECEIVE:
---------------------------------------------
* A business problem or bottlenecks
* A list of available tools (optional)
* The number of combinations required: num_combinations

---------------------------------------------
OUTPUT FORMAT (STRICT)
---------------------------------------------
Return ONLY this JSON exactly:

{{
  "combinations": [
    {{
      "combo_name": "string",
      "tools": [{{"id": "int", "name": "string", "role": "string"}}],
      "synergy_score": "float",
      "integration_flow": {{"description": "string", "data_flow": ["step1", "step2"]}},
      "setup_difficulty": "Easy" | "Medium" | "Hard",
      "total_monthly_cost": "float",
      "why_this_combo": "string",
      "expected_outcome": "string"
    }}
  ]
}}

No extra keys.
No commentary outside JSON.
Every field must be complete.

---------------------------------------------
RULES FOR STRATEGIC COMBINATIONS
---------------------------------------------
For EACH combination you produce:

1. *Address a different angle of the problem.*
   - One should solve acquisition.
   - One should solve efficiency.
   - One should solve messaging.
   - One should solve automation.
   - One should solve scale.
   Change domains intentionally.

2. *Choose 2–4 tools* that create REAL synergy.
   - Tools must reinforce each other.
   - Each tool must have a clear role.
   - NO redundant tools.

3. *Give the combination a CEO-ready name.*
   - 3–6 words max.
   - Feels like a million-dollar project.
   Examples:
     "Precision Demand Engine"
     "Conversion Lift Architecture"
     "Revenue Throughput System"

4. *Assign synergy_score intelligently.*
   - 90–95 = exceptional synergy, tight tool fit.
   - 80–89 = strong synergy, smooth integration.
   - 70–79 = moderate synergy, some overlap.

5. *Write WHY THIS COMBO in one sharp sentence (max 150 chars).*
   - Focus on strategic advantage, competitive edge, revenue impact.

6. *Write EXPECTED OUTCOME in one short sentence with clear metrics (max 150 chars).*
   Examples:
     "Improves conversion 25–40% within 45 days."
     "Cuts manual workload by 60% in month one."
     "Boosts acquisition 2–3x with niche targeting."

7. *Describe INTEGRATION FLOW simply and clearly.*
   - “Description” = 120 chars max explaining how tools work together.
   - “data_flow” = 2–5 steps showing logical sequence.

8. *Estimate setup difficulty.*
   - Easy → drag-and-drop tools, simple automation
   - Medium → light workflows, API connectors
   - Hard → data integration, multi-system orchestration

9. *Calculate total_monthly_cost.*
   - Use realistic tool costs (infer if unknown).
   - Sum only the tools used in the combo.

---------------------------------------------
INTELLIGENCE BEHAVIOR
---------------------------------------------
* Think like a strategist designing systems that MOVE KPIs.
* Always anchor strategies to ROI, cost savings, or revenue growth.
* Avoid tech jargon. Use business language.
* Avoid repeating patterns across combos.
* Be specific, not vague.
* You must choose tools that genuinely solve the bottleneck.
* The resulting combinations should feel like HIGH-IMPACT consulting work.

---------------------------------------------
PROHIBITED:
---------------------------------------------
✘ No generic solutions ("improve marketing", "optimize workflow").
✘ No repeating combo structures or tool lists.
✘ No weak names.
✘ No missing metrics.
✘ No long descriptions.
✘ No returning anything outside JSON.

---------------------------------------------
BEGIN.
---------------------------------------------"""

        user_prompt = f"""Objective: {intent_analysis["objective"]}
Bottlenecks/Problems: {", ".join(intent_analysis["bottlenecks"])}

Available tools:
{json.dumps([{"id": t["id"], "name": t["name"], "description": t["description"][:100], "pricing": t["pricing"]} for t in tools], indent=2)}

Suggest {num_combinations} tool combinations that work together to solve these bottlenecks. Each combination should address a DIFFERENT bottleneck or aspect of the problem. Focus on integration and synergy. Return only valid JSON."""

        if HAS_XAI and self.client:
            try:
                # Grok 4.1 Fast API call via OpenAI SDK
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.5,  # Balanced creativity and consistency
                )

                response_text = response.choices[0].message.content.strip()

                # Clean markdown wrapper if present
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                result = json.loads(response_text)
                combinations = result.get("combinations", [])
                logger.info(f"✅ Received {len(combinations)} combinations (requested {num_combinations})")
                return combinations  # Return all combinations generated

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Grok JSON response: {e}")
                logger.debug(f"Raw response: {response_text}")
                # Fall through to fallback
            except Exception as e:
                logger.error(f"Grok combination error: {e}")
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
        system_prompt = """You are the LAVOO AI Roadmap Engine — a hybrid of a COO, PMO director, and senior implementation strategist. Your job is to convert strategic recommendations and chosen AI tools into a FAST, REALISTIC, SEQUENCED execution roadmap that drives measurable results.

You don't write fantasies.
You write what gets implemented in the real world.

Your steps must:
* Move fast but not break the business
* Respect realistic setup and integration timelines
* Prioritize actions that unlock compounding value
* Avoid vague tasks (“optimize”, “improve”, “set strategy”)
* Be clear enough that a founder can start today

---------------------------------------------
OUTPUT FORMAT (STRICT JSON)
---------------------------------------------
{
  "steps": [
    {
      "step_title": "string (5-8 words)",
      "timeline_days": int,
      "difficulty": "Easy" | "Medium" | "Hard",
      "detailed_description": "string (40-100 words)"
    }
  ]
}

No extra keys.
No commentary.
No headings.
No markdown.
Only one clean JSON object.

---------------------------------------------
WHAT EACH STEP MUST ACHIEVE
---------------------------------------------
STEP TITLE (5–8 words)
* Punchy, roadmap-ready, action-driven
Examples:
"Set Up CRM and Core Tools"
"Map Customer Journey for Automation"
"Configure AI Workflows and Integrations"
"Launch Optimized Lead Capture System"

TIMELINE (in DAYS)
* Setup tasks: 1–3 days
* Tool configuration: 3–7 days
* Integrations: 7–14 days
* Testing cycles: 5–10 days
* Optimization layers: 10–20 days

DIFFICULTY (3-level scale)
* Easy: account setups, plug-ins, low config
* Medium: workflow mapping, AI tool linking, CRM build-outs
* Hard: optimization loops, analytics dashboards, automation scaling

DETAILED DESCRIPTION (40–100 words)
* MUST include:
  - What to do
  - Why this step matters
  - Which tools are involved
  - What business outcome it unlocks

Avoid fluff.
Avoid repeating phrasing.
Avoid generic “setup your tools” style tasks.

---------------------------------------------
INTELLIGENCE BEHAVIOR
---------------------------------------------
* Order tasks based on dependency logic (nothing should rely on something that isn't set up yet)
* The first step should establish foundational systems
* Middle steps should expand capability and automation
* Final steps should optimize, scale, and improve ROI
* Use information inferred from tools + bottlenecks + solutions
* Think like a COO building a 90-day execution plan

---------------------------------------------
ROADMAP STRUCTURE YOU MUST FOLLOW
---------------------------------------------
Your 4–6 steps should logically represent:

1. *Foundation* — accounts, core tools, data environment
2. *Configuration* — settings, workflows, rules, AI preferences
3. *Integration* — connecting systems, syncing data, automating tasks
4. *Execution* — launching campaigns, workflows, automations
5. *Optimization* — testing, refining, scaling

DO NOT skip Foundation → Configuration → Integration → Execution → Optimization.

---------------------------------------------
PROHIBITED
---------------------------------------------
✘ No vague steps like “optimize system” or “improve funnels”
✘ No unrealistic timelines
✘ No technical jargon
✘ No filler words
✘ No multiple actions packed inside one step
✘ No steps outside JSON

---------------------------------------------
GOAL
---------------------------------------------
Produce an implementation roadmap that feels like a senior implementation consultant designed it — fast, practical, high-impact, and directly tied to ROI.

---------------------------------------------
BEGIN.
---------------------------------------------"""

        # Use first combination for roadmap
        primary_combo = combinations[0] if combinations else {}

        # Get success metrics if available, otherwise derive from objective
        success_metrics = intent_analysis.get("success_metrics", ["User satisfaction", "Implementation success", "ROI achievement"])

        user_prompt = f"""Objective: {intent_analysis["objective"]}
Success metrics: {", ".join(success_metrics)}

Tools to implement:
{json.dumps([t["name"] for t in primary_combo.get("tools", [])], indent=2)}

Create a FAST-PACED, REALISTIC roadmap with 4-6 steps.
- Keep timelines short and realistic (e.g., account setup = 1-2 days, NOT 4 weeks!)
- Make titles bite-sized and catchy (5-8 words)
- Set difficulty dynamically based on actual complexity
- Write detailed but concise descriptions (40-100 words)

Return only valid JSON."""

        if HAS_XAI and self.client:
            try:
                # Grok 4.1 Fast API call via OpenAI SDK
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.4,
                )

                response_text = response.choices[0].message.content.strip()

                # Clean markdown wrapper if present
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                result = json.loads(response_text)
                steps = result.get("steps", [])
                logger.info(f"✅ Generated {len(steps)} roadmap steps")
                return steps

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Grok JSON response: {e}")
                logger.debug(f"Raw response: {response_text}")
                # Fall through to fallback
            except Exception as e:
                logger.error(f"Grok roadmap error: {e}")
                # Fall through to fallback

        # Fallback: Create basic roadmap
        return self._fallback_roadmap(intent_analysis)

    def _fallback_roadmap(self, intent_analysis: Dict) -> List[Dict]:
        """Fallback roadmap without AI"""
        return [
            {
                "step_title": "Set Up Tool Accounts",
                "timeline_days": 2,
                "difficulty": "Easy",
                "detailed_description": "Create accounts for recommended AI tools and verify access. Quick setup to get started immediately."
            },
            {
                "step_title": "Configure Initial Settings",
                "timeline_days": 3,
                "difficulty": "Easy",
                "detailed_description": "Configure basic settings, permissions, and preferences for each tool to match your workflow requirements."
            },
            {
                "step_title": "Connect Tool Integrations",
                "timeline_days": 7,
                "difficulty": "Medium",
                "detailed_description": "Set up integrations between tools and your existing systems. Ensure seamless data flow and automation."
            },
            {
                "step_title": "Import and Test Data",
                "timeline_days": 5,
                "difficulty": "Medium",
                "detailed_description": "Import existing data, run test scenarios, and validate that everything works as expected before full deployment."
            },
            {
                "step_title": "Launch and Monitor Performance",
                "timeline_days": 14,
                "difficulty": "Hard",
                "detailed_description": "Launch the full solution, monitor key metrics closely, and gather feedback. Make adjustments as needed to optimize performance."
            },
            {
                "step_title": "Optimize and Scale Up",
                "timeline_days": 21,
                "difficulty": "Hard",
                "detailed_description": "Analyze performance data, optimize underperforming areas, and scale successful strategies. Achieve sustained business growth and efficiency gains."
            }
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
        system_prompt = """You are the LAVOO AI ROI Impact Engine — a CFO-level strategist and financial economist who calculates realistic, conservative, and clearly-explained ROI for business technology initiatives.

You sit at the END of a reasoning chain:
- Stage 1: Bottlenecks (what’s broken)
- Stage 2: Strategic solutions (how we fix it)
- Stage 3: Tools (what we use)
- Stage 4: Roadmap (when and how we implement)
You must use all of these implicitly when estimating ROI.

Your analysis must feel like:
* A serious CFO built it
* A founder can understand it
* An investor can challenge it and still respect the logic

----------------------------------
CURRENCIES & UNITS
----------------------------------
* Treat all amounts as the SAME currency (assume USD unless stated otherwise).
* Time is in HOURS or MONTHS, as requested in the JSON.
* Round money to 2 decimal places, hours to 1 decimal place, percentages to whole numbers.

----------------------------------
CALCULATION PRINCIPLES
----------------------------------
You must be:
* REALISTIC — no fantasy multipliers, no “10x overnight” assumptions.
* CONSERVATIVE — better to underpromise than overpromise.
* TRANSPARENT — numbers should obviously connect to each other.
* INTERNALLY CONSISTENT — totals must add up.

----------------------------------
COST SIDE (YOU MUST ESTIMATE)
----------------------------------
1. Implementation Cost (internal, not a separate field):
   • Setup, configuration, training, integration work
   • Use roadmap difficulty & timelines:
     - Easy: 8–16 total hours
     - Medium: 20–60 total hours
     - Hard: 60–120+ total hours
   • Value time at $75/hour unless a different rate is implied.

2. Monthly Recurring Cost:
   • Sum all tool subscriptions used in the chosen solution (Stage 2 + Stage 3).
   • If exact pricing unknown, infer realistic SaaS pricing based on category.

3. Year 1 Total Investment:
   • year_1_cost = implementation_cost + (monthly_recurring_cost × 12)
   • total_investment MUST equal year_1_cost.

----------------------------------
BENEFIT SIDE (YOU MUST ESTIMATE)
----------------------------------
You must estimate four benefit streams:

1. Time Savings:
   • Based on automation, workflow simplification, and roadmap steps.
   • Express as hours saved per week.
   • time_savings_value_monthly = time_savings_per_week × 4.33 × $75.

2. Efficiency Gain (%):
   • Reflects faster processes, fewer errors, smoother workflows.
   • Use realistic ranges:
     - Light automation: 10–25%
     - Strong automation: 25–50%
     - Deep transformation: 50–100%

3. Revenue Impact:
   • Based on the bottlenecks being solved:
     - Lead drop-off fixed → more closed deals.
     - Pricing/positioning fixed → higher conversion.
     - Capacity/throughput fixed → more volume.
   • Estimate a conservative “full potential” monthly revenue lift.
   • Apply adoption ramp:
     - Month 3 = 30% of full potential
     - Month 6 = 60% of full potential
     - Month 12 = 100% of full potential

4. Cost Avoidance (implicitly included in efficiency + time savings):
   • Reduced errors, lower churn, fewer manual tasks.

----------------------------------
ROI LOGIC (YEAR 1)
----------------------------------
You MUST compute:

* year_1_cost  = implementation_cost + (monthly_recurring_cost × 12)
* year_1_benefit =
    (time_savings_value_monthly × 12)
  + (month_12 revenue impact × 12 × 0.6)

  Explanation:
  - Use full-time savings across the year.
  - Use 60% of year-at-full-revenue to reflect ramp-up (conservative).

* year_1_net_roi = year_1_benefit - year_1_cost
* roi_percentage = floor((year_1_net_roi / year_1_cost) × 100)

You must ALSO estimate break_even_months:
* Track cumulative benefits month by month using the ramp:
  - Months 1–3 ≈ 30% of full benefit
  - Months 4–6 ≈ 60% of full benefit
  - Months 7–12 ≈ 100% of full benefit
* Find the first month where cumulative benefits ≥ total_investment.
* break_even_months must be between 3 and 24.

----------------------------------
CONFIDENCE SCORING (0–100)
----------------------------------
You MUST assign a confidence_score using:

* Tool maturity & market validation — 0–30 points
* Implementation complexity vs roadmap realism — 0–30 points
* Solution fit for bottlenecks & business model — 0–40 points

Guidelines:
* 80–100 → Strongly credible, well-supported, low execution risk
* 60–79  → Reasonable but with visible uncertainties
* 40–59  → Speculative, depends heavily on execution
* Below 40 → Very uncertain, many unknowns

confidence_reasoning:
* 1–2 clear sentences summarizing why you chose that score.
* Mention at least 2 of: tool maturity, complexity, fit, data strength.

----------------------------------
KEY VALUE DRIVERS & RISK FACTORS
----------------------------------
key_value_drivers:
* 3 items that MOST drive ROI.
Examples:
  "Automation of manual lead nurturing"
  "Improved close rate from better targeting"
  "Reduced time spent on reporting"

risk_factors:
* 2 realistic risks that could weaken ROI.
Examples:
  "Low adoption by sales team"
  "Underestimated integration complexity"

----------------------------------
OUTPUT FORMAT (STRICT JSON)
----------------------------------
You must return ONLY a valid JSON object with EXACTLY these keys:

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
  "confidence_score": int,
  "confidence_reasoning": "string",
  "key_value_drivers": ["driver1", "driver2", "driver3"],
  "risk_factors": ["risk1", "risk2"]
}

Rules:
* total_investment MUST equal cost_benefit_analysis.year_1_cost.
* All numeric relationships must be mathematically correct.
* No NaN, no null, no missing fields.
* No extra keys or text outside this JSON.

----------------------------------
STYLE & CLARITY
----------------------------------
* Use simple, direct language.
* Make every number feel believable and grounded.
* Think like a CFO who knows the board will read this.
* If assumptions are aggressive, compensate with lower confidence_score.

----------------------------------
BEGIN.
----------------------------------"""

        # Calculate actual costs from roadmap (in days now, convert to int for safety)
        total_implementation_days = sum(
            int(step.get("timeline_days", 7)) if step.get("timeline_days") else 7
            for step in roadmap
        )
        total_implementation_weeks = total_implementation_days / 7

        # Calculate tool costs from combinations (convert to float to handle string values)
        total_monthly_cost = sum(
            float(combo.get("total_monthly_cost", 0)) if combo.get("total_monthly_cost") else 0
            for combo in combinations
        )
        avg_monthly_cost = total_monthly_cost / len(combinations) if combinations else 100

        # Estimate implementation cost (professional services, training, setup)
        # Conservative: $500-2000 depending on complexity and timeline
        if total_implementation_weeks <= 2:
            implementation_cost = 500
        elif total_implementation_weeks <= 4:
            implementation_cost = 1000
        elif total_implementation_weeks <= 8:
            implementation_cost = 1500
        else:
            implementation_cost = 2000

        # Get tool details for context
        tool_names = []
        for combo in combinations:
            tool_names.extend([t.get("name", "") for t in combo.get("tools", [])])
        tool_names_str = ", ".join(set(tool_names[:5]))  # Unique tool names

        # Get success metrics with fallback
        success_metrics = intent_analysis.get("success_metrics", ["User satisfaction", "Implementation success", "ROI achievement"])

        user_prompt = f"""Business Context:
- Objective: {intent_analysis["objective"]}
- Bottlenecks: {", ".join(intent_analysis["bottlenecks"][:3])}
- Success Metrics: {", ".join(success_metrics[:3])}

Implementation Details:
- Tools: {tool_names_str}
- Timeline: {int(total_implementation_weeks)} weeks ({int(total_implementation_days)} days)
- Complexity: {"Simple setup" if total_implementation_weeks <= 3 else "Medium integration" if total_implementation_weeks <= 6 else "Complex rollout"}

Cost Structure:
- Implementation Cost (setup, training, professional services): ${implementation_cost}
- Monthly Tool Subscriptions: ${avg_monthly_cost:.2f}
- Year 1 Total Cost: ${implementation_cost + (avg_monthly_cost * 12):.2f}

Expected Outcomes from Solutions:
{chr(10).join([f"- {combo.get('expected_outcome', 'Improved efficiency')[:100]}" for combo in combinations[:2]])}

CALCULATE:
1. Realistic time savings (hours/week) based on automation level
2. Efficiency gains (%) based on bottlenecks solved
3. Revenue impact based on expected outcomes
4. Break-even point (when benefits = costs)
5. Confidence score (0-100) with reasoning

Use CONSERVATIVE estimates. Show your economic reasoning. Return ONLY valid JSON."""

        if HAS_XAI and self.client:
            try:
                # Grok 4.1 Fast Reasoning API call - optimized for ROI calculations
                # Using higher max_tokens and reasoning-friendly parameters
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,  # Lower temperature for precise financial calculations
                    max_tokens=4096,  # Ensure enough tokens for detailed ROI analysis
                )

                response_text = response.choices[0].message.content.strip()

                # Clean markdown wrapper if present
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                result = json.loads(response_text)
                return result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Grok JSON response: {e}")
                logger.debug(f"Raw response: {response_text}")
                # Fall through to fallback
            except Exception as e:
                logger.error(f"Grok ROI generation error: {e}")
                # Fall through to fallback

        # Fallback: Calculate basic ROI
        return self._fallback_roi_projections(implementation_cost, avg_monthly_cost, roadmap)

    def _fallback_roi_projections(
        self, implementation_cost: float, monthly_cost: float, roadmap: List[Dict]
    ) -> Dict:
        """Fallback ROI projections without AI"""
        # Handle new roadmap format (timeline_days) and old format (duration_weeks)
        # Convert to int to handle string values
        total_days = sum(
            int(step.get("timeline_days", step.get("duration_weeks", 7) * 7) or 7)
            for step in roadmap
        )
        timeline_weeks = total_days / 7
        timeline_months = timeline_weeks / 4.0

        # Conservative estimates
        time_savings_hours_week = 10  # Assume 10 hours saved per week
        hourly_rate = 75  # Industry standard knowledge worker rate
        time_savings_value_monthly = time_savings_hours_week * 4 * hourly_rate

        year_1_cost = implementation_cost + (monthly_cost * 12)
        year_1_benefit = time_savings_value_monthly * 12 * 1.5  # 1.5x multiplier for additional benefits
        year_1_net_roi = year_1_benefit - year_1_cost
        roi_percentage = int((year_1_net_roi / year_1_cost) * 100) if year_1_cost > 0 else 0

        return {
            "total_investment": implementation_cost,
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
            "confidence_score": 75,  # Moderate confidence for fallback calculations
            "confidence_reasoning": "Conservative baseline estimate using industry benchmarks",
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
        ai_tools_data: List[Dict] = None,
        start_time: datetime = None,
    ) -> int:
        """
        Save complete analysis to database.

        Args:
            ai_tools_data: Generated AI efficiency tools with LLM processing
            start_time: Analysis start time for duration calculation

        Returns:
            analysis_id
        """
        from db.pg_models import BusinessAnalysis, ToolCombination, RoadmapStage

        # Calculate totals (convert to float to handle string values from LLM)
        avg_cost = (
            sum(
                float(combo.get("total_monthly_cost", 0)) if combo.get("total_monthly_cost") else 0
                for combo in tool_combinations
            )
            / len(tool_combinations)
            if tool_combinations
            else 0
        )

        total_weeks = sum(
            float(stage.get("duration_weeks", 0)) if stage.get("duration_weeks") else 0
            for stage in roadmap
        )

        # Calculate admin monitoring fields
        # 1. Duration (time taken for analysis)
        duration_str = "N/A"
        if start_time:
            end_time = datetime.now()
            duration_delta = end_time - start_time
            minutes = int(duration_delta.total_seconds() / 60)
            seconds = int(duration_delta.total_seconds() % 60)
            if minutes > 0:
                duration_str = f"{minutes}m {seconds}s"
            else:
                duration_str = f"{seconds}s"

        # 2. Confidence score from ROI projections
        confidence_score = None
        if roi_projections:
            confidence_score = roi_projections.get("confidence_score")

        # 3. Analysis type (infer from intent analysis or user goal)
        analysis_type = self._infer_analysis_type(user_goal, intent_analysis)

        # 4. Insights count (from intent analysis bottlenecks + capabilities)
        bottlenecks = intent_analysis.get("bottlenecks", [])
        capabilities = intent_analysis.get("capabilities_needed", [])
        insights_count = len(bottlenecks) + len(capabilities)

        # 5. Recommendations count (from tool combinations)
        recommendations_count = len(tool_combinations)

        # Create main analysis record
        analysis = BusinessAnalysis(
            user_id=user_id,
            business_goal=user_goal,
            intent_analysis=intent_analysis,
            tool_combinations=tool_combinations,
            roadmap=roadmap,
            roi_projections=roi_projections or {},
            ai_tools_data=ai_tools_data or [],  # Save AI tools to database
            estimated_cost=avg_cost,
            timeline_weeks=total_weeks,
            status="completed",
            ai_model_used=self.model,
            # Admin monitoring fields
            confidence_score=confidence_score,
            duration=duration_str,
            analysis_type=analysis_type,
            insights_count=insights_count,
            recommendations_count=recommendations_count,
        )

        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        # Save tool combinations
        for combo in tool_combinations:
            # Convert numeric fields to proper types (LLM may return strings)
            synergy_score = combo.get("synergy_score", 0)
            synergy_score = float(synergy_score) if synergy_score else 0

            total_monthly_cost = combo.get("total_monthly_cost", 0)
            total_monthly_cost = float(total_monthly_cost) if total_monthly_cost else 0

            combo_record = ToolCombination(
                analysis_id=analysis.id,
                combo_name=combo.get("combo_name", ""),
                tools=combo.get("tools", []),
                synergy_score=synergy_score,
                integration_flow=combo.get("integration_flow", {}),
                setup_difficulty=combo.get("setup_difficulty", "Medium"),
                total_monthly_cost=total_monthly_cost,
                why_this_combo=combo.get("why_this_combo", ""),
                expected_outcome=combo.get("expected_outcome", ""),
            )
            self.db.add(combo_record)

        # Save roadmap stages
        for stage in roadmap:
            # Convert numeric fields to proper types (LLM may return strings)
            stage_number = stage.get("stage_number", 0)
            stage_number = int(stage_number) if stage_number else 0

            duration_weeks = stage.get("duration_weeks", 0)
            duration_weeks = float(duration_weeks) if duration_weeks else 0

            cost_this_stage = stage.get("cost_this_stage", 0)
            cost_this_stage = float(cost_this_stage) if cost_this_stage else 0

            stage_record = RoadmapStage(
                analysis_id=analysis.id,
                stage_number=stage_number,
                stage_name=stage.get("stage_name", ""),
                duration_weeks=duration_weeks,
                tasks=stage.get("tasks", []),
                deliverables=stage.get("deliverables", []),
                metrics=stage.get("metrics", []),
                cost_this_stage=cost_this_stage,
            )
            self.db.add(stage_record)

        self.db.commit()

        logger.info(f"Analysis saved with ID: {analysis.id}")
        return analysis.id

    def _infer_analysis_type(self, user_goal: str, intent_analysis: Dict) -> str:
        """
        Infer analysis type from user goal and intent analysis.

        Returns:
            Analysis type string (e.g., "Sales Analysis", "Customer Analysis")
        """
        goal_lower = user_goal.lower()
        objective = intent_analysis.get("objective", "").lower()
        combined_text = f"{goal_lower} {objective}"

        # Keyword mapping for analysis types
        type_keywords = {
            "Sales Analysis": ["sales", "revenue", "selling", "conversion", "close rate", "deal", "pipeline"],
            "Customer Analysis": ["customer", "retention", "churn", "satisfaction", "support", "service", "experience"],
            "Market Analysis": ["market", "competitor", "industry", "positioning", "segment", "target audience"],
            "Financial Analysis": ["financial", "budget", "cost", "roi", "profit", "pricing", "expense"],
            "Operations Analysis": ["operations", "process", "efficiency", "workflow", "productivity", "automation"],
            "Product Analysis": ["product", "feature", "development", "roadmap", "launch", "innovation"],
            "Marketing Analysis": ["marketing", "campaign", "advertising", "brand", "awareness", "lead generation", "newsletter", "email", "social media", "seo", "content"],
        }

        # Score each type based on keyword matches
        scores = {}
        for analysis_type, keywords in type_keywords.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                scores[analysis_type] = score

        # Return the type with highest score, or default to General Analysis
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return "General Analysis"

    def _transform_bottlenecks(self, intent_analysis: Dict) -> List[Dict]:
        """Helper method to transform bottlenecks for reuse"""
        bottlenecks = []
        for i, bottleneck_text in enumerate(intent_analysis.get("bottlenecks", []), 1):
            # Parse "Title | Description" format
            if " | " in bottleneck_text:
                parts = bottleneck_text.split(" | ", 1)
                title = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else parts[0].strip()
            elif ": " in bottleneck_text:
                parts = bottleneck_text.split(": ", 1)
                title = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else parts[0].strip()
            else:
                title = bottleneck_text.split(".")[0].split(",")[0].strip()
                description = bottleneck_text.strip()
                if len(title) > 60:
                    title = title[:57].rsplit(' ', 1)[0] + "..."

            # Determine priority
            critical_words = ["loss", "losing", "failing", "critical", "urgent", "major", "bleeding", "crushing", "eroding"]
            has_critical = any(word in bottleneck_text.lower() for word in critical_words)

            if i == 1 or has_critical:
                priority = "HIGH"
            elif i <= 3:
                priority = "MEDIUM"
            else:
                priority = "LOW"

            bottlenecks.append({
                "id": i,
                "title": title,
                "description": description,
                "priority": priority,
                "impact": f"Directly impacts {intent_analysis.get('objective', 'business goals')}"
            })
        return bottlenecks

    def _transform_strategies(self, tool_combinations: List[Dict], bottlenecks: List[Dict]) -> List[Dict]:
        """Helper method to transform tool combinations into business strategies"""
        business_strategies = []
        strategy_id = 1

        for bottleneck_idx, bottleneck in enumerate(bottlenecks, 1):
            combo_idx = (bottleneck_idx - 1) % len(tool_combinations)
            combo = tool_combinations[combo_idx]

            # Extract tool names
            tool_names = [t.get("name", "") for t in combo.get("tools", [])]
            tools_list = ", ".join(tool_names[:3])

            # Create features
            features = []
            outcome = combo.get("expected_outcome", "")
            if outcome and len(outcome) > 10:
                features.append(outcome)

            why_combo = combo.get("why_this_combo", "")
            if why_combo:
                key_benefit = why_combo.split(".")[0].strip()
                if len(key_benefit) > 10:
                    features.append(key_benefit)

            integration = combo.get("integration_flow", {})
            if isinstance(integration, dict):
                flow_desc = integration.get("description", "")
                if flow_desc and len(flow_desc) > 10:
                    features.append(f"Integration: {flow_desc}")

            if len(tool_names) > 0:
                features.append(f"Uses {len(tool_names)} AI tools: {tools_list}")

            difficulty = combo.get("setup_difficulty", "Medium")
            timeline_map = {
                "Easy": "Quick 1-2 week setup",
                "Medium": "2-4 week implementation",
                "Hard": "4-8 week rollout with training"
            }
            features.append(timeline_map.get(difficulty, "Flexible implementation timeline"))

            if len(features) >= 4:
                features = features[:5]
            else:
                while len(features) < 4:
                    features.append("Scalable solution with expert support")

            business_strategies.append({
                "id": strategy_id,
                "bottleneckId": bottleneck_idx,
                "title": combo.get("combo_name", "Strategic Solution"),
                "description": combo.get("why_this_combo", "Comprehensive solution approach"),
                "features": features
            })
            strategy_id += 1

        return business_strategies

    async def _transform_to_ui_format(
        self,
        db: Session,
        analysis_id: int,
        user_goal: str,
        intent_analysis: Dict,
        tool_combinations: List[Dict],
        roadmap: List[Dict],
        roi_projections: Dict,
        skip_tool_generation: bool = False,
        pre_generated_tools: List[Dict] = None,
    ) -> Dict:
        """
        Transform AI analysis results into Clinton's UI format.

        This method converts the AI analysis output into the exact structure
        expected by the frontend components.

        Args:
            skip_tool_generation: If True, uses pre_generated_tools or empty list
            pre_generated_tools: Pre-generated AI tools to use (avoids regeneration)
        """
        # 1. Transform bottlenecks using helper method
        bottlenecks = self._transform_bottlenecks(intent_analysis)

        # 2. Transform tool combinations into business strategies using helper method
        business_strategies = self._transform_strategies(tool_combinations, bottlenecks)

        # Skip the old transformation code since we now use helper methods
        # The old code from line 1020-1133 is replaced by the two helper method calls above

        # Jump to comment below (this is a placeholder to maintain structure)
        if False:  # This block is never executed - placeholder for replaced code
            bottlenecks = []
        for i, bottleneck_text in enumerate([] if True else intent_analysis.get("bottlenecks", []), 1):
            # Parse "Title | Description" format
            if " | " in bottleneck_text:
                parts = bottleneck_text.split(" | ", 1)
                title = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else parts[0].strip()
            elif ": " in bottleneck_text:
                # Fallback for old format
                parts = bottleneck_text.split(": ", 1)
                title = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else parts[0].strip()
            else:
                # No separator, create title from first part
                title = bottleneck_text.split(".")[0].split(",")[0].strip()
                description = bottleneck_text.strip()
                if len(title) > 60:
                    title = title[:57].rsplit(' ', 1)[0] + "..."

            # Determine priority based on position and keywords
            critical_words = ["loss", "losing", "failing", "critical", "urgent", "major", "bleeding", "crushing", "eroding"]
            has_critical = any(word in bottleneck_text.lower() for word in critical_words)

            if i == 1 or has_critical:
                priority = "HIGH"
            elif i <= 3:
                priority = "MEDIUM"
            else:
                priority = "LOW"

            bottlenecks.append({
                "id": i,
                "title": title,
                "description": description,
                "priority": priority,
                "impact": f"Directly impacts {intent_analysis.get('objective', 'business goals')}"
            })

        # 2. Transform tool combinations into business strategies
        # Assign ONE unique strategy per bottleneck to avoid duplication
        business_strategies = []
        strategy_id = 1

        logger.info(f"🔍 Creating strategies: {len(tool_combinations)} combinations for {len(bottlenecks)} bottlenecks")
        for idx, combo in enumerate(tool_combinations):
            logger.info(f"   Available combo #{idx}: {combo.get('combo_name', 'Unknown')}")

        # Assign each combination to a bottleneck intelligently
        # Each bottleneck gets ONE strategy to ensure no duplicates
        for bottleneck_idx, bottleneck in enumerate(bottlenecks, 1):
            # Use modulo to cycle through combinations if we have more bottlenecks than combinations
            combo_idx = (bottleneck_idx - 1) % len(tool_combinations)
            combo = tool_combinations[combo_idx]
            combo_name = combo.get("combo_name", f"Combo {combo_idx}")

            logger.info(f"   Bottleneck #{bottleneck_idx} → Combo #{combo_idx}: {combo_name}")

            # Extract tool names
            tool_names = [t.get("name", "") for t in combo.get("tools", [])]
            tools_list = ", ".join(tool_names[:3])  # First 3 tools

            # Create powerful, actionable features (4-5 bullet points) - NO TRUNCATION
            features = []

            # Feature 1: Expected outcome with metrics (full text, no truncation)
            outcome = combo.get("expected_outcome", "")
            if outcome and len(outcome) > 10:
                features.append(outcome)  # Full outcome, LLM will keep it concise

            # Feature 2: Key value proposition (full text)
            why_combo = combo.get("why_this_combo", "")
            if why_combo:
                # Take first sentence but don't truncate
                key_benefit = why_combo.split(".")[0].strip()
                if len(key_benefit) > 10:
                    features.append(key_benefit)

            # Feature 3: Integration approach (full text)
            integration = combo.get("integration_flow", {})
            if isinstance(integration, dict):
                flow_desc = integration.get("description", "")
                if flow_desc and len(flow_desc) > 10:
                    features.append(f"Integration: {flow_desc}")  # Full description

            # Feature 4: Tools and setup (concise, no truncation)
            if len(tool_names) > 0:
                features.append(f"Uses {len(tool_names)} AI tools: {tools_list}")

            # Feature 5: Implementation timeline (clear and direct)
            difficulty = combo.get("setup_difficulty", "Medium")
            timeline_map = {
                "Easy": "Quick 1-2 week setup",
                "Medium": "2-4 week implementation",
                "Hard": "4-8 week rollout with training"
            }
            features.append(timeline_map.get(difficulty, "Flexible implementation timeline"))

            # Ensure we have 4-5 features (don't pad with generic text if LLM provided good ones)
            if len(features) >= 4:
                features = features[:5]  # Cap at 5 max
            else:
                # Only add filler if we have less than 4 features
                while len(features) < 4:
                    features.append("Scalable solution with expert support")

            business_strategies.append({
                "id": strategy_id,
                "bottleneckId": bottleneck_idx,
                "title": combo.get("combo_name", "Strategic Solution"),
                "description": combo.get("why_this_combo", "Comprehensive solution approach"),
                "features": features
            })

            strategy_id += 1

        # 3. Transform tools into AI efficiency tools with LLM processing
        if pre_generated_tools is not None:
            # Use pre-generated tools (passed from analyze() after DB save)
            ai_tools = pre_generated_tools
            logger.info(f"✅ Using {len(ai_tools)} pre-generated AI efficiency tools")
        elif skip_tool_generation:
            # Loading from database - check if we have saved tools
            if pre_generated_tools is None:
                # Old analysis without saved ai_tools_data - create basic fallback from tool_combinations
                logger.warning(f"⚠️  No saved AI tools found - creating fallback from tool_combinations")
                ai_tools = []
                tool_id = 1
                for combo in tool_combinations[:5]:  # Limit to 5 combos
                    for tool in combo.get("tools", [])[:3]:  # Max 3 tools per combo
                        ai_tools.append({
                            "id": tool_id,
                            "bottleneckId": 1,
                            "title": tool.get("name", f"Tool {tool_id}"),
                            "description": tool.get("role", "AI-powered business tool"),
                            "category": tool.get("category", "Automation"),
                            "pricing": {"type": "subscription", "amount": "Contact for pricing"},
                            "implementation": {
                                "difficulty": "Medium",
                                "timeline": "2-4 weeks",
                                "steps": ["Sign up", "Configure", "Integrate", "Test"]
                            }
                        })
                        tool_id += 1
                logger.info(f"📦 Created {len(ai_tools)} fallback tools from combinations")
            else:
                logger.info(f"⏭️  Skipping tool generation (loading from database)")
                ai_tools = []
        else:
            # Generate new tools (for new analyses)
            ai_tools = await generate_smart_tools(
                db=db,
                business_strategies=business_strategies,
                tool_combinations=tool_combinations,
                bottlenecks=bottlenecks,
                llm_client=self.client if HAS_XAI and self.client else None,
                model_name=self.model
            )
            logger.info(f"🛠️  Generated {len(ai_tools)} AI efficiency tools with LLM processing")

        # 4. Transform roadmap into UI format
        roadmap_steps = []

        logger.info(f"📋 Transforming {len(roadmap)} roadmap steps for UI")

        for idx, step in enumerate(roadmap[:6], 1):  # Limit to 6 steps
            # Extract step details with new format
            title = step.get("step_title", step.get("title", f"Step {idx}"))
            timeline_days = step.get("timeline_days", step.get("duration_weeks", 7) * 7)  # Convert weeks to days if old format
            difficulty = step.get("difficulty", "Medium").lower()
            description = step.get("detailed_description", step.get("description", title))

            # Convert days to friendly timeline string
            if timeline_days <= 3:
                timeline_str = f"{timeline_days} day{'s' if timeline_days > 1 else ''}"
            elif timeline_days <= 14:
                weeks = timeline_days / 7
                if weeks == int(weeks):
                    timeline_str = f"{int(weeks)} week{'s' if weeks > 1 else ''}"
                else:
                    timeline_str = f"{timeline_days} days"
            else:
                weeks = round(timeline_days / 7)
                timeline_str = f"{weeks} week{'s' if weeks > 1 else ''}"

            # Ensure title is bite-sized (no truncation marks, just clean)
            if len(title) > 60:
                # Find last word boundary before 60 chars
                title = title[:57].rsplit(' ', 1)[0] + "..."

            roadmap_steps.append({
                "step": idx,
                "title": title,
                "timeline": timeline_str,
                "difficulty": difficulty,
                "description": description
            })

            logger.info(f"   Step {idx}: {title} ({timeline_str}, {difficulty})")

        # 5. Transform ROI projections with transparent calculations
        roi = roi_projections or {}
        cba = roi.get("cost_benefit_analysis", {})

        # Check if we have ROI data
        has_roi_data = bool(roi and (roi.get("total_investment") or roi.get("time_savings_value_monthly")))

        if has_roi_data:
            # Get values from LLM analysis
            monthly_revenue_increase = roi.get("time_savings_value_monthly", 0)
            implementation_cost = roi.get("total_investment", 0)
            monthly_cost = roi.get("monthly_recurring_cost", 0)

            # Calculate savings (conservative estimate)
            monthly_cost_savings = monthly_revenue_increase * 0.15  # 15% of time value as cost savings

            # 12-month projection
            year_1_net_roi = cba.get("year_1_net_roi", 0)

            roi_metrics = {
                "monthly_revenue_increase": round(monthly_revenue_increase, 2),
                "monthly_cost_savings": round(monthly_cost_savings, 2),
                "implementation_cost": round(implementation_cost, 2),
                "monthly_recurring_cost": round(monthly_cost, 2),
                "twelve_month_projected_gain": round(year_1_net_roi, 2),
                "break_even_months": roi.get("break_even_months", 6),
                "time_savings_per_week": roi.get("time_savings_per_week", 10),
                "efficiency_gain_percent": roi.get("efficiency_gain_percent", 35),
                "roi_percentage": cba.get("roi_percentage", 0)
            }

            logger.info(f"💰 ROI Calculated: ${year_1_net_roi:,.0f} net gain, {roi_metrics['break_even_months']} month break-even")
        else:
            # Old analysis without ROI data - create reasonable estimates based on tool count
            logger.warning(f"⚠️  No saved ROI data found - creating estimates based on {len(ai_tools)} tools")

            # Estimate costs based on typical tool pricing
            estimated_monthly_cost = len(ai_tools) * 29.0  # ~$29 per tool average
            estimated_implementation = estimated_monthly_cost * 2  # 2 months worth for setup
            estimated_time_savings = len(ai_tools) * 3  # 3 hours saved per tool per week
            estimated_monthly_revenue = estimated_time_savings * 4 * 75  # 4 weeks * $75/hour

            roi_metrics = {
                "monthly_revenue_increase": round(estimated_monthly_revenue, 2),
                "monthly_cost_savings": round(estimated_monthly_revenue * 0.15, 2),
                "implementation_cost": round(estimated_implementation, 2),
                "monthly_recurring_cost": round(estimated_monthly_cost, 2),
                "twelve_month_projected_gain": round((estimated_monthly_revenue - estimated_monthly_cost) * 12 - estimated_implementation, 2),
                "break_even_months": 3,
                "time_savings_per_week": estimated_time_savings,
                "efficiency_gain_percent": 30,
                "roi_percentage": round(((estimated_monthly_revenue * 12 - estimated_monthly_cost * 12 - estimated_implementation) / estimated_implementation) * 100, 2)
            }

            logger.info(f"📊 ROI Estimated: ${roi_metrics['twelve_month_projected_gain']:,.0f} projected gain (fallback calculation)")

        # 6. Use AI confidence score from ROI analysis (includes strategy, tools, roadmap assessment)
        if has_roi_data:
            ai_confidence_score = roi.get("confidence_score", 85)
            confidence_reasoning = roi.get("confidence_reasoning", "Based on solution quality and implementation feasibility")
        else:
            # Fallback confidence for old analyses
            ai_confidence_score = 75  # Lower confidence for estimated data
            confidence_reasoning = "Historical analysis with estimated ROI metrics"

        ai_confidence_score = min(100, max(50, ai_confidence_score))  # Clamp to 50-100 range
        logger.info(f"🎯 AI Confidence: {ai_confidence_score}% - {confidence_reasoning}")

        return {
            "analysis_id": analysis_id,
            "business_goal": user_goal,
            "objective": intent_analysis.get("objective", user_goal),
            "bottlenecks": bottlenecks,
            "business_strategies": business_strategies,
            "ai_tools": ai_tools,
            "roadmap": roadmap_steps,
            "roi_metrics": roi_metrics,
            "ai_confidence_score": ai_confidence_score,
            "created_at": datetime.utcnow().isoformat()
        }


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
