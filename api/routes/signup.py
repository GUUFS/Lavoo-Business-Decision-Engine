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
from db.pg_connections import get_db

# import the user models for PostgreSQL
from db.pg_models import User, Referral

import random, string

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
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    referrer_code: str = Form(None),
    db: Session = Depends(get_db),
):
    """
    Create a new user account with optional referral support.
    """
    # 🔍 DEBUG: Print what we received
    print(f"DEBUG - Received referrer_code: '{referrer_code}'")
    print(f"DEBUG - Type: {type(referrer_code)}")

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
        # 🔍 DEBUG: Show what we're searching for
        search_code = referrer_code.upper().strip()
        print(f"DEBUG - Searching for referral_code: '{search_code}'")

        # 🔍 DEBUG: Show all referral codes in database
        all_codes = db.query(User.referral_code).all()
        print(f"DEBUG - All referral codes in DB: {[code[0] for code in all_codes]}")

        referrer = db.query(User).filter(
            User.referral_code == search_code
        ).first()

        if not referrer:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid referral code: '{referrer_code}'. No matching user found."
            )

        print(f"DEBUG - Found referrer: {referrer.name} (ID: {referrer.id})")

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
    )

    db.add(new_user)
    db.flush()

    # Process referral rewards
    if referrer:
        # Determine chops based on subscription status
        chops = 20 if referrer.subscription_status == "active" else 10

        # Update referrer stats (handle None values)
        referrer.total_chops = (referrer.total_chops or 0) + chops
        referrer.referral_chops = (referrer.referral_chops or 0) + chops
        referrer.referral_count = (referrer.referral_count or 0) + 1

        # Create referral record
        referral = Referral(
            referrer_id=referrer.id,
            referred_user_id=new_user.id,
            chops_awarded=chops,
            created_at=datetime.utcnow()
        )
        db.add(referral)

    db.commit()
    db.refresh(new_user)

    return {
        "message": "User created successfully",
        "user_id": new_user.id,
        "referral_code": new_user.referral_code,
        "referral_applied": referrer is not None
    }
