"""
Staff referral pool (api/services/staff_referral_service.py) is switched
off: a signup with no referral code is no longer given to a staff member,
unless STAFF_REFERRAL_POOL_ENABLED is set to true.
"""
from api.services.staff_referral_service import assign_next_staff_referrer
from database.pg_models import StaffReferralPool, User


def _staff_in_pool(db):
    """One active staff member in the pool."""
    # 1. The staff account.
    staff = User(name="Pool Staff", email="pool-staff@test.local", password="x", confirm_password="x", is_staff=True)
    db.add(staff)
    db.flush()
    # 2. In the pool, never assigned yet.
    db.add(StaffReferralPool(user_id=staff.id, email=staff.email, is_active=True, assigned_count=0))
    db.flush()
    return staff


def test_nobody_is_assigned_while_switched_off(db, monkeypatch):
    monkeypatch.delenv("STAFF_REFERRAL_POOL_ENABLED", raising=False)
    _staff_in_pool(db)
    assert assign_next_staff_referrer(db) is None
    pool = db.query(StaffReferralPool).filter_by(email="pool-staff@test.local").one()
    assert pool.assigned_count == 0        # their turn isn't used up either


def test_switching_it_back_on_assigns_again(db, monkeypatch):
    monkeypatch.setenv("STAFF_REFERRAL_POOL_ENABLED", "true")
    staff = _staff_in_pool(db)
    assert assign_next_staff_referrer(db).id == staff.id
