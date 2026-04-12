
import os
import sys
import json
from database.pg_connections import SessionLocal
from database.pg_models import BusinessAnalysis
from api.routes.user.missions import _parse_action_plans

try:
    db = SessionLocal()
    analyses = db.query(BusinessAnalysis).order_by(BusinessAnalysis.created_at.desc()).limit(10).all()

    for analysis in analyses:
        plans = _parse_action_plans(analysis)
        user_progress = analysis.user_progress or {}
        if isinstance(user_progress, str):
            user_progress = json.loads(user_progress)
        
        if not isinstance(user_progress, dict):
            user_progress = {}

        completed_steps = user_progress.get("completed_actions", [])
        
        if len(completed_steps) < len(plans):
            item = plans[len(completed_steps)]
            if not isinstance(item, dict):
                print(f"Error on ID {analysis.id}: item is {type(item)}: {repr(item)}")
            else:
                item.get("title", "")
except Exception as e:
    import traceback
    traceback.print_exc()

