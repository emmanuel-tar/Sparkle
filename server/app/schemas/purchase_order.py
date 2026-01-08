"""
Purchase Order Schemas
"""

import uuid
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.purchase_order import POStatus
from app.schemas.supplier import SupplierResponse as Supplier
from app.schemas.inventory import InventoryItemResponse as InventoryItem


class PurchaseOrderItemBase(BaseModel):
    item_id: uuid.UUID
    quantity: float = Field(..., gt=0)
    unit_cost: Decimal = Field(..., gt=0)


class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass


class PurchaseOrderItemUpdate(BaseModel):
    quantity: Optional[float] = None
    received_quantity: Optional[float] = None
    unit_cost: Optional[Decimal] = None


class PurchaseOrderItem(PurchaseOrderItemBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    purchase_order_id: uuid.UUID
    received_quantity: float
    inventory_item: Optional[InventoryItem] = None


class PurchaseOrderBase(BaseModel):
    supplier_id: uuid.UUID
    order_number: str
    expected_date: Optional[datetime] = None
    notes: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    items: List[PurchaseOrderItemCreate]


class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[uuid.UUID] = None
    status: Optional[POStatus] = None
    expected_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: Optional[List[PurchaseOrderItemCreate]] = None


class PurchaseOrder(PurchaseOrderBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    status: POStatus
    total_amount: Decimal
    received_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[uuid.UUID] = None
    
    supplier: Supplier
    items: List[PurchaseOrderItem]


class PurchaseOrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    order_number: str
    supplier_name: str
    status: POStatus
    total_amount: Decimal
    expected_date: Optional[datetime] = None
    created_at: datetime
