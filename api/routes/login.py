import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic_settings import BaseSettings
from sqlalchemy.orm import Session

from db.pg_connections import get_db
from typing import Optional
from db.pg_models import ShowUser, User, AuthResponse

bearer_scheme = HTTPBearer()
router = APIRouter(prefix="", tags=["authenticate"])

"""Generating and storing the secret key"""

class Settings(BaseSettings):
    secret_key: str = os.getenv("SECRET_KEY") or secrets.token_hex(32)

settings = Settings()
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"

# Extended token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days (was 30 minutes)
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days (was 7 days)

# Environment detection
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

@router.get("/me", response_model=AuthResponse)
def me(access_token: str = Cookie(None), db: Session = Depends(get_db)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        user_id: int = payload.get("id")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "subscription_status": user.subscription_status,
        "subscription_plan": user.subscription_plan,
        "role": role,
        "access_token": access_token,
        "token_type": "bearer"
    }


def get_admin_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(authorization: Optional[str] = Header(None), access_token_cookie: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    """
    Get current user from either Authorization header or cookie.
    Priority: Authorization header > Cookie
    """
    token = None
    
    # First, try to get token from Authorization header
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() != 'bearer':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # If no Authorization header, try cookie
    elif access_token_cookie:
        token = access_token_cookie
    
    # If no token found anywhere
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role: str = payload.get("role")
        email: str = payload.get("sub")
        user_id: int = payload.get("id")
        
        if email is None:
            raise credentials_exception
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        print(f"JWT decode error: {str(e)}")
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    return {"user": user, "role": role}


@router.post("/login", response_model=AuthResponse)
def login(request: ShowUser, response: Response, db: Session = Depends(get_db)):
    """User login endpoint - returns JWT access token"""
    user = db.query(User).filter(User.email == request.email).first()

    # Check if the email is registered
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email has not been registered!"
        )

    # Verify password
    if not pwd_context.verify(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Password is incorrect!"
        )

    role = "admin" if user.is_admin else "user"

    # Generate access token with extended expiration
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": role, "id": user.id}, 
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token({"sub": user.email, "role": role, "id": user.id})

    # Set cookies with extended max_age
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION,  # True in production, False in development
        samesite="None" if IS_PRODUCTION else "lax",  # "None" for production (Stripe), "lax" for development
        max_age=60 * 60 * 24 * 7  # 7 days to match token expiration
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="None" if IS_PRODUCTION else "lax",
        max_age=60 * 60 * 24 * 30  # 30 days
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": role
    }

    
@router.post("/refresh", response_model=AuthResponse)
def refresh_token_endpoint(refresh_token: str = Cookie(None), response: Response = None, db: Session = Depends(get_db)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        user_id = payload.get("id")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired")
    except JWTError as e:
        print(f"Refresh token decode error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Issue a new access token
    access_token = create_access_token(
        {"sub": email, "role": role, "id": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Also issue a new refresh token
    new_refresh_token = create_refresh_token({"sub": email, "role": role, "id": user.id})

    # Update cookies if response is provided
    if response:
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=IS_PRODUCTION,
            samesite="None" if IS_PRODUCTION else "lax",
            max_age=60 * 60 * 24 * 7
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=IS_PRODUCTION,
            samesite="None" if IS_PRODUCTION else "lax",
            max_age=60 * 60 * 24 * 30
        )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": role
    }


@router.post("/token")
def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login for Swagger UI.
    Use email as username in the form.
    """
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user:
        print(f"User not found: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not pwd_context.verify(form_data.password, user.password):
        print(f"Password verification failed for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    role = "admin" if user.is_admin else "user"

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": role, "id": user.id}, 
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer", "role": role}