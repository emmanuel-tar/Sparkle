"""
Customer Models

Customer profiles and loyalty program management.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
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

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.sales import Sale


class LoyaltyTier(str, Enum):
    """Customer loyalty tiers."""
    
    BRONZE = "bronze"       # Base tier
    SILVER = "silver"       # 1000+ points
    GOLD = "gold"           # 5000+ points
    PLATINUM = "platinum"   # 15000+ points
    DIAMOND = "diamond"     # 50000+ points


class Customer(Base, UUIDMixin, TimestampMixin):
    """
    Customer profile model.
    
    Tracks customer information, loyalty points, and purchase history.
    """
    
    __tablename__ = "customers"
    
    # Basic Information
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    
    # Loyalty
    loyalty_card_number: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, index=True)
    loyalty_tier: Mapped[LoyaltyTier] = mapped_column(String(20), default=LoyaltyTier.BRONZE)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_points: Mapped[int] = mapped_column(Integer, default=0)
    
    # Demographics
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Address
    address: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Preferences
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # Example: {"preferred_categories": [...], "communication_opt_in": true, "language": "en"}
    
    # Analytics
    total_purchases: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    average_order_value: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    last_purchase_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Store Credit
    store_credit: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Marketing
    sms_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    email_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Tags for segmentation
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    
    # AI/ML Data
    ai_insights: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # Example: {"predicted_clv": 50000, "churn_risk": 0.2, "next_purchase_probability": {...}}
    
    # Relationships
    sales: Mapped[list["Sale"]] = relationship(
        "Sale",
        back_populates="customer",
        order_by="Sale.created_at.desc()",
    )
    
    @property
    def full_name(self) -> str:
        """Get customer's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def add_points(self, points: int) -> None:
        """Add loyalty points and update tier if needed."""
        self.loyalty_points += points
        self.lifetime_points += points
        self._update_tier()
    
    def redeem_points(self, points: int) -> bool:
        """Redeem loyalty points if sufficient balance."""
        if points > self.loyalty_points:
            return False
        self.loyalty_points -= points
        return True
    
    def _update_tier(self) -> None:
        """Update loyalty tier based on lifetime points."""
        if self.lifetime_points >= 50000:
            self.loyalty_tier = LoyaltyTier.DIAMOND
        elif self.lifetime_points >= 15000:
            self.loyalty_tier = LoyaltyTier.PLATINUM
        elif self.lifetime_points >= 5000:
            self.loyalty_tier = LoyaltyTier.GOLD
        elif self.lifetime_points >= 1000:
            self.loyalty_tier = LoyaltyTier.SILVER
        else:
            self.loyalty_tier = LoyaltyTier.BRONZE
    
    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name='{self.full_name}', tier='{self.loyalty_tier}')>"
