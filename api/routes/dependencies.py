# write the code to prevent non-admins from accessing certain routes
from typing import Optional
from fastapi import Depends, HTTPException, Request, status, Header, Cookie
from sqlalchemy.orm import Session
from database.pg_models import User
from database.pg_connections import get_db
from api.routes.auth.login import get_current_user, get_admin_user, bearer_scheme

def admin_required(current_user: User = Depends(get_admin_user),db: Session = Depends(get_db)):
    # prevent non-admin users from accessing the route
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource."
        )
    return current_user


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    access_token_cookie: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Best-effort version of get_current_user for routes that serve both
    logged-out and logged-in visitors (e.g. the public Signal detail page).

    Mirrors get_current_user's exact verification path — same header/cookie
    precedence, same JWT decode, same DB lookup — by calling it directly, so
    there is only ever one place that actually validates a token. The only
    difference: instead of raising 401 when there's no token, a malformed
    header, an expired/invalid JWT, or no matching user, this simply
    returns None so the route can treat the request as "anonymous" rather
    than fail it.

    A route using this dependency MUST NOT assume current_user is present —
    always check `if current_user` before using it.
    """
    if not authorization and not access_token_cookie:
        return None

    try:
        return get_current_user(
            authorization=authorization,
            access_token_cookie=access_token_cookie,
            db=db,
        )
    except HTTPException:
        # Invalid scheme, malformed header, expired/invalid JWT, or user
        # not found — all of these mean "treat as anonymous", not "fail".
        return None

# Subscription statuses that count as a paying Pro or Premium member.
PAID_SUBSCRIPTION_STATUSES = ("active", "trialing")


def has_decision_engine_access(user: User) -> bool:
    """True for Pro and Premium subscribers, admins, and new accounts in
    their free trial ("3 days of Premium", subscriptions/free_trial.py)."""
    from subscriptions.free_trial import free_trial_active
    # 1. A paying subscriber, or an admin.
    status_value = (user.subscription_status or "").lower()
    if status_value in PAID_SUBSCRIPTION_STATUSES or getattr(user, "is_admin", False):
        return True
    # 2. A new account still in its free trial.
    return free_trial_active(user)


def decision_engine_access_ends_at(user: User) -> Optional[str]:
    """When this user's Decision Engine access ends (ISO time), if it comes
    only from the free trial; None when they pay, are an admin, or have no access."""
    from subscriptions.free_trial import free_trial_active, free_trial_ends_at
    # 1. Paying subscribers and admins: access doesn't end with the trial.
    status_value = (user.subscription_status or "").lower()
    if status_value in PAID_SUBSCRIPTION_STATUSES or getattr(user, "is_admin", False):
        return None
    # 2. In the free trial: access ends when the trial ends.
    if free_trial_active(user):
        return free_trial_ends_at(user).isoformat()
    # 3. No access at all.
    return None


def subscriber_required(current_user: User = Depends(get_current_user)) -> User:
    """Only Pro and Premium subscribers, admins, and accounts in their free
    trial may use the route.

    get_current_user already re-syncs subscription_status against the latest
    payment, so an expired subscription reads "Free" here, not "active".
    """
    # 1. Let them in if they have access.
    if has_decision_engine_access(current_user):
        return current_user
    # 2. Otherwise: ask them to upgrade.
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="The Decision Engine is available to Pro and Premium subscribers. Upgrade to continue.",
    )


def owns_claimed_ad_checkup(db: Session, user: User, analysis_id) -> bool:
    """True if this analysis came from an ad check-up (lavoo.io/checkup) that
    this user claimed when they signed up (decision_engine/guest_checkup.py)."""
    from database.pg_models import GuestCheckup
    # 1. The address must name an analysis.
    try:
        analysis_id = int(analysis_id)
    except (TypeError, ValueError):
        return False
    # 2. A claimed ad check-up, claimed by this same user.
    return db.query(GuestCheckup.id).filter(
        GuestCheckup.analysis_id == analysis_id,
        GuestCheckup.claimed_by == user.id,
        GuestCheckup.status == "claimed",
    ).first() is not None


def subscriber_or_ad_checkup_owner(request: Request, current_user: User = Depends(get_current_user),
                                   db: Session = Depends(get_db)) -> User:
    """Like subscriber_required, with one exception: anyone may open, and run
    the Missions of, the analysis they claimed from an ad check-up.

    The ad promises a free check-up with what to stop doing and daily
    Missions, so a new free account must see its full result
    (/l/checkup-result/ID) and start its Missions. Everything else in the
    Decision Engine (new check-ups, history, other analyses) stays paid."""
    # 1. Subscribers, admins and free-trial accounts: as before.
    if has_decision_engine_access(current_user):
        return current_user
    # 2. Their own claimed ad check-up (routes with {analysis_id} in the address).
    if owns_claimed_ad_checkup(db, current_user, request.path_params.get("analysis_id")):
        return current_user
    # 3. Otherwise: ask them to upgrade.
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="The Decision Engine is available to Pro and Premium subscribers. Upgrade to continue.",
    )
