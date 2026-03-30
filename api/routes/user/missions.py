"""
Dynamic Missions System
Missions are dynamically generated from user's business analyses
Each action plan becomes a trackable mission
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.pg_connections import get_db
from database.pg_models import User, BusinessAnalysis
from api.routes.auth.login import get_current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/missions", tags=["missions"])


class MissionStepComplete(BaseModel):
    reflection: Optional[str] = None


class MissionResponse(BaseModel):
    id: int
    analysis_id: int
    business_goal: str
    title: str
    description: str
    progress: float
    total_steps: int
    completed_steps: int
    points_reward: int
    status: str
    created_at: str
    steps: List[dict]


@router.get("")
async def get_user_missions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all missions for the current user.
    Missions are generated from their business analyses.
    Each action plan in an analysis becomes a mission step.
    """
    try:
        # Get all user's analyses
        analyses = db.query(BusinessAnalysis).filter(
            BusinessAnalysis.user_id == current_user.id
        ).order_by(BusinessAnalysis.created_at.desc()).all()

        missions = []

        for analysis in analyses:
            # Skip if no action plans
            if not analysis.action_plans or len(analysis.action_plans) == 0:
                continue

            # Get user progress from analysis metadata
            user_progress = analysis.user_progress or {}
            completed_steps = user_progress.get('completed_actions', [])

            # Convert action plans to mission steps
            steps = []
            for idx, action in enumerate(analysis.action_plans, 1):
                step_id = f"{analysis.id}_action_{idx}"
                is_completed = step_id in completed_steps

                steps.append({
                    'id': step_id,
                    'day': idx,
                    'label': action.get('title', action.get('action_title', f'Action {idx}')),
                    'description': action.get('what_to_do', [''])[0] if action.get('what_to_do') else
                                   action.get('what_to_do_steps', [''])[0] if action.get('what_to_do_steps') else
                                   action.get('description', ''),
                    'done': is_completed,
                    'active': not is_completed and (idx == len(completed_steps) + 1),
                    'points': 20,
                    'effort': action.get('effort', 'MEDIUM'),
                    'reflection': user_progress.get('reflections', {}).get(step_id)
                })

            # Calculate progress
            total_steps = len(steps)
            completed_count = len(completed_steps)
            progress_percentage = (completed_count / total_steps * 100) if total_steps > 0 else 0

            # Determine status
            if completed_count == 0:
                mission_status = "not_started"
            elif completed_count == total_steps:
                mission_status = "completed"
            else:
                mission_status = "active"

            missions.append({
                'id': analysis.id,
                'analysis_id': analysis.id,
                'business_goal': analysis.business_goal,
                'title': analysis.strategic_priority or f"Mission: {analysis.business_goal[:50]}",
                'description': f"Complete {total_steps} action steps",
                'progress': round(progress_percentage, 1),
                'total_steps': total_steps,
                'completed_steps': completed_count,
                'points_reward': total_steps * 20,
                'status': mission_status,
                'created_at': analysis.created_at.isoformat() if analysis.created_at else None,
                'steps': steps
            })

        return {
            "success": True,
            "data": missions
        }

    except Exception as e:
        logger.error(f"Error fetching missions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch missions"
        )


