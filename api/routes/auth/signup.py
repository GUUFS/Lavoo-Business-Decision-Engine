# load the signup page

# import the fastAPI library into
import os

from fastapi import APIRouter, Depends, Form, HTTPException

from datetime import datetime

# import the function to hash the passwords
from passlib.context import CryptContext

# import the session
from sqlalchemy.orm import Session

# import the function for rendering the HTML sites
# import the database files (PostgreSQL/Neon)
from database.pg_connections import get_db

# import the user models for PostgreSQL
from database.pg_models import User, Referral

# import the email function
from fastapi import BackgroundTasks
from emailing.email_service import email_service
from api.services.notification_service import NotificationService
from database.pg_models import NotificationType

import random, string
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["signup"])

# call the function for hashing the user's password
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# for the project's static folder done with react.js
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # get the absolute path of the file
BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(CURRENT_DIR))
)  # get the current directory of the file
OUT_DIR = os.path.join(BASE_DIR, "web")  # get the absolute path of the out folder

def generate_referral_code(length=8):
    chars = string.ascii_uppercase + string.digits  # Allowed symbols
    return ''.join(random.choice(chars) for _ in range(length))

@router.post("/signup")
def signup(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    company_name: str = Form(None),
    referrer_code: str = Form(None),
    db: Session = Depends(get_db),
):
    """
    Create a new user account with optional referral support.
    """
    # Check if email exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Validate passwords match
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Validate and fetch referrer if code provided
    referrer = None
    if referrer_code and referrer_code.strip():
        search_code = referrer_code.upper().strip()
        referrer = db.query(User).filter(
            User.referral_code == search_code
        ).first()

        if not referrer:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid referral code. No matching user found."
            )

        logger.info(f"Referral code '{search_code}' validated for referrer ID {referrer.id}")

    # Generate unique referral code for new user
    user_refcode = generate_referral_code()

    # Ensure referral code is unique
    while db.query(User).filter(User.referral_code == user_refcode).first():
        user_refcode = generate_referral_code()

    # Create user
    hashed = pwd_context.hash(password)
    passcode = pwd_context.hash(confirm_password)
    new_user = User(
        name=name,
        email=email,
        password=hashed,
        confirm_password=passcode,
        referral_code=user_refcode,
        referrer_code=referrer.referral_code if referrer else None,
        company_name=company_name if company_name else None,
    )

    from subscriptions.beta_service import BetaService
    BetaService.initialize_grace_period(new_user, db)

    db.add(new_user)
    db.flush()

    # Process referral rewards (Note: Chops awarding removed as per user request)
    if referrer:
        # Update referrer stats (Increment count only, no chops)
        referrer.referral_count = (referrer.referral_count or 0) + 1

        # Create referral record with 0 chops
        referral = Referral(
            referrer_id=referrer.id,
            referred_user_id=new_user.id,
            chops_awarded=0,
            created_at=datetime.utcnow()
        )
        db.add(referral)
        
        # Notify referrer
        NotificationService.create_notification(
            db=db,
            user_id=referrer.id,
            type=NotificationType.REFERRAL_REGISTERED.value,
            title="New Referral!",
            message=f"{new_user.name} has registered using your link.",
            link="/dashboard/referrals"
        )

    try:
        db.commit()
        db.refresh(new_user)
        logger.info(f"User {new_user.email} created successfully (ID: {new_user.id})")
    except Exception as e:
        db.rollback()
        logger.error(f"Database commit failed during signup: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred during signup")

    # Send welcome email
    background_tasks.add_task(
        email_service.send_welcome_email,
        new_user.email,
        new_user.name
    )

    return {
        "message": "User created successfully",
        "user_id": new_user.id,
        "referral_code": new_user.referral_code,
        "referral_applied": referrer is not None
    }
