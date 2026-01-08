"""
Supplier Schemas

Request/response models for supplier management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, EmailStr


class SupplierBase(BaseModel):
    """Base supplier schema."""
    
    name: str = Field(..., min_length=1, max_length=200)
    contact_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    tax_id: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    is_active: bool = True


class SupplierCreate(SupplierBase):
    """Supplier creation schema."""
    pass


class SupplierUpdate(BaseModel):
    """Supplier update schema."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    tax_id: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    """Supplier response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime
    updated_at: datetime
