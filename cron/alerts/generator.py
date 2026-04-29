# decision_engine/content_generator.py
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

# Import xAI SDK for Grok API with Agent Tools
try:
    from xai_sdk import Client
    from xai_sdk.chat import user
    from xai_sdk.tools import web_search
    HAS_XAI = True
except ImportError:
    HAS_XAI = False
    print("Warning: xai-sdk package not installed. Install with: uv add xai-sdk")

# Import database models
from database.pg_connections import SessionLocal, get_db
from database.pg_models import Insight, Alert

logger = logging.getLogger(__name__)

# Configure logging for standalone script execution
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class AlertsGenerator:
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

        # Initialize xAI SDK client for Grok API with Agent Tools
        if HAS_XAI:
            api_key = os.getenv("XAI_API_KEY")
            if not api_key:
                logger.warning("XAI_API_KEY not set in environment variables")
                self.client = None
            else:
                self.client = Client(api_key=api_key)
                logger.info("xAI Grok client initialized for content generation")
        else:
            self.client = None
            logger.warning("xAI SDK not installed")

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
            if url:  # Skip None URLs
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

CRITICAL: You MUST use your web search capabilities to find REAL, LIVE, active opportunities on the internet.\nDO NOT hallucinate or make up URLs.\nDO NOT make up fake grants, fake hackathons, or fake events.\nIf you cannot find real opportunities, return an empty array [].\nYour job is to fetch ONLY opportunities that are:
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
1. Return up to 3 opportunities. IF YOU CANNOT FIND ANY RECENT, VALID OPPORTUNITIES FROM THE LAST 72 HOURS, YOU MUST RETURN AN EMPTY ARRAY `[]`. DO NOT invent, hallucinate, or recycle old alerts.
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
• Recent news: MUST be within the last 72hrs (between {three_days_ago} and {self.today}).
• Opportunities with a future date/deadline are allowed if active.
• Past-dated or closed opportunities must be excluded automatically. If you only find past-dated alerts, output an empty array [].

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
            # Create chat with xAI SDK Agent Tools
            chat = self.client.chat.create(
                model=self.model,
                tools=[web_search()],  # Enable web search tool
            )

            # Add system message and user prompt
            chat.append(user(
                "You are an opportunity scout with web search capabilities. SEARCH THE WEB FIRST before answering. VERY IMPORTANT: You must NOT hallucinate. Only use real articles and opportunities from the search results. Provide real URLs. You find time-sensitive business opportunities. Always return valid JSON arrays only."
            ))
            chat.append(user(prompt))

            # Sample response (non-streaming)
            response = chat.sample()

            content = response.content.strip() if response.content else ""

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


async def run_content_generation(alert_count: int = 2):
    db = SessionLocal()
    try:
        generator = AlertsGenerator(db)
        logger.info("\n🚨 Generating Opportunity Alerts...")
        alerts = await generator.generate_alerts(count=alert_count)
        if alerts:
            saved, skipped = generator.save_alerts(alerts)
            logger.info(f"Alerts: {saved} saved, {skipped} skipped")
        else:
            logger.info("No new alerts found")
        logger.info("✅ Content Generation Complete")
    except Exception as e:
        logger.error(f"Failed to generate alerts: {e}")
    finally:
        db.close()
