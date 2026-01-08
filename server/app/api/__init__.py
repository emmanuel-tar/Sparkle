"""
API Router Package

Aggregates all API routes under versioned prefixes.
"""

from fastapi import APIRouter

from app.api.v1 import router as v1_router

router = APIRouter()

# Include v1 routes
router.include_router(v1_router, prefix="/v1")
