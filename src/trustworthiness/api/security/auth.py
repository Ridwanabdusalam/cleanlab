"""
Authentication and authorization functionality.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from ...models import User, TokenData

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, settings) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), settings = None):
    """Get the current user from a JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # In a real app, you would fetch the user from a database here
    user = get_user_fake_db(username)
    if user is None:
        raise credentials_exception
    return user


def get_user_fake_db(username: str) -> Optional[User]:
    """Fake user database lookup."""
    # In a real app, this would query a database
    if username == "testuser":
        return User(
            username=username,
            email="test@example.com",
            full_name="Test User",
            disabled=False,
            hashed_password=get_password_hash("testpassword")
        )
    return None


def get_settings():
    """Dependency to get settings."""
    # This will be overridden by FastAPI's dependency_overrides
    pass


def setup_authentication(app):
    """Set up authentication for the application."""
    # This is where you would set up any authentication middleware
    # For now, we'll just add a dependency on the settings
    app.dependency_overrides[get_settings] = lambda: app.state.settings
