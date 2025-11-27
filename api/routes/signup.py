# load the signup page

# import the fastAPI library into
import os

from fastapi import APIRouter, Depends, Form, HTTPException

# import the function to hash the passwords
from passlib.context import CryptContext

# import the session
from sqlalchemy.orm import Session

# import the function for rendering the HTML sites
# import the database files (PostgreSQL/Neon)
from db.pg_connections import get_db

# import the user models for PostgreSQL
from db.pg_models import User

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

def generate_referral_code(length=4):
    chars = string.ascii_letters + string.digits
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
    Create a new user account.
    Accepts Form data with name, email, password, and confirm_password.
    """
    # Check if email exists
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="User already exists")

    # Validate passwords match
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    user_refcode = generate_referral_code()
    # Create user
    hashed = pwd_context.hash(password)
    passcode = pwd_context.hash(confirm_password)
    new_user = User(name=name, email=email, password=hashed, confirm_password=passcode,
                referral_code=user_refcode, referrer_code=referrer_code #optional
                )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user_id": new_user.id, "referral_code":new_user.referral_code}