@router.get("/active")
async def get_active_missions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get only active (incomplete) missions"""
    try:
        analyses = db.query(BusinessAnalysis).filter(
            BusinessAnalysis.user_id == current_user.id
        ).order_by(BusinessAnalysis.created_at.desc()).all()

        active_missions = []

        for analysis in analyses:
            if not analysis.action_plans:
                continue

            user_progress = analysis.user_progress or {}
            if isinstance(user_progress, str):
                import json
                try:
                    user_progress = json.loads(user_progress)
                except json.JSONDecodeError:
                    user_progress = {}
            if not isinstance(user_progress, dict):
                user_progress = {}
                
            completed_steps = user_progress.get('completed_actions', [])
            total_steps = len(analysis.action_plans)

            # Only include if not fully completed
            if len(completed_steps) < total_steps:
                active_missions.append({
                    'id': analysis.id,
                    'analysis_id': analysis.id,
                    'business_goal': analysis.business_goal or "Business Goal",
                    'title': analysis.strategic_priority or (analysis.business_goal[:50] if analysis.business_goal else "Business Goal"),
                    'progress': round(len(completed_steps) / total_steps * 100, 1) if total_steps > 0 else 0,
                    'total_steps': total_steps,
                    'completed_steps': len(completed_steps),
                    'next_action': analysis.action_plans[len(completed_steps)].get('title', '') if len(completed_steps) < len(analysis.action_plans) else None
                })

        return {
            "success": True,
            "data": active_missions
        }

    except Exception as e:
        logger.error(f"Error fetching active missions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch active missions"
        )


@router.get("/constraints/active")
async def get_active_constraints(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all active constraints from user's analyses.
    These are bottlenecks and constraints that haven't been resolved yet.
    """
    try:
        analyses = db.query(BusinessAnalysis).filter(
            BusinessAnalysis.user_id == current_user.id
        ).order_by(BusinessAnalysis.created_at.desc()).all()

        active_constraints = []

        for analysis in analyses:
            user_progress = analysis.user_progress or {}
            resolved_constraints = user_progress.get('resolved_constraints', [])

            # Add primary bottleneck if exists and not resolved
            if analysis.primary_bottleneck:
                constraint_id = f"{analysis.id}_primary"
                if constraint_id not in resolved_constraints:
                    active_constraints.append({
                        'id': constraint_id,
                        'analysis_id': analysis.id,
                        'type': 'primary_bottleneck',
                        'title': analysis.primary_bottleneck.get('title', 'Primary Bottleneck'),
                        'description': analysis.primary_bottleneck.get('description', ''),
                        'impact': analysis.primary_bottleneck.get('impact', 'high'),
                        'consequence': analysis.primary_bottleneck.get('consequence', ''),
                        'created_at': analysis.created_at.isoformat() if analysis.created_at else None
                    })

            # Add secondary constraints if not resolved
            if analysis.secondary_constraints:
                for idx, constraint in enumerate(analysis.secondary_constraints, 1):
                    constraint_id = f"{analysis.id}_constraint_{idx}"
                    if constraint_id not in resolved_constraints:
                        active_constraints.append({
                            'id': constraint_id,
                            'analysis_id': analysis.id,
                            'type': 'secondary_constraint',
                            'number': idx,
                            'title': constraint.get('title', f'Constraint {idx}'),
                            'description': constraint.get('description', ''),
                            'impact': constraint.get('impact', 'medium'),
                            'created_at': analysis.created_at.isoformat() if analysis.created_at else None
                        })

        return {
            "success": True,
            "data": active_constraints,
            "count": len(active_constraints)
        }

    except Exception as e:
        logger.error(f"Error fetching active constraints: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch active constraints"
        )


