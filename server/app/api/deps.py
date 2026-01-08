"""
API Dependencies

Common dependencies for API endpoints.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import verify_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.models.user import User, UserRole

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Dependency to get the current authenticated user.
    
    Validates the JWT token and returns the user object.
    """
    token = credentials.credentials
    
    # Verify token
    user_id = verify_token(token)
    if user_id is None:
        raise UnauthorizedException("Invalid or expired token")
    
    # Get user from database
    try:
        uuid = UUID(user_id)
    except ValueError:
        raise UnauthorizedException("Invalid token payload")
    
    result = await db.execute(
        select(User).where(User.id == uuid, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise UnauthorizedException("User not found or inactive")
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency to get current active user."""
    if not current_user.is_active:
        raise ForbiddenException("User account is disabled")
    return current_user


def require_role(*roles: UserRole):
    """
    Dependency factory to require specific roles.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    async def check_role(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in roles:
            raise ForbiddenException(
                f"Access denied. Required roles: {[r.value for r in roles]}"
            )
        return current_user
    
    return check_role


def require_permission(permission: str):
    """
    Dependency factory to require specific permission.
    
    Usage:
        @router.get("/reports", dependencies=[Depends(require_permission("view_reports"))])
    """
    async def check_permission(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if not current_user.has_permission(permission):
            raise ForbiddenException(f"Access denied. Required permission: {permission}")
        return current_user
    
    return check_permission


# Type aliases for cleaner endpoint signatures
CurrentUser = Annotated[User, Depends(get_current_active_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
