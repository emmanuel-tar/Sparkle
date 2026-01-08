"""
Location Schemas

Request/response models for location management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AddressSchema(BaseModel):
    """Address schema for locations."""
    
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "Nigeria"
    postal_code: Optional[str] = None


class LocationSettings(BaseModel):
    """Location settings schema."""
    
    tax_rate: float = 7.5
    currency: str = "NGN"
    receipt_header: Optional[str] = None
    receipt_footer: Optional[str] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None


class LocationCreate(BaseModel):
    """Location creation schema."""
    
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    description: Optional[str] = None
    address: Optional[AddressSchema] = None
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    settings: Optional[LocationSettings] = None
    is_headquarters: bool = False


class LocationUpdate(BaseModel):
    """Location update schema."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    address: Optional[AddressSchema] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    settings: Optional[LocationSettings] = None
    is_active: Optional[bool] = None
    is_headquarters: Optional[bool] = None


class LocationResponse(BaseModel):
    """Location response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    code: str
    description: Optional[str]
    address: Optional[dict]
    phone: Optional[str]
    email: Optional[str]
    settings: Optional[dict]
    is_active: bool
    is_headquarters: bool
    created_at: datetime
    updated_at: datetime
