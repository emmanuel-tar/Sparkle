"""
Authentication Schemas

Request/response models for authentication endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    """Login request schema."""
    
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    """User registration request schema."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    role: UserRole = UserRole.CASHIER
    location_id: Optional[UUID] = None


class Token(BaseModel):
    """JWT token response."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration


class TokenPayload(BaseModel):
    """JWT token payload."""
    
    sub: str
    exp: datetime
    iat: datetime
    type: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    
    refresh_token: str


class UserCreate(BaseModel):
    """User creation schema (admin use)."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = None
    role: UserRole = UserRole.CASHIER
    location_id: Optional[UUID] = None
    permissions: Optional[dict] = None


class UserUpdate(BaseModel):
    """User update schema."""
    
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    location_id: Optional[UUID] = None
    permissions: Optional[dict] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    username: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    role: UserRole
    location_id: Optional[UUID]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    
    current_password: str
    new_password: str = Field(..., min_length=8)
