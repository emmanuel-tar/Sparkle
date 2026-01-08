"""
FastAPI Application Entry Point

Main application configuration with middleware, exception handlers, and route registration.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import AppException
from app.database import close_db, init_db
from app.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    await init_db()
    print("Database initialized")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    await close_db()
    print("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Full-featured retail ERP system with client-server architecture",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    # Log the error in production
    if not settings.debug:
        # TODO: Add proper logging
        pass
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.debug else None,
        },
    )


# Health Check Endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/health",
    }


# Register API Routes
app.include_router(api_router, prefix="/api")


# WebSocket endpoint placeholder
@app.websocket("/ws")
async def websocket_endpoint():
    """WebSocket endpoint for real-time updates."""
    # TODO: Implement WebSocket handling
    pass
