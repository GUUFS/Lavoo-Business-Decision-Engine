"""
Google OAuth Authentication Routes

Handles Google OAuth 2.0 login flow for user authentication.

Endpoints:
    - GET /auth/google/login - Initiate Google OAuth flow
    - GET /auth/google/callback - Handle OAuth callback

Requirements:
    - GOOGLE_CLIENT_ID environment variable
    - GOOGLE_CLIENT_SECRET environment variable
    - GOOGLE_REDIRECT_URI environment variable (e.g., http://localhost:8000/api/v1/auth/google/callback)
"""

import os
import secrets
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from database.pg_connections import get_db
from database.pg_models import User, Referral, NotificationType
from api.routes.auth.login import create_access_token, get_effective_role
from api.routes.auth.signup import pwd_context, generate_referral_code
from api.services.streak_service import update_login_streak
from api.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])

# Google OAuth settings
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# Defaults corrected to match reality, not just left as a placeholder: the
# route is actually mounted at /api/auth/google/callback (api/main.py mounts
# this router at prefix="/api"; the old /api/v1/... default 404s), and the
# frontend is lavoo.io in production, not a Vite dev server on :5173 — same
# class of stale-default bug found this session in stripe_connect.py and
# payout_service.py, which each broke a redirect/callback whenever the real
# env var was unset.
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://lavoo.io")

# Google OAuth URLs
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/login")
async def google_login(ref: Optional[str] = Query(None)):
    """
    Initiate Google OAuth flow.
    
    Args:
        ref (str, optional): Referral code to pass through OAuth flow
        
    Returns:
        RedirectResponse: Redirect to Google OAuth consent page
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured (missing GOOGLE_CLIENT_ID)")
    
    # Build OAuth authorization URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    
    # Add referral code to state if provided
    if ref:
        params["state"] = f"ref={ref}"
    
    # Construct authorization URL
    auth_url = f"{GOOGLE_AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    logger.info(f"Initiating Google OAuth flow{' with referral: ' + ref if ref else ''}")
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def google_callback(
    request: Request,
    code: str = Query(...),
    state: Optional[str] = Query(None)
):
    """
    Handle Google OAuth callback.
    
    Exchanges authorization code for access token, fetches user info,
    creates/updates user in database, and redirects to frontend with JWT.
    
    Args:
        code (str): Authorization code from Google
        state (str, optional): State parameter (contains referral code if passed)
        
    Returns:
        RedirectResponse: Redirect to frontend with access token
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    try:
        # Extract referral code from state if present
        referral_code = None
        if state and "ref=" in state:
            referral_code = state.split("ref=")[1].split("&")[0]
        
        # Exchange authorization code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                }
            )
            
            if token_response.status_code != 200:
                logger.error(f"Google token exchange failed: {token_response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange authorization code")
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            
            # Fetch user info from Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                logger.error(f"Failed to fetch Google user info: {userinfo_response.text}")
                raise HTTPException(status_code=400, detail="Failed to fetch user information")
            
            user_info = userinfo_response.json()
        
        # Extract user details
        google_id = user_info.get("id")
        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")
        
        if not google_id or not email:
            raise HTTPException(status_code=400, detail="Missing required user information from Google")
        
        # Get database session
        db: Session = next(get_db())
        
        try:
            # User has no google_id/profile_image_url/email_verified columns —
            # this previously filtered/assigned all three, raising an
            # AttributeError on the very first query for every single
            # attempt (new signup, existing user, all alike), which the
            # broad except below silently turned into a generic
            # ?error=oauth_failed redirect. Matched by email only, same as
            # every other lookup in this codebase (see e.g.
            # subscriptions/flutterwave.py's /verify).
            user = db.query(User).filter(User.email == email).first()

            if user:
                user.avatar_url = picture or user.avatar_url
                user.last_login = datetime.now(timezone.utc)
                logger.info(f"Existing user logged in via Google: {email}")
            else:
                # New account via Google: password/confirm_password are
                # NOT NULL columns with no OAuth carve-out, so a real (but
                # unusable — the user never sees it) hash goes in both,
                # matching signup.py's pattern of hashing into each field
                # rather than leaving either unset.
                placeholder_password = pwd_context.hash(secrets.token_urlsafe(32))

                user_refcode = generate_referral_code()
                while db.query(User).filter(User.referral_code == user_refcode).first():
                    user_refcode = generate_referral_code()

                referrer = None
                if referral_code:
                    referrer = db.query(User).filter(User.referral_code == referral_code).first()

                user = User(
                    email=email,
                    name=name or email.split("@")[0],
                    avatar_url=picture,
                    password=placeholder_password,
                    confirm_password=placeholder_password,
                    referral_code=user_refcode,
                    referrer_code=referrer.referral_code if referrer else None,
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    last_login=datetime.now(timezone.utc),
                )

                from subscriptions.beta_service import BetaService
                BetaService.initialize_grace_period(user, db)

                db.add(user)
                db.flush()  # assigns user.id, needed for the Referral row below
                logger.info(f"New user created via Google OAuth: {email}")

                if referrer:
                    referrer.referral_count = (referrer.referral_count or 0) + 1
                    user.total_chops = (user.total_chops or 0) + 50
                    referrer.total_chops = (referrer.total_chops or 0) + 50
                    referrer.referral_chops = (referrer.referral_chops or 0) + 50

                    db.add(Referral(
                        referrer_id=referrer.id,
                        referred_user_id=user.id,
                        chops_awarded=50,
                        created_at=datetime.now(timezone.utc),
                    ))
                    NotificationService.create_notification(
                        db=db,
                        user_id=user.id,
                        type=NotificationType.REFERRAL_REGISTERED.value,
                        title="Welcome Bonus!",
                        message="You received 50 chops for joining via a referral link.",
                        link="/dashboard/earnings",
                    )
                    logger.info(f"New user created via Google OAuth with referral: {referral_code}")

            update_login_streak(db, user)

            db.commit()
            db.refresh(user)

            # sub must be the user's email, not id — get_current_user (the
            # dependency every authenticated endpoint uses) decodes `sub`
            # and looks the user up by User.email == sub. This previously
            # put the numeric id in `sub`, which would have made every
            # request with this token fail auth even had the rest of this
            # function not already been crashing before reaching here.
            effective_role = get_effective_role(user)
            jwt_token = create_access_token(
                data={
                    "sub": user.email,
                    "id": user.id,
                    "role": effective_role,
                    "is_admin": bool(user.is_admin),
                },
                expires_delta=timedelta(days=30)
            )

            # Redirect to frontend with token
            redirect_url = f"{FRONTEND_URL}/auth/callback?token={jwt_token}&user_id={user.id}&role={effective_role}"

            logger.info(f"Google OAuth successful for user {email}, redirecting to frontend")
            
            return RedirectResponse(url=redirect_url)
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}", exc_info=True)
        # Redirect to frontend with error
        error_url = f"{FRONTEND_URL}/login?error=oauth_failed"
        return RedirectResponse(url=error_url)
