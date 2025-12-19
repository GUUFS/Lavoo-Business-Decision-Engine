"""
Cron Jobs Package

This package contains all scheduled tasks for the AI Business Analyst platform.

Jobs:
- insights.py: Generate business insights (every 4 hours, 3 per run)
- alerts.py: Generate opportunity alerts (every 2 hours, 2 per run)
- cleanup.py: Delete old data (daily, removes data older than 4 months)
"""
