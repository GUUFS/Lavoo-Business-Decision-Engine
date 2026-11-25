"""
Mission steps and reflections (api/routes/user/missions.py).

Completing a step earns nothing by itself; one reflection earns exactly
20 chops (once per step) and is shown under the step's task in All Tasks,
all from one call.
"""
import asyncio

from api.routes.user.missions import MissionStepComplete, complete_mission_step, get_mission_details
from database.pg_models import BusinessAnalysis, User

ROADMAP = [{"phase": "Week 1", "tasks": ["Write the model spec", "Call three farmers"]},
           {"phase": "Week 2", "tasks": ["Post the offer"]}]


def _mission(db, email):
    """A founder with a 3-step mission."""
    user = User(name="Ada Founder", email=email, password="x", confirm_password="x", total_chops=0)
    db.add(user)
    db.flush()
    analysis = BusinessAnalysis(user_id=user.id, business_goal="poultry", execution_roadmap=ROADMAP)
    db.add(analysis)
    db.flush()
    return user, analysis


def _complete(db, user, analysis, step, reflection=None):
    """POST /missions/{id}/steps/{step}/complete."""
    return asyncio.run(complete_mission_step(analysis.id, step, MissionStepComplete(reflection=reflection), db, user))


def test_completing_a_step_earns_nothing_and_a_reflection_earns_20(db):
    user, analysis = _mission(db, "steps@missions.test")
    assert _complete(db, user, analysis, 1)["data"]["chops_earned"] == 0
    assert _complete(db, user, analysis, 1, "Wrote it in 40 minutes")["data"]["chops_earned"] == 20
    assert user.total_chops == 20


def test_a_reflection_is_20_even_when_it_completes_the_first_step(db):
    """Before, the first step ever + a reflection gave 40."""
    user, analysis = _mission(db, "first@missions.test")
    assert _complete(db, user, analysis, 1, "Done and learned a lot")["data"]["chops_earned"] == 20
    assert user.total_chops == 20


def test_the_reflection_shows_under_its_task_and_counts_once(db):
    user, analysis = _mission(db, "shown@missions.test")
    _complete(db, user, analysis, 3)
    _complete(db, user, analysis, 3, "Two farmers replied")
    # Sent again (e.g. a retry): saved, but no more chops.
    assert _complete(db, user, analysis, 3, "Two farmers replied")["data"]["chops_earned"] == 0
    steps = asyncio.run(get_mission_details(analysis.id, db, user))["data"]["steps"]
    step3 = next(s for s in steps if s["day"] == 3)
    assert step3["done"] and step3["reflection"] == "Two farmers replied"
    assert step3["comments"][0]["text"] == "Two farmers replied"  # task-1-0, as the app numbers it
    assert user.total_chops == 20
