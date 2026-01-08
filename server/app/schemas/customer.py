"""
Customer Schemas

Request/response models for customer management.
"""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.customer import LoyaltyTier


class CustomerCreate(BaseModel):
    """Customer creation schema."""
    
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    phone: str = Field(..., min_length=10, max_length=20)
    
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    
    address: Optional[dict] = None
    preferences: Optional[dict] = None
    
    sms_opt_in: bool = True
    email_opt_in: bool = True
    
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class CustomerUpdate(BaseModel):
    """Customer update schema."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    
    address: Optional[dict] = None
    preferences: Optional[dict] = None
    
    sms_opt_in: Optional[bool] = None
    email_opt_in: Optional[bool] = None
    
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class CustomerResponse(BaseModel):
    """Customer response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    first_name: str
    last_name: str
    email: Optional[str]
    phone: str
    
    loyalty_card_number: Optional[str]
    loyalty_tier: LoyaltyTier
    loyalty_points: int
    lifetime_points: int
    
    date_of_birth: Optional[date]
    gender: Optional[str]
    address: Optional[dict]
    
    total_purchases: int
    total_spent: float
    average_order_value: float
    last_purchase_date: Optional[datetime]
    
    store_credit: float
    is_active: bool
    
    tags: Optional[List[str]]
    
    created_at: datetime
    updated_at: datetime
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class LoyaltyPointsAdjustment(BaseModel):
    """Loyalty points adjustment schema."""
    
    customer_id: UUID
    points: int = Field(..., description="Positive to add, negative to redeem")
    reason: str = Field(..., min_length=1, max_length=200)
