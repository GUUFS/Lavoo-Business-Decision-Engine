#!/usr/bin/env python3
"""
Cron Job Runner for AI Content Generation
This script is designed to be run by cron to automatically generate insights and alerts.

Usage:
    python scripts/run_content_generator.py

Or with custom counts:
    python scripts/run_content_generator.py --insights 5 --alerts 3

Cron Examples:
    # Every 6 hours
    0 */6 * * * cd /path/to/ai-business-analyst && python scripts/run_content_generator.py

    # Every 12 hours at 6am and 6pm
    0 6,18 * * * cd /path/to/ai-business-analyst && python scripts/run_content_generator.py

    # Once daily at 8am
    0 8 * * * cd /path/to/ai-business-analyst && python scripts/run_content_generator.py
"""

import asyncio
import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.content_generator import run_content_generation


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI-powered insights and opportunity alerts"
    )
    parser.add_argument(
        "--insights",
        type=int,
        default=3,
        help="Number of insights to generate (default: 3)"
    )
    parser.add_argument(
        "--alerts",
        type=int,
        default=2,
        help="Number of alerts to generate (default: 2)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without saving to database"
    )

    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           AI CONTENT GENERATOR - CRON JOB RUNNER             ║
╠══════════════════════════════════════════════════════════════╣
║  Insights to generate: {args.insights:<5}                    ║
║  Alerts to generate:   {args.alerts:<5}                      ║
║  Dry run:              {str(args.dry_run):<5}                ║
╚══════════════════════════════════════════════════════════════╝
    """)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be saved to database")
        # TODO: Implement dry run mode
        return

    # Run the async content generation
    asyncio.run(run_content_generation(
        insight_count=args.insights,
        alert_count=args.alerts
    ))


if __name__ == "__main__":
    main()
