"""
Inventory Models

Product catalog, stock tracking, and category management.
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
    from app.models.supplier import Supplier


class Category(Base, UUIDMixin, TimestampMixin):
    """Product category for organizing inventory."""
    
    __tablename__ = "categories"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUIDType,
        ForeignKey("categories.id"),
        nullable=True,
    )
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Self-referential relationship for subcategories
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
    )
    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
    )
    
    # Products in this category
    products: Mapped[list["InventoryItem"]] = relationship(
        "InventoryItem",
        back_populates="category",
    )
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"


class InventoryItem(Base, UUIDMixin, TimestampMixin):
    """
    Product/inventory item model.
    
    Tracks stock levels, pricing, and AI-related parameters.
    """
    
    __tablename__ = "inventory_items"
    
    # Basic Information
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Category
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUIDType,
        ForeignKey("categories.id"),
        nullable=True,
    )
    
    # Location (for multi-location inventory)
    location_id: Mapped[uuid.UUID] = mapped_column(
        GUIDType,
        ForeignKey("locations.id"),
        nullable=False,
    )
    
    # Stock Levels
    current_stock: Mapped[float] = mapped_column(Numeric(10, 3), default=0)
    reserved_stock: Mapped[float] = mapped_column(Numeric(10, 3), default=0)
    min_stock_level: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    max_stock_level: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    reorder_point: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    reorder_quantity: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    
    @property
    def available_stock(self) -> float:
        """Calculate available stock (current - reserved)."""
        return float(self.current_stock) - float(self.reserved_stock)
    
    @property
    def is_low_stock(self) -> bool:
        """Check if stock is below minimum level."""
        if self.min_stock_level is None:
            return False
        return float(self.current_stock) <= float(self.min_stock_level)
    
    # Pricing
    cost_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    selling_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    
    @property
    def profit_margin(self) -> Optional[float]:
        """Calculate profit margin percentage."""
        if self.cost_price is None or self.cost_price == 0:
            return None
        return ((float(self.selling_price) - float(self.cost_price)) / float(self.cost_price)) * 100
    
    # Unit Information
    unit: Mapped[str] = mapped_column(String(20), default="pcs")  # pcs, kg, ltr, etc.
    weight: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)  # in kg
    
    # Images
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    images: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    
    # AI/ML Parameters
    ai_parameters: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # Example: {"demand_model": "seasonal", "forecast_accuracy": 0.85, "price_elasticity": -1.2}
    
    trend_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Sustainability
    carbon_footprint: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_taxable: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_negative_stock: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Expiry Tracking (for perishables)
    has_expiry: Mapped[bool] = mapped_column(Boolean, default=False)
    shelf_life_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Supplier
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUIDType,
        ForeignKey("suppliers.id"),
        nullable=True,
    )
    
    # Relationships
    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="products",
    )
    location: Mapped["Location"] = relationship(
        "Location",
        back_populates="inventory_items",
    )
    supplier: Mapped[Optional["Supplier"]] = relationship(
        "Supplier",
        back_populates="products",
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement",
        back_populates="item",
        order_by="StockMovement.created_at.desc()",
    )
    
    def __repr__(self) -> str:
        return f"<InventoryItem(id={self.id}, sku='{self.sku}', name='{self.name}')>"


class MovementType(str, Enum):
    """Types of stock movements."""
    
    PURCHASE = "purchase"           # Stock received from supplier
    SALE = "sale"                   # Stock sold to customer
    RETURN_IN = "return_in"         # Customer return
    RETURN_OUT = "return_out"       # Return to supplier
    ADJUSTMENT = "adjustment"       # Manual stock adjustment
    TRANSFER_IN = "transfer_in"     # Transfer from another location
    TRANSFER_OUT = "transfer_out"   # Transfer to another location
    DAMAGE = "damage"               # Damaged/written off
    EXPIRED = "expired"             # Expired stock
    COUNT = "count"                 # Physical count adjustment


class StockMovement(Base, UUIDMixin, TimestampMixin):
    """
    Stock movement tracking.
    
    Records all inventory changes for audit trail.
    """
    
    __tablename__ = "stock_movements"
    
    # Item Reference
    item_id: Mapped[uuid.UUID] = mapped_column(
        GUIDType,
        ForeignKey("inventory_items.id"),
        nullable=False,
    )
    
    # Movement Details
    movement_type: Mapped[MovementType] = mapped_column(String(20), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    unit_cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Stock Levels (snapshot)
    stock_before: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    stock_after: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    
    # Reference
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUIDType, nullable=True)
    # Example: reference_type="sale", reference_id=<sale_id>
    
    # Additional Info
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    batch_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Who performed the movement
    performed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUIDType,
        ForeignKey("users.id"),
        nullable=True,
    )
    
    # Relationships
    item: Mapped["InventoryItem"] = relationship(
        "InventoryItem",
        back_populates="stock_movements",
    )
    
    def __repr__(self) -> str:
        return f"<StockMovement(id={self.id}, type='{self.movement_type}', qty={self.quantity})>"
