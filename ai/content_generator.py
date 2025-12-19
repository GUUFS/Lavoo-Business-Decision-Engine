# ai/content_generator.py
"""
AI Content Generator - Automated Insights & Opportunity Alerts
Uses Grok 4.1 with web search capabilities to find fresh business intelligence.

Workflow:
1. Grok searches the web for latest AI/Business news
2. Filters for relevant, actionable content
3. Formats into Insight or Alert structure
4. Checks for duplicates in database
5. Saves new content only
"""

import json
import logging
import os
import hashlib
import requests
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import func

# Load environment variables
load_dotenv('.env.local')

# Import OpenAI SDK for xAI Grok API
try:
    from openai import OpenAI
    HAS_XAI = True
except ImportError:
    HAS_XAI = False
    print("Warning: openai package not installed. Install with: pip install openai")

# Import database models
from db.pg_connections import SessionLocal, get_db
from db.pg_models import Insight, Alert

logger = logging.getLogger(__name__)

# Configure logging for standalone script execution
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class ContentGenerator:
    """
    AI-powered content generator that:
    1. Uses Grok 4.1 to search the web for fresh business/AI news
    2. Generates formatted Insights and Opportunity Alerts
    3. Avoids duplicates by checking existing content
    4. Stores new content in the database
    """

    def __init__(self, db_session: Session):
        """
        Initialize the content generator.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        # Use Grok 4 Fast with reasoning for web search capabilities
        self.model = "grok-4-fast-reasoning"  # Grok 4 Fast (with reasoning)
        self.today = date.today().strftime("%Y-%m-%d")

        # Initialize OpenAI SDK client for xAI Grok API
        if HAS_XAI:
            api_key = os.getenv("XAI_API_KEY")
            if not api_key:
                logger.warning("XAI_API_KEY not set in environment variables")
                self.client = None
            else:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.x.ai/v1",
                    timeout=180.0  # 3 minutes for web search
                )
                logger.info("xAI Grok client initialized for content generation")
        else:
            self.client = None
            logger.warning("OpenAI SDK not installed")

    def _get_existing_titles(self, content_type: str) -> set:
        """
        Get existing titles from database to prevent duplicates.

        Args:
            content_type: 'insight' or 'alert'

        Returns:
            Set of existing title hashes
        """
        if content_type == 'insight':
            titles = self.db.query(Insight.title).filter(Insight.is_active == True).all()
        else:
            titles = self.db.query(Alert.title).filter(Alert.is_active == True).all()

        # Create hash of titles for efficient comparison
        return {hashlib.md5(t[0].lower().encode()).hexdigest() for t in titles}

    def _get_existing_title_list(self, content_type: str) -> list:
        """
        Get list of existing titles to include in prompt for duplicate prevention.

        Args:
            content_type: 'insight' or 'alert'

        Returns:
            List of existing titles (most recent first)
        """
        if content_type == 'insight':
            titles = self.db.query(Insight.title).filter(
                Insight.is_active == True
            ).order_by(Insight.created_at.desc()).limit(30).all()
        else:
            titles = self.db.query(Alert.title).filter(
                Alert.is_active == True
            ).order_by(Alert.created_at.desc()).limit(30).all()

        return [t[0] for t in titles]

    def _is_duplicate(self, title: str, existing_hashes: set) -> bool:
        """Check if content with similar title already exists."""
        title_hash = hashlib.md5(title.lower().encode()).hexdigest()
        return title_hash in existing_hashes

    def _get_existing_urls(self, content_type: str) -> set:
        """
        Get set of existing URLs to prevent same article with different titles.

        Args:
            content_type: 'insight' or 'alert'

        Returns:
            Set of normalized URLs
        """
        if content_type == 'insight':
            urls = self.db.query(Insight.url).filter(Insight.is_active == True).all()
        else:
            urls = self.db.query(Alert.url).filter(Alert.is_active == True).all()

        # Normalize URLs (remove trailing slashes, query params) for comparison
        normalized_urls = set()
        for url_tuple in urls:
            url = url_tuple[0]
            # Remove trailing slash
            url = url.rstrip('/')
            # Remove query parameters
            url = url.split('?')[0]
            normalized_urls.add(url.lower())

        return normalized_urls

    def _is_duplicate_content(self, title: str, url: str, existing_title_hashes: set, existing_urls: set) -> tuple:
        """
        Check if content is duplicate based on both title AND URL.

        Args:
            title: Content title
            url: Content URL
            existing_title_hashes: Set of existing title hashes
            existing_urls: Set of existing normalized URLs

        Returns:
            Tuple of (is_duplicate: bool, reason: str)
        """
        # Check title duplicate
        title_hash = hashlib.md5(title.lower().encode()).hexdigest()
        if title_hash in existing_title_hashes:
            return (True, "duplicate title")

        # Check URL duplicate (normalize first)
        normalized_url = url.rstrip('/').split('?')[0].lower()
        if normalized_url in existing_urls:
            return (True, "duplicate URL")

        return (False, None)

    def _is_suspicious_url(self, url: str) -> bool:
        """
        Check if URL looks suspicious, fake, or is not a specific article.

        Returns True if URL appears to be fabricated or is a category/homepage.
        """
        url_lower = url.lower()

        # Check for obviously fake domains
        if 'example.com' in url_lower or 'placeholder' in url_lower:
            return True

        # Check for category/landing pages instead of specific articles
        category_indicators = [
            '/category/',
            '/categories/',
            '/tag/',
            '/tags/',
            '/topic/',
            '/topics/',
        ]

        for indicator in category_indicators:
            if indicator in url_lower:
                return True

        # Check if URL ends with just a category (no article slug)
        # e.g., /artificial-intelligence/ or /ai/ or /technology/
        path_parts = url_lower.rstrip('/').split('/')
        if len(path_parts) > 0:
            last_part = path_parts[-1]
            # If last part is very generic and short, likely a category
            generic_categories = ['ai', 'tech', 'technology', 'business', 'news',
                                 'artificial-intelligence', 'machine-learning', 'startup']
            if last_part in generic_categories:
                return True

        return False

    def _validate_url_response(self, url: str) -> bool:
        """
        Actually test if URL is accessible via HTTP request.

        Returns True if URL returns a valid HTTP status (200-399).
        """
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            # Accept 200-399 status codes (success and redirects)
            return 200 <= response.status_code < 400
        except requests.exceptions.Timeout:
            logger.warning(f"URL validation timeout: {url[:50]}...")
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"URL validation failed: {url[:50]}... - {str(e)[:50]}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error validating URL: {url[:50]}... - {str(e)[:50]}")
            return False

    async def generate_insights(self, count: int = 3) -> List[Dict]:
        """
        Generate fresh AI/Business insights by searching the web.

        Args:
            count: Number of insights to generate

        Returns:
            List of generated insights
        """
        if not self.client:
            logger.error("Grok client not initialized")
            return []

        existing_hashes = self._get_existing_titles('insight')
        existing_titles = self._get_existing_title_list('insight')
        existing_urls = self._get_existing_urls('insight')
        logger.info(f"Found {len(existing_hashes)} existing insights in database")

        # Calculate date range (24 hours)
        from datetime import timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        prompt = f"""You are Lavoo's AI Research & Insights Engine, an elite technology journalist, business intelligence analyst, with 20+ years experience across AI, startups, venture funding, automation, productivity and global tech trends.

