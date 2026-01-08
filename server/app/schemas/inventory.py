"""
Inventory Schemas

Request/response models for inventory management.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.inventory import MovementType


class CategoryCreate(BaseModel):
    """Category creation schema."""
    
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryResponse(BaseModel):
    """Category response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    description: Optional[str]
    parent_id: Optional[UUID]
    icon: Optional[str]
    color: Optional[str]
    is_active: bool
    created_at: datetime


class InventoryItemCreate(BaseModel):
    """Inventory item creation schema."""
    
    sku: str = Field(..., min_length=1, max_length=50)
    barcode: Optional[str] = Field(None, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    location_id: UUID
    
    # Stock
    current_stock: float = 0
    min_stock_level: Optional[float] = None
    max_stock_level: Optional[float] = None
    reorder_point: Optional[float] = None
    reorder_quantity: Optional[float] = None
    
    # Pricing
    cost_price: Optional[float] = None
    selling_price: float = Field(..., gt=0)
    tax_rate: float = 0
    
    # Units
    unit: str = "pcs"
    weight: Optional[float] = None
    
    # Images
    image_url: Optional[str] = None
    images: Optional[List[str]] = None
    
    # Flags
    is_taxable: bool = True
    allow_negative_stock: bool = False
    has_expiry: bool = False
    shelf_life_days: Optional[int] = None


class InventoryItemUpdate(BaseModel):
    """Inventory item update schema."""
    
    barcode: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    
    min_stock_level: Optional[float] = None
    max_stock_level: Optional[float] = None
    reorder_point: Optional[float] = None
    reorder_quantity: Optional[float] = None
    
    cost_price: Optional[float] = None
    selling_price: Optional[float] = Field(None, gt=0)
    tax_rate: Optional[float] = None
    
    unit: Optional[str] = None
    weight: Optional[float] = None
    
    image_url: Optional[str] = None
    images: Optional[List[str]] = None
    
    is_active: Optional[bool] = None
    is_taxable: Optional[bool] = None
    allow_negative_stock: Optional[bool] = None
    has_expiry: Optional[bool] = None
    shelf_life_days: Optional[int] = None


class InventoryItemResponse(BaseModel):
    """Inventory item response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    sku: str
    barcode: Optional[str]
    name: str
    description: Optional[str]
    category_id: Optional[UUID]
    location_id: UUID
    
    current_stock: float
    reserved_stock: float
    min_stock_level: Optional[float]
    max_stock_level: Optional[float]
    reorder_point: Optional[float]
    
    cost_price: Optional[float]
    selling_price: float
    tax_rate: float
    
    unit: str
    image_url: Optional[str]
    
    is_active: bool
    is_taxable: bool
    is_low_stock: bool = False
    
    created_at: datetime
    updated_at: datetime


class StockAdjustment(BaseModel):
    """Stock adjustment request schema."""
    
    item_id: UUID
    quantity: float = Field(..., description="Positive to add, negative to subtract")
    movement_type: MovementType
    notes: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[datetime] = None
    unit_cost: Optional[float] = None


class StockMovementResponse(BaseModel):
    """Stock movement response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    item_id: UUID
    movement_type: MovementType
    quantity: float
    unit_cost: Optional[float]
    stock_before: float
    stock_after: float
    notes: Optional[str]
    batch_number: Optional[str]
    created_at: datetime
