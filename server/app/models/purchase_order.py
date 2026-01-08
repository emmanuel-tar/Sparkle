"""
Purchase Order Models

Tracks orders sent to suppliers and status of stock replenishment.
"""

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Optional
from datetime import datetime

from sqlalchemy import String, Text, Boolean, ForeignKey, Numeric, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, GUIDType

if TYPE_CHECKING:
    from app.models.supplier import Supplier
    from app.models.inventory import InventoryItem, StockMovement
    from app.models.user import User


class POStatus(str, Enum):
    """Status of a Purchase Order."""
    PENDING = "pending"       # Draft / Not yet sent
    ORDERED = "ordered"       # Sent to supplier
    RECEIVED = "received"     # Stock has arrived and been added
    CANCELLED = "cancelled"   # Order aborted
    PARTIAL = "partial"       # Partial delivery received


class PurchaseOrder(Base, UUIDMixin, TimestampMixin):
    """
    Purchase Order (PO) model.
    """
    
    __tablename__ = "purchase_orders"
    
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        GUIDType,
        ForeignKey("suppliers.id"),
        nullable=False,
    )
    
    status: Mapped[POStatus] = mapped_column(
        String(20),
        default=POStatus.PENDING,
        nullable=False,
    )
    
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    expected_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Who created the PO
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUIDType,
        ForeignKey("users.id"),
        nullable=True,
    )
    
    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="purchase_orders")
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
    )
    created_by: Mapped[Optional["User"]] = relationship("User")
    
    def __repr__(self) -> str:
        return f"<PurchaseOrder(id={self.id}, number='{self.order_number}', status='{self.status}')>"


class PurchaseOrderItem(Base, UUIDMixin, TimestampMixin):
    """
    Individual items within a Purchase Order.
    """
    
    __tablename__ = "purchase_order_items"
    
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        GUIDType,
        ForeignKey("purchase_orders.id"),
        nullable=False,
    )
    
    item_id: Mapped[uuid.UUID] = mapped_column(
        GUIDType,
        ForeignKey("inventory_items.id"),
        nullable=False,
    )
    
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    received_quantity: Mapped[float] = mapped_column(Numeric(12, 3), default=0)
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="items")
    inventory_item: Mapped["InventoryItem"] = relationship("InventoryItem")
    
    def __repr__(self) -> str:
        return f"<PurchaseOrderItem(id={self.id}, po_id={self.purchase_order_id}, qty={self.quantity})>"