Your mission: Quickly scan the web and fetch ONLY the most fresh, high-value, globally relevant news published within the last 24 hours (between {yesterday} and {self.today}). Identify insights creators, entrepreneurs and business operators can act on immediately.

Output 5–7 items per request then pick the top 2 items. Prioritize speed and relevance. Keep responses lightweight, sharp, and insight-rich with minimum fluff.

Strict rules:
• No duplicates: never return a link previously delivered.
• Ignore anything older than 24 hours (between {yesterday} and {self.today}).
• Verify sources: only credible publications.
• Rewrite insights uniquely: NO summaries copied from articles.
• Return ONLY 2 news that feels useful, forward-moving, monetizable or strategic.
• Headlines must trigger curiosity + clicks + urgency.
• Each item MUST have an impact score (60–100) where:
  - 90–100 = Critical / game-changing / viral-worthy
  - 75–89 = High value / immediate opportunity
  - 60–74 = Useful insight, moderate urgency
  - <60 = Do not include
• Prioritize high-scoring stories first.

Your writing style: Clear. Punchy. Smart. No jargon.
Think better than Bloomberg clarity, Wired creativity, and a newsletter voice that feels human, exciting and easy to read.
The reader should feel like they're getting inside information.

Return results in THIS EXACT JSON array format only:
[
  {{
    "title": "Irresistible headline that sparks clicks (max 80 chars)",
    "category": "AI Technology | Funding | Automation | Business Strategy | Productivity | Marketing | Creator Economy | Networking | Financial Technology",
    "impact_score": 60-100,
    "read_time": "2 min | 3 min | 5 min",
    "what_changed": "What happened + core details + numbers where possible (2-3 sentences)",
    "why_it_matters": "Explain implications for creators/entrepreneurs. Highlight opportunities, risks and competitive edge (2-4 sentences)",
    "action_to_take": "One actionable move a reader can take now (1-2 practical lines)",
    "source": "Publication name only",
    "url": "Direct link to original article"
  }}
]

