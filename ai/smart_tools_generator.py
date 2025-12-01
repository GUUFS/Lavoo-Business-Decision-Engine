"""
Smart AI Tools Generator with LLM Processing
Handles tool selection, summarization, and uniform formatting
"""
import json
import logging
from typing import Dict, List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def generate_smart_tools(
    db: Session,
    business_strategies: List[Dict],
    tool_combinations: List[Dict],
    bottlenecks: List[Dict],
    llm_client,
    model_name: str
) -> List[Dict]:
    """
    Generate smart AI efficiency tools with LLM processing.
    - Selects tools that align with each solution
    - LLM summarizes pricing, features, description
    - LLM generates dynamic comparison data
    - LLM creates implementation guide

    Args:
        db: Database session
        business_strategies: List of business strategies
        tool_combinations: Tool combinations from LLM
        bottlenecks: List of bottlenecks
        llm_client: OpenAI client for xAI
        model_name: Model to use

    Returns:
        List of AI tools with LLM-processed data
    """
    from db.pg_models import AITool as AIToolModel

    ai_tools = []
    tool_id = 1
    processed_tools = set()  # Track processed tools to avoid duplicates

    # Map each strategy to relevant tools
    for strategy in business_strategies:
        strategy_id = strategy["id"]
        bottleneck_id = strategy["bottleneckId"]
        strategy_title = strategy["title"]
        strategy_desc = strategy["description"]

        # Get tools for this strategy from combinations
        relevant_combo = None
        for combo in tool_combinations:
            if combo.get("combo_name") == strategy_title:
                relevant_combo = combo
                break

        if not relevant_combo:
            continue

        # Process each tool in the combination
        for tool_data in relevant_combo.get("tools", [])[:4]:  # Max 4 tools per strategy
            tool_name = tool_data.get("name", "")

            # Skip if already processed
            tool_key = f"{tool_name}_{bottleneck_id}"
            if tool_key in processed_tools:
                continue
            processed_tools.add(tool_key)

            # Get tool from database
            db_tool = db.query(AIToolModel).filter(
                AIToolModel.name.ilike(f"%{tool_name}%")
            ).first()

            if not db_tool:
                logger.warning(f"Tool '{tool_name}' not found in database")
                continue

            # Extract raw data from database
            raw_pricing = db_tool.pricing or "Contact for pricing"
            raw_features = db_tool.key_features or ""
            raw_description = db_tool.description or ""
            raw_pros = db_tool.pros or ""
            raw_cons = db_tool.cons or ""
            raw_integration = db_tool.compatibility_integration or ""

            # Use LLM to process and summarize the data
            processed_data = await process_tool_with_llm(
                llm_client=llm_client,
                model_name=model_name,
                tool_name=tool_name,
                raw_pricing=raw_pricing,
                raw_features=raw_features,
                raw_description=raw_description,
                raw_pros=raw_pros,
                raw_cons=raw_cons,
                raw_integration=raw_integration,
                strategy_context=strategy_desc,
                difficulty=relevant_combo.get("setup_difficulty", "Medium")
            )

            if not processed_data:
                continue

            # Build the tool object
            ai_tools.append({
                "id": tool_id,
                "bottleneckId": bottleneck_id,
                "title": tool_name,
                "description": processed_data["description"],
                "price": processed_data["pricing"],
                "rating": f"{int(db_tool.ratings * 10)}/100" if db_tool.ratings else "N/A",
                "features": processed_data["features"],
                "pros": processed_data["pros"],
                "cons": processed_data["cons"],
                "website": db_tool.url or "https://example.com",
                "comparison": processed_data["comparison"],
                "implementation": processed_data["implementation"]
            })

            tool_id += 1

    return ai_tools


