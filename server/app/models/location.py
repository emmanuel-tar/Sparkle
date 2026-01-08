"""
Location Model

Represents store locations in a multi-location retail environment.
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, String, Text, JSON

from app.models.base import GUIDType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.inventory import InventoryItem
    from app.models.sales import Sale


class Location(Base, UUIDMixin, TimestampMixin):
    """
    Store location model.
    
    Represents a physical retail location with its own inventory,
    staff, and sales tracking.
    """
    
    __tablename__ = "locations"
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Address (stored as JSON for flexibility)
    address: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Example: {"street": "123 Main St", "city": "Lagos", "state": "Lagos", "country": "Nigeria", "postal_code": "100001"}
    
    # Contact Information
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Settings and Configuration
    settings: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # Example: {"tax_rate": 7.5, "currency": "NGN", "receipt_header": "...", "receipt_footer": "..."}
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_headquarters: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", 
        back_populates="location",
        lazy="selectin"
    )
    inventory_items: Mapped[list["InventoryItem"]] = relationship(
        "InventoryItem",
        back_populates="location",
        lazy="selectin"
    )
    sales: Mapped[list["Sale"]] = relationship(
        "Sale",
        back_populates="location",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Location(id={self.id}, name='{self.name}', code='{self.code}')>"