After generating items:
• Sort highest impact_score → lowest.
• Remove any weak, vague or low-value stories.
• Final output should feel like a cheat code for staying ahead of the world.

Tone guideline for headlines: Create FOMO, curiosity, and urgency without exaggerating.
Examples:
• "New AI Model Overtakes GPT-5: Startups Should Pay Attention"
• "$120M Funding Round Signals Huge New Market: Early Founders Win"
• "This AI Tool Cuts Editing Time 80%: Creators Are Switching Fast"
• "E-commerce Automation Just Leveled Up. Here's How to Cash In"

DO NOT CREATE DUPLICATES - These titles already exist:
{chr(10).join(['- ' + t for t in existing_titles[:20]]) if existing_titles else '(No existing insights)'}

Return only the JSON. No commentary, no explanation. Deliver pure gold at speed."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business intelligence analyst with web search capabilities. You find and summarize the latest business and AI news. Always return valid JSON arrays only."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for factual content
                extra_body={
                    "search_parameters": {
                        "mode": "on",
                        "return_citations": True,
                        "sources": [
                            {"type": "web"},
                            {"type": "news"}
                        ]
                    }
                }
            )

            content = response.choices[0].message.content.strip()

            # Debug: Log raw response
            logger.info(f"Raw API response (first 500 chars): {content[:500]}")

            # Parse JSON response
            # Handle potential markdown code blocks
            if content.startswith("```"):
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()

            insights = json.loads(content)

            if not isinstance(insights, list):
                insights = [insights]

            # Filter out duplicates and validate URLs
            new_insights = []
            for insight in insights:
                title = insight.get('title', 'Unknown')
                url = insight.get('url', '')

                # Type conversion: Handle string impact scores
                impact_score = insight.get('impact_score', 0)
                if isinstance(impact_score, str):
                    try:
                        impact_score = int(impact_score)
                        insight['impact_score'] = impact_score  # Convert in place
                    except (ValueError, TypeError):
                        impact_score = 0  # Invalid score

                # Enhanced duplicate check (title AND URL)
                is_duplicate, reason = self._is_duplicate_content(
                    title, url, existing_hashes, existing_urls
                )
                if is_duplicate:
                    logger.info(f"Skipping {reason}: {title[:50]}... (URL: {url[:50]}...)")
                    continue

                # Validate URL format
                if not url or not url.startswith('http'):
                    logger.warning(f"Skipping insight with invalid URL format: {title[:50]}... (URL: {url})")
                    continue

                # Quick pattern validation (check if it's obviously fake)
                if self._is_suspicious_url(url):
                    logger.warning(f"Skipping insight with suspicious URL pattern: {title[:50]}... (URL: {url})")
                    continue

                # HTTP validation - actually test if URL works
                if not self._validate_url_response(url):
                    logger.warning(f"Skipping insight with non-accessible URL: {title[:50]}... (URL: {url})")
                    continue

                new_insights.append(insight)
                logger.info(f"✓ Valid insight: {title[:50]}...")

            return new_insights

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse insights JSON: {e}")
            logger.error(f"Raw content: {content[:500]}")
            return []
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return []

    async def generate_alerts(self, count: int = 2) -> List[Dict]:
        """
        Generate fresh opportunity alerts by searching the web.

        Args:
            count: Number of alerts to generate

        Returns:
            List of generated alerts
        """
        if not self.client:
            logger.error("Grok client not initialized")
            return []

        existing_hashes = self._get_existing_titles('alert')
        existing_titles = self._get_existing_title_list('alert')
        existing_urls = self._get_existing_urls('alert')
        logger.info(f"Found {len(existing_hashes)} existing alerts in database")

        # Calculate date range (24-72 hours for opportunities)
        from datetime import timedelta
        three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        prompt = f"""You are Lavoo's Opportunity Intelligence Engine, an elite strategist who finds real business opportunities before they go mainstream. You scan the web for openings creators, entrepreneurs and businesses can act on today.

Your job is to fetch ONLY opportunities that are:
• new, recent, ongoing OR still open within defined timeframe
• announced within the last 24–72 hours OR still accepting submissions/invitations
• actionable, profitable, time-sensitive or early-mover advantages

Opportunity Types to Look For:
• Grants, funding calls, accelerator applications
• Hackathons, startup challenges, venture competitions
• AI tools/features launching with first-mover advantage
• Tech events, webinars, workshops, fellowships
• B2B/B2C markets showing demand spikes
• Partnerships/integration possibilities
• SaaS gaps, new API releases, automation openings
• Cost-saving opportunities & new commercial channels

Hard Rules:
1. Return 3–5 opportunities per request and select the most valuable top 2.
2. NO outdated or expired opportunities.
3. NO broken/dead links, verify URLs are live & reachable.
4. NO duplicates, do not return any URL previously generated.
5. Data must be original insights, not copied summaries.
6. Each item needs urgency, upside, and actionability.
7. Include deadlines if any: (dd/mm/yyyy or "closes in X days")
8. Only include impact score ≥ 70.
9. Prioritize hottest + soon-to-close at the top.
10. If link confidence < 100%, validate or replace with source page.

Time Validity Guidelines:
• Recent news: within last 72hrs max (between {three_days_ago} and {self.today}).
• Opportunities with a future date/deadline are allowed if active.
• Past-dated or closed opportunities must be excluded automatically.

Add backlink validation logic:
If URL appears dead OR returns error/redirect/404:
→ search for primary source, announcement page or official website
→ replace with verified live link before output
→ if none found, skip entire opportunity

Return output in THIS exact JSON array format:
[
  {{
    "title": "FOMO-driven opportunity headline (max 70 chars)",
    "impact_score": 70-100,
    "urgency_level": "High | Medium | Low",
    "category": "Funding | Hackathon | AI Tools | Events | Grants | Partnerships | Scholarships | Markets | Cost Savings",
    "deadline": "dd/mm/yyyy or 'Closes in X days' or 'Ongoing'",
    "why_act_now": "What changed + why timing matters. (2-3 sentences, urgency-focused)",
    "potential_reward": "Describe upside (profit, exposure, adoption, ROI, network access). (2-4 sentences)",
    "action_required": "Clear executable next steps. (1-3 simple bullet-like instructions)",
    "source": "Source or authority name",
    "url": "LIVE verified link only"
  }}
]

Headline tone:
• Spark urgency, profit, and early-access excitement.
• Example energy:
  "$150K Innovation Grant Now Open: Solo Founders Welcome"
  "XYZ Hackathon Opens: Winners Get Funding & Accelerator Slots"
  "New AI API Launch = Opportunity to Build Tools Before Competition"
  "Government SME Grant Accepting Applicants: Limited Window"

DO NOT CREATE DUPLICATES - These titles already exist:
{chr(10).join(['- ' + t for t in existing_titles[:20]]) if existing_titles else '(No existing alerts)'}

Return ONLY the formatted JSON: no intro text, no commentary."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an opportunity scout with web search capabilities. You find time-sensitive business opportunities. Always return valid JSON arrays only."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                extra_body={
                    "search_parameters": {
                        "mode": "on",
                        "return_citations": True,
                        "sources": [
                            {"type": "web"},
                            {"type": "news"}
                        ]
                    }
                }
            )

            content = response.choices[0].message.content.strip()

            # Debug: Log raw response
            logger.info(f"Raw API response (first 500 chars): {content[:500]}")

            # Parse JSON response
            if content.startswith("```"):
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()

            alerts = json.loads(content)

            if not isinstance(alerts, list):
                alerts = [alerts]

            # Filter out duplicates and validate URLs
            new_alerts = []
            for alert in alerts:
                title = alert.get('title', 'Unknown')
                url = alert.get('url', '')

                # Type conversion: Handle string impact scores
                impact_score = alert.get('impact_score', 70)
                if isinstance(impact_score, str):
                    try:
                        impact_score = int(impact_score)
                        alert['impact_score'] = impact_score  # Convert in place
                    except (ValueError, TypeError):
                        impact_score = 70  # Default for alerts

                # Map urgency_level to priority (backwards compatibility)
                if 'urgency_level' in alert and 'priority' not in alert:
                    alert['priority'] = alert['urgency_level']

                # Map impact_score to score field (backwards compatibility)
                if 'impact_score' in alert and 'score' not in alert:
                    alert['score'] = alert['impact_score']

                # Map deadline to time_remaining (backwards compatibility)
                if 'deadline' in alert and 'time_remaining' not in alert:
                    alert['time_remaining'] = alert['deadline']

                # Enhanced duplicate check (title AND URL)
                is_duplicate, reason = self._is_duplicate_content(
                    title, url, existing_hashes, existing_urls
                )
                if is_duplicate:
                    logger.info(f"Skipping {reason}: {title[:50]}... (URL: {url[:50]}...)")
                    continue

                # Validate URL format
                if not url or not url.startswith('http'):
                    logger.warning(f"Skipping alert with invalid URL format: {title[:50]}... (URL: {url})")
                    continue

                # Quick pattern validation (check if it's obviously fake)
                if self._is_suspicious_url(url):
                    logger.warning(f"Skipping alert with suspicious URL pattern: {title[:50]}... (URL: {url})")
                    continue

                # HTTP validation - actually test if URL works
                if not self._validate_url_response(url):
                    logger.warning(f"Skipping alert with non-accessible URL: {title[:50]}... (URL: {url})")
                    continue

                new_alerts.append(alert)
                logger.info(f"✓ Valid alert: {title[:50]}...")

            return new_alerts

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse alerts JSON: {e}")
            logger.error(f"Raw content: {content[:500]}")
            return []
        except Exception as e:
            logger.error(f"Error generating alerts: {e}")
            return []

    def save_insights(self, insights: List[Dict]) -> Tuple[int, int]:
        """
        Save insights to database.

        Args:
            insights: List of insight dictionaries

        Returns:
            Tuple of (saved_count, skipped_count)
        """
        saved = 0
        skipped = 0

        for insight_data in insights:
            try:
                # Validate required fields (impact_score is optional for backwards compatibility)
                required = ['title', 'category', 'what_changed', 'why_it_matters', 'action_to_take']
                if not all(insight_data.get(f) for f in required):
                    logger.warning(f"Skipping insight with missing fields: {insight_data.get('title', 'Unknown')}")
                    skipped += 1
                    continue

                # Handle date field - use impact_score as fallback if date not present
                date_value = insight_data.get('date', self.today)

                insight = Insight(
                    title=insight_data['title'][:255],  # Truncate if needed
                    category=insight_data.get('category', 'General'),
                    read_time=insight_data.get('read_time', '3 min'),
                    date=date_value,
                    source=insight_data.get('source', 'AI Generated'),
                    url=insight_data.get('url', ''),  # URL of the source article
                    what_changed=insight_data['what_changed'],
                    why_it_matters=insight_data['why_it_matters'],
                    action_to_take=insight_data['action_to_take'],
                    is_active=True,
                    total_views=0,
                    total_shares=0
                )

                self.db.add(insight)
                self.db.commit()
                saved += 1
                logger.info(f"✅ Saved insight: {insight.title[:50]}...")

            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to save insight: {e}")
                skipped += 1

        return saved, skipped

    def save_alerts(self, alerts: List[Dict]) -> Tuple[int, int]:
        """
        Save alerts to database.

        Args:
            alerts: List of alert dictionaries

        Returns:
            Tuple of (saved_count, skipped_count)
        """
        saved = 0
        skipped = 0

        for alert_data in alerts:
            try:
                # Validate required fields (flexible for new format)
                required = ['title', 'category', 'why_act_now', 'potential_reward', 'action_required']
                if not all(alert_data.get(f) for f in required):
                    logger.warning(f"Skipping alert with missing fields: {alert_data.get('title', 'Unknown')}")
                    skipped += 1
                    continue

                # Handle priority field (urgency_level or priority)
                priority = alert_data.get('priority', alert_data.get('urgency_level', 'Medium'))

                # Handle score field (impact_score or score)
                score = alert_data.get('score', alert_data.get('impact_score', 70))
                if isinstance(score, str):
                    score = int(score)
                score = max(1, min(100, score))  # Clamp to 1-100

                # Handle time_remaining field (deadline or time_remaining)
                time_remaining = alert_data.get('time_remaining', alert_data.get('deadline', 'Ongoing'))

                alert = Alert(
                    title=alert_data['title'][:255],
                    category=alert_data['category'],
                    priority=priority,
                    score=score,
                    time_remaining=time_remaining,
                    why_act_now=alert_data['why_act_now'],
                    potential_reward=alert_data['potential_reward'],
                    action_required=alert_data['action_required'],
                    source=alert_data.get('source', 'AI Generated'),
                    url=alert_data.get('url', ''),  # URL of the source article
                    date=alert_data.get('date', self.today),  # Use article date or today
                    is_active=True,
                    total_views=0,
                    total_shares=0
                )

                self.db.add(alert)
                self.db.commit()
                saved += 1
                logger.info(f"✅ Saved alert: {alert.title[:50]}...")

            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to save alert: {e}")
                skipped += 1

        return saved, skipped


async def run_content_generation(insight_count: int = 3, alert_count: int = 2):
    """
    Main function to run content generation.

    Args:
        insight_count: Number of insights to generate
        alert_count: Number of alerts to generate
    """
    logger.info("=" * 60)
    logger.info(f"🚀 Starting AI Content Generation - {datetime.now()}")
    logger.info("=" * 60)

    # Create database session
    db = SessionLocal()

    try:
        generator = ContentGenerator(db)

        # Generate and save insights
        logger.info("\n📊 Generating Insights...")
        insights = await generator.generate_insights(count=insight_count)

        if insights:
            saved, skipped = generator.save_insights(insights)
            logger.info(f"Insights: {saved} saved, {skipped} skipped")
        else:
            logger.info("No new insights found")

        # Generate and save alerts
        logger.info("\n🚨 Generating Opportunity Alerts...")
        alerts = await generator.generate_alerts(count=alert_count)

        if alerts:
            saved, skipped = generator.save_alerts(alerts)
            logger.info(f"Alerts: {saved} saved, {skipped} skipped")
        else:
            logger.info("No new alerts found")

        logger.info("\n" + "=" * 60)
        logger.info("✅ Content Generation Complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        raise
    finally:
        db.close()


# CLI entry point
if __name__ == "__main__":
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description="Generate AI-powered insights and alerts")
    parser.add_argument("--insights", type=int, default=3, help="Number of insights to generate")
    parser.add_argument("--alerts", type=int, default=2, help="Number of alerts to generate")

    args = parser.parse_args()

    asyncio.run(run_content_generation(
        insight_count=args.insights,
        alert_count=args.alerts
    ))