@router.post("/constraints/{constraint_id}/resolve")
async def resolve_constraint(
    constraint_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a constraint as resolved"""
    try:
        # Extract analysis_id from constraint_id (format: {analysis_id}_primary or {analysis_id}_constraint_{idx})
        analysis_id = int(constraint_id.split('_')[0])

        analysis = db.query(BusinessAnalysis).filter(
            BusinessAnalysis.id == analysis_id,
            BusinessAnalysis.user_id == current_user.id
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )

        # Initialize user_progress if not exists
        user_progress = analysis.user_progress or {}

        if 'resolved_constraints' not in user_progress:
            user_progress['resolved_constraints'] = []

        if constraint_id not in user_progress['resolved_constraints']:
            user_progress['resolved_constraints'].append(constraint_id)

            # Award chops for resolving constraint
            current_user.total_chops = (current_user.total_chops or 0) + 30

        analysis.user_progress = user_progress
        db.commit()

        return {
            "success": True,
            "message": "Constraint marked as resolved",
            "data": {
                'constraint_id': constraint_id,
                'resolved': True,
                'chops_earned': 30,
                'total_chops': current_user.total_chops
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving constraint: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve constraint"
        )


@router.get("/{analysis_id}")
async def get_mission_details(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed mission information for a specific analysis"""
    try:
        analysis = db.query(BusinessAnalysis).filter(
            BusinessAnalysis.id == analysis_id,
            BusinessAnalysis.user_id == current_user.id
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mission not found"
            )

        if not analysis.action_plans:
            return {
                "success": True,
                "data": {
                    'id': analysis.id,
                    'title': 'No actions available',
                    'steps': []
                }
            }

        user_progress = analysis.user_progress or {}
        completed_steps = user_progress.get('completed_actions', [])

        steps = []
        for idx, action in enumerate(analysis.action_plans, 1):
            step_id = f"{analysis.id}_action_{idx}"
            is_completed = step_id in completed_steps

            # Get full action details
            what_to_do = action.get('what_to_do', action.get('what_to_do_steps', action.get('steps', [])))
            why_matters = action.get('why_this_matters', action.get('why_it_matters', action.get('why_it_matters_bullets', [])))

            steps.append({
                'id': step_id,
                'number': idx,
                'day': idx,
                'label': action.get('title', action.get('action_title', f'Action {idx}')),
                'description': what_to_do[0] if what_to_do else '',
                'full_steps': what_to_do,
                'why_it_matters': why_matters,
                'effort': action.get('effort', 'MEDIUM'),
                'done': is_completed,
                'active': not is_completed and (idx == len(completed_steps) + 1),
                'points': 20,
                'toolkit': action.get('ai_tool', action.get('toolkit')),
                'completed_at': user_progress.get('completion_dates', {}).get(step_id),
                'reflection': user_progress.get('reflections', {}).get(step_id)
            })

        return {
            "success": True,
            "data": {
                'id': analysis.id,
                'analysis_id': analysis.id,
                'business_goal': analysis.business_goal,
                'title': analysis.strategic_priority or analysis.business_goal,
                'description': analysis.primary_bottleneck.get('description', '') if analysis.primary_bottleneck else '',
                'strategic_priority': analysis.strategic_priority,
                'progress': round(len(completed_steps) / len(analysis.action_plans) * 100, 1),
                'total_steps': len(analysis.action_plans),
                'completed_steps': len(completed_steps),
                'points_reward': len(analysis.action_plans) * 20,
                'status': 'completed' if len(completed_steps) == len(analysis.action_plans) else 'active',
                'steps': steps
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching mission details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch mission details"
        )


@router.post("/{analysis_id}/steps/{step_number}/complete")
async def complete_mission_step(
    analysis_id: int,
    step_number: int,
    body: MissionStepComplete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a mission step as complete and optionally add reflection"""
    try:
        analysis = db.query(BusinessAnalysis).filter(
            BusinessAnalysis.id == analysis_id,
            BusinessAnalysis.user_id == current_user.id
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mission not found"
            )

        if not analysis.action_plans or step_number > len(analysis.action_plans):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid step number"
            )

        # Initialize user_progress if not exists
        user_progress = analysis.user_progress or {
            'completed_actions': [],
            'completion_dates': {},
            'reflections': {}
        }

        step_id = f"{analysis_id}_action_{step_number}"

        # Mark as completed
        if step_id not in user_progress.get('completed_actions', []):
            if 'completed_actions' not in user_progress:
                user_progress['completed_actions'] = []
            user_progress['completed_actions'].append(step_id)

            if 'completion_dates' not in user_progress:
                user_progress['completion_dates'] = {}
            user_progress['completion_dates'][step_id] = datetime.utcnow().isoformat()

            # Award chops (20 points per step)
            current_user.total_chops = (current_user.total_chops or 0) + 20

        # Save reflection if provided
        if body.reflection:
            if 'reflections' not in user_progress:
                user_progress['reflections'] = {}
            user_progress['reflections'][step_id] = body.reflection

        # Update analysis with new progress
        analysis.user_progress = user_progress

        # Check if mission completed
        is_mission_completed = len(user_progress['completed_actions']) == len(analysis.action_plans)

        if is_mission_completed:
            # Award bonus chops for completing entire mission
            bonus_chops = len(analysis.action_plans) * 5
            current_user.total_chops = (current_user.total_chops or 0) + bonus_chops

        db.commit()

        return {
            "success": True,
            "message": "Step completed successfully",
            "data": {
                'step_id': step_id,
                'completed': True,
                'chops_earned': 20,
                'mission_completed': is_mission_completed,
                'total_chops': current_user.total_chops
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing mission step: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete mission step"
        )
