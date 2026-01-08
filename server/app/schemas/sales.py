"""
Sales Schemas

Request/response models for POS transactions.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.sales import PaymentMethod, SaleStatus


class SaleItemCreate(BaseModel):
    """Sale item creation schema."""
    
    item_id: UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    discount_percent: float = Field(0, ge=0, le=100)
    discount_amount: float = Field(0, ge=0)


class SaleCreate(BaseModel):
    """Sale creation schema."""
    
    location_id: UUID
    terminal_id: Optional[str] = None
    customer_id: Optional[UUID] = None
    
    items: List[SaleItemCreate] = Field(..., min_length=1)
    
    discount_amount: float = Field(0, ge=0)
    discount_reason: Optional[str] = None
    
    payment_method: PaymentMethod
    payment_details: Optional[dict] = None
    amount_tendered: Optional[float] = None
    
    points_redeemed: int = Field(0, ge=0)
    notes: Optional[str] = None
    
    # For offline sync
    sync_id: Optional[str] = None
    offline_created: bool = False


class SaleItemResponse(BaseModel):
    """Sale item response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    item_id: UUID
    sku: str
    name: str
    quantity: float
    unit_price: float
    cost_price: Optional[float]
    discount_percent: float
    discount_amount: float
    tax_rate: float
    tax_amount: float
    line_total: float


class SaleResponse(BaseModel):
    """Sale response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    receipt_number: str
    location_id: UUID
    terminal_id: Optional[str]
    customer_id: Optional[UUID]
    cashier_id: UUID
    
    subtotal: float
    tax_amount: float
    discount_amount: float
    discount_reason: Optional[str]
    total_amount: float
    
    payment_method: PaymentMethod
    payment_details: Optional[dict]
    amount_tendered: Optional[float]
    change_given: Optional[float]
    
    status: SaleStatus
    is_synced: bool
    
    points_earned: int
    points_redeemed: int
    
    items: List[SaleItemResponse]
    
    created_at: datetime


class SaleSummary(BaseModel):
    """Daily sales summary schema."""
    
    date: datetime
    total_sales: int
    total_revenue: float
    total_tax: float
    total_discounts: float
    average_sale: float
    top_products: List[dict]
