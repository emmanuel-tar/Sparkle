"""
User Model

Handles authentication and role-based access control.
"""

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text, JSON

from app.models.base import GUIDType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.location import Location


class UserRole(str, Enum):
    """User roles for access control."""
    
    SUPER_ADMIN = "super_admin"      # Full system access
    ADMIN = "admin"                   # Location-level admin
    MANAGER = "manager"               # Manager with reports access
    CASHIER = "cashier"               # POS operations only
    INVENTORY = "inventory"           # Inventory management
    VIEWER = "viewer"                 # Read-only access


class User(Base, UUIDMixin, TimestampMixin):
    """
    User model for authentication and authorization.
    
    Supports role-based access control with location assignment.
    """
    
    __tablename__ = "users"
    
    # Authentication
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Role and Permissions
    role: Mapped[UserRole] = mapped_column(String(20), default=UserRole.CASHIER)
    permissions: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # Custom permissions override: {"can_give_discounts": true, "max_discount_percent": 10}
    
    # Location Assignment
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUIDType,
        ForeignKey("locations.id"),
        nullable=True,
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Session Management
    refresh_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relationships
    location: Mapped[Optional["Location"]] = relationship(
        "Location",
        back_populates="users",
        lazy="selectin"
    )
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        # Super admin has all permissions
        if self.role == UserRole.SUPER_ADMIN:
            return True
        
        # Check custom permissions
        if self.permissions and permission in self.permissions:
            return self.permissions[permission]
        
        # Default role-based permissions
        role_permissions = {
            UserRole.ADMIN: ["manage_users", "view_reports", "manage_inventory", "manage_sales"],
            UserRole.MANAGER: ["view_reports", "manage_inventory", "manage_sales"],
            UserRole.CASHIER: ["manage_sales"],
            UserRole.INVENTORY: ["manage_inventory"],
            UserRole.VIEWER: ["view_reports"],
        }
        
        return permission in role_permissions.get(self.role, [])
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