async def process_tool_with_llm(
    llm_client,
    model_name: str,
    tool_name: str,
    raw_pricing: str,
    raw_features: str,
    raw_description: str,
    raw_pros: str,
    raw_cons: str,
    raw_integration: str,
    strategy_context: str,
    difficulty: str
) -> Dict:
    """
    Use LLM to process and summarize tool data for concise output.

    Returns dictionary with:
    - description: Concise simplified description
    - pricing: Simplified pricing
    - features: 4-5 key features
    - pros: 3-4 key advantages
    - cons: 2-3 main considerations
    - comparison: Dynamic comparison data
    - implementation: Dynamic implementation guide
    """
    system_prompt = """You are the LAVOO AI Efficiency Tools Engine — a hybrid of a CTO, business strategist, and technical analyst. Your job is to transform raw tool data into powerful, concise, executive-grade summaries that help decision-makers choose the right tools FAST.

Your summaries must reveal:
* What the tool actually does
* Where it creates efficiency
* Where it fits in a workflow
* How difficult it is to adopt
* Whether it is worth the cost

Do NOT write like a marketer.
Do NOT write like a developer.
Write like a senior consultant advising a CEO with limited time.

----------------------------------------
OUTPUT FORMAT (STRICT JSON ONLY)
----------------------------------------
{
  "description": "string",
  "pricing": "string",
  "features": ["feature1", "feature2", "feature3", "feature4"],
  "pros": ["pro1", "pro2", "pro3"],
  "cons": ["con1", "con2"],
  "comparison": {
    "pricing": "string",
    "easeOfUse": "X/10",
    "learningCurve": "Easy|Medium|Hard",
    "integration": "string"
  },
  "implementation": {
    "timeframe": "X days|weeks",
    "difficulty": "Easy|Medium|Hard",
    "steps": ["1. Step", "2. Step", "3. Step", "4. Step"],
    "requirements": ["requirement1", "requirement2"]
  }
}

Return only valid JSON. No text before or after.

----------------------------------------
RULES FOR EACH SECTION
----------------------------------------

DESCRIPTION:
* ONE sentence
* CEO-level clarity
* State the core job the tool performs
* Max 18–22 words
Examples:
"AI-powered search engine that delivers personalized, privacy-focused results across academic and general-web sources."

PRICING:
* Simple, scannable, no complexity
Examples:
"Free + Pro plans", "$12/mo starting", "Usage-based pricing", "Tiered subscriptions"

FEATURES (4–5 items):
* MUST be high-impact features
* MUST be scannable (5–8 words)
* No marketing fluff
Examples:
"AI-personalized search results"
"Browser extension integration"
"Access to peer-reviewed studies"

PROS (3–4 items):
* MUST be real advantages
* Focus on value, speed, relevance
Examples:
"3× faster research results"
"High accuracy on niche queries"

CONS (2–3 items):
* MUST be true trade-offs
* No scare tactics
Examples:
"Requires active internet connection"
"Limited free-tier capabilities"

----------------------------------------
COMPARISON RULES
----------------------------------------
This section helps CEOs decide QUICKLY.

pricing:
* Summarize relative cost ("Cheaper than X", "Mid-range", "Premium pricing")

easeOfUse:
* Return “X/10” (strict format)
* Consider UI simplicity + onboarding

learningCurve:
* Easy → beginner-friendly
* Medium → some setup needed
* Hard → technical configuration

integration:
* Summarize integration footprint (max 12 words)
Examples:
"Browser extension + cloud sync"
"API + CRM connectors"

----------------------------------------
IMPLEMENTATION SECTION
----------------------------------------
timeframe:
* Realistic adoption period (1 day, 3 days, 1 week)

difficulty:
* Easy | Medium | Hard (based on user effort)

steps (4):
* MUST be clear
* MUST be sequential
* MUST be actionable
Examples:
"1. Create account"
"2. Install browser plug-in"
"3. Configure preferences"
"4. Connect integrations"

requirements:
* 2–3 items
Examples:
"Stable internet", "Modern browser", "Team permissions"

----------------------------------------
INTELLIGENCE BEHAVIOR
----------------------------------------
* Prioritize conciseness AND clarity equally
* Drop all jargon — no filler wording
* Choose features that matter to decision-makers
* Compare tools objectively, not emotionally
* Summaries must feel like high-end consulting briefs
* Every line must help a CEO make a faster, better decision

----------------------------------------
PROHIBITED (NON-NEGOTIABLE)
----------------------------------------
✘ No marketing fluff
✘ No repeating phrases
✘ No informal language
✘ No long paragraphs
✘ No over-explaining
✘ No generic “good tool” statements
✘ No text outside JSON

----------------------------------------
BEGIN.
----------------------------------------"""

    user_prompt = f"""Tool: {tool_name}
Strategy Context: {strategy_context}

RAW DATA FROM DATABASE:
Pricing: {raw_pricing[:500]}
Features: {raw_features[:500]}
Description: {raw_description[:300]}
Pros: {raw_pros[:300]}
Cons: {raw_cons[:200]}
Integration: {raw_integration[:200]}

PROCESS this data into clean, concise summaries. Be brief but informative. Return ONLY valid JSON."""

    if llm_client:
        try:
            response = llm_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
            )

            response_text = response.choices[0].message.content.strip()

            # Clean markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)
            return result

        except Exception as e:
            logger.error(f"LLM tool processing error for {tool_name}: {e}")
            # Fall through to fallback

    # Fallback: Basic processing without LLM
    return fallback_tool_processing(
        tool_name, raw_pricing, raw_features, raw_description,
        raw_pros, raw_cons, difficulty
    )


def fallback_tool_processing(
    tool_name: str, raw_pricing: str, raw_features: str,
    raw_description: str, raw_pros: str, raw_cons: str, difficulty: str
) -> Dict:
    """Fallback tool processing without LLM"""
    # Parse without truncation
    features = [f.strip() for f in raw_features.split("|") if f.strip()][:5]
    pros = [p.strip() for p in raw_pros.split("|") if p.strip()][:4]
    cons = [c.strip() for c in raw_cons.split("|") if c.strip()][:3]

    # Ensure we have enough items
    while len(features) < 4:
        features.append("Powerful AI-driven capabilities")
    while len(pros) < 3:
        pros.append("Easy to implement and use")
    while len(cons) < 2:
        cons.append("Requires initial setup time")

    return {
        "description": (raw_description if raw_description else f"AI-powered {tool_name} solution"),
        "pricing": (raw_pricing if raw_pricing else "See website for pricing"),
        "features": features[:5],
        "pros": pros[:4],
        "cons": cons[:3],
        "comparison": {
            "pricing": "Multiple tiers available",
            "easeOfUse": "7/10",
            "learningCurve": difficulty,
            "integration": "API and integrations available"
        },
        "implementation": {
            "timeframe": "1-2 weeks",
            "difficulty": difficulty,
            "steps": [
                "1. Create account and configure settings",
                "2. Connect to existing systems via API",
                "3. Train team on key features and workflows",
                "4. Monitor performance and optimize usage"
            ],
            "requirements": ["Technical knowledge", "API access"]
        }
    }
