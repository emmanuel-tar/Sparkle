"""
Supplier Model

Tracks inventory suppliers and their contact information.
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, GUIDType

if TYPE_CHECKING:
    from app.models.inventory import InventoryItem
    from app.models.purchase_order import PurchaseOrder


class Supplier(Base, UUIDMixin, TimestampMixin):
    """
    Supplier/Vendor model.
    """
    
    __tablename__ = "suppliers"
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    products: Mapped[list["InventoryItem"]] = relationship(
        "InventoryItem",
        back_populates="supplier",
    )
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        "PurchaseOrder",
        back_populates="supplier",
    )
    
    def __repr__(self) -> str:
        return f"<Supplier(id={self.id}, name='{self.name}')>"
