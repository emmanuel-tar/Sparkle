"""
Authentication Endpoints

Login, registration, and token management.
"""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
    REFRESH_TOKEN_TYPE,
)
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    UnauthorizedException,
)
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    Token,
    UserResponse,
    UserCreate,
    RefreshTokenRequest,
    PasswordChangeRequest,
)
from app.api.deps import CurrentUser, DBSession

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    db: DBSession,
):
    """
    Authenticate user and return access/refresh tokens.
    """
    # Find user by username
    result = await db.execute(
        select(User).where(User.username == request.username)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise UnauthorizedException("Invalid username or password")
    
    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise UnauthorizedException("Invalid username or password")
    
    # Check if user is active
    if not user.is_active:
        raise UnauthorizedException("Account is disabled")
    
    # Create tokens
    access_token = create_access_token(
        subject=str(user.id),
        additional_claims={
            "role": user.role.value if isinstance(user.role, UserRole) else user.role,
            "location_id": str(user.location_id) if user.location_id else None,
        },
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    
    # Store refresh token
    user.refresh_token = refresh_token
    await db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: DBSession,
):
    """
    Refresh access token using refresh token.
    """
    # Verify refresh token
    user_id = verify_token(request.refresh_token, REFRESH_TOKEN_TYPE)
    if user_id is None:
        raise UnauthorizedException("Invalid or expired refresh token")
    
    # Get user
    from uuid import UUID
    result = await db.execute(
        select(User).where(User.id == UUID(user_id), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise UnauthorizedException("User not found")
    
    # Verify stored refresh token matches
    if user.refresh_token != request.refresh_token:
        raise UnauthorizedException("Invalid refresh token")
    
    # Create new tokens
    access_token = create_access_token(
        subject=str(user.id),
        additional_claims={
            "role": user.role.value if isinstance(user.role, UserRole) else user.role,
            "location_id": str(user.location_id) if user.location_id else None,
        },
    )
    new_refresh_token = create_refresh_token(subject=str(user.id))
    
    # Update stored refresh token
    user.refresh_token = new_refresh_token
    await db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: DBSession,
):
    """
    Register a new user (for initial setup or self-registration).
    """
    # Check if username exists
    result = await db.execute(
        select(User).where(User.username == request.username)
    )
    if result.scalar_one_or_none():
        raise ConflictException("Username already exists")
    
    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise ConflictException("Email already exists")
    
    # Create user
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        role=request.role,
        location_id=request.location_id,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
):
    """
    Get current authenticated user's information.
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout(
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Logout user by invalidating refresh token.
    """
    current_user.refresh_token = None
    await db.commit()
    
    return {"message": "Logged out successfully"}


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Change current user's password.
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise BadRequestException("Current password is incorrect")
    
    # Update password
    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.refresh_token = None  # Invalidate all sessions
    await db.commit()
    
    return {"message": "Password changed successfully"}
