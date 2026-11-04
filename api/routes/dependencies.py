# write the code to prevent non-admins from accessing certain routes
from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Cookie
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


def subscriber_required(current_user: User = Depends(get_current_user)) -> User:
    """Only Pro and Premium subscribers (and admins) may use the route.

    get_current_user already re-syncs subscription_status against the latest
    payment, so an expired subscription reads "Free" here, not "active".
    """
    status_value = (current_user.subscription_status or "").lower()
    if status_value in PAID_SUBSCRIPTION_STATUSES or getattr(current_user, "is_admin", False):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="The Decision Engine is available to Pro and Premium subscribers. Upgrade to continue.",
    )
