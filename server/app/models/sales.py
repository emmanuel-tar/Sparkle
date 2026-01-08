"""
Sales Models

Transaction tracking for POS operations.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, GUIDType

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.customer import Customer


class PaymentMethod(str, Enum):
    """Supported payment methods."""
    
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    MOBILE = "mobile"      # Mobile money (e.g., M-Pesa)
    CREDIT = "credit"      # Store credit
    SPLIT = "split"        # Multiple payment methods


class SaleStatus(str, Enum):
    """Status of a sale transaction."""
    
    PENDING = "pending"         # Sale in progress
    COMPLETED = "completed"     # Sale finalized
    VOID = "void"               # Sale cancelled
    REFUNDED = "refunded"       # Full refund issued
    PARTIAL_REFUND = "partial_refund"  # Partial refund issued


class Sale(Base, UUIDMixin, TimestampMixin):
    """
    Sale transaction model.
    
    Records all POS transactions with full audit trail.
    """
    
    __tablename__ = "sales"
    
    # Transaction Reference
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    
    # Location and Terminal
    location_id: Mapped[uuid.UUID] = mapped_column(
        GUIDType,
        ForeignKey("locations.id"),
        nullable=False,
    )
    terminal_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Customer (optional for walk-in)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUIDType,
        ForeignKey("customers.id"),
        nullable=True,
    )
    
    # Cashier
    cashier_id: Mapped[uuid.UUID] = mapped_column(
        GUIDType,
        ForeignKey("users.id"),
        nullable=False,
    )
    
    # Amounts
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    discount_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Payment
    payment_method: Mapped[PaymentMethod] = mapped_column(String(20), nullable=False)
    payment_details: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # For split payments: {"cash": 5000, "card": 3000}
    # For card: {"last_four": "1234", "auth_code": "ABC123"}
    
    amount_tendered: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    change_given: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Status
    status: Mapped[SaleStatus] = mapped_column(String(20), default=SaleStatus.COMPLETED)
    
    # Sync Status (for offline support)
    is_synced: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    offline_created: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Loyalty Points
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    points_redeemed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Denormalized items for quick access (JSON copy of items)
    items_snapshot: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    
    # Metadata
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    
    # Relationships
    location: Mapped["Location"] = relationship(
        "Location",
        back_populates="sales",
    )
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="sales",
    )
    items: Mapped[list["SaleItem"]] = relationship(
        "SaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Sale(id={self.id}, receipt='{self.receipt_number}', total={self.total_amount})>"


class SaleItem(Base, UUIDMixin):
    """
    Individual item in a sale transaction.
    
    Links products to sales with quantity and pricing details.
    """
    
    __tablename__ = "sale_items"
    
    # Sale Reference
    sale_id: Mapped[uuid.UUID] = mapped_column(
        GUIDType,
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Product Reference (snapshot at time of sale)
    item_id: Mapped[uuid.UUID] = mapped_column(
        GUIDType,
        ForeignKey("inventory_items.id"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Quantity and Pricing
    quantity: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cost_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Discounts
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    
    # Tax
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    
    # Line Total
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    sale: Mapped["Sale"] = relationship(
        "Sale",
        back_populates="items",
    )
    
    def __repr__(self) -> str:
        return f"<SaleItem(sku='{self.sku}', qty={self.quantity}, total={self.line_total})>"
