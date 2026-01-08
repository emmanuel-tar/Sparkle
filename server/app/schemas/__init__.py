"""
Pydantic Schemas Package

Request/response models for API validation.
"""

from app.schemas.auth import (
    Token,
    TokenPayload,
    LoginRequest,
    RegisterRequest,
    UserResponse,
    UserCreate,
    UserUpdate,
)
from app.schemas.location import (
    LocationCreate,
    LocationUpdate,
    LocationResponse,
)
from app.schemas.inventory import (
    CategoryCreate,
    CategoryResponse,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    StockAdjustment,
)
from app.schemas.sales import (
    SaleCreate,
    SaleItemCreate,
    SaleResponse,
    SaleItemResponse,
)
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
)
from app.schemas.common import (
    PaginatedResponse,
    SuccessResponse,
    ErrorResponse,
)

__all__ = [
    # Auth
    "Token",
    "TokenPayload",
    "LoginRequest",
    "RegisterRequest",
    "UserResponse",
    "UserCreate",
    "UserUpdate",
    # Location
    "LocationCreate",
    "LocationUpdate",
    "LocationResponse",
    # Inventory
    "CategoryCreate",
    "CategoryResponse",
    "InventoryItemCreate",
    "InventoryItemUpdate",
    "InventoryItemResponse",
    "StockAdjustment",
    # Sales
    "SaleCreate",
    "SaleItemCreate",
    "SaleResponse",
    "SaleItemResponse",
    # Customer
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    # Common
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
]
