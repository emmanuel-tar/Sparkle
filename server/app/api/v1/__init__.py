"""
API v1 Router

Combines all v1 API endpoints.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.locations import router as locations_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.sales import router as sales_router
from app.api.v1.customers import router as customers_router

router = APIRouter()

# Authentication routes
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Resource routes
router.include_router(locations_router, prefix="/locations", tags=["Locations"])
router.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
router.include_router(sales_router, prefix="/sales", tags=["Sales"])
router.include_router(customers_router, prefix="/customers", tags=["Customers"])
