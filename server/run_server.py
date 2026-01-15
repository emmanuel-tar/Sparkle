#!/usr/bin/env python
"""
Simple server runner script for debugging.
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings
from app.database import init_db, engine
from app.main import app

async def main():
    """Initialize and run the server."""
    # Initialize database
    print(f"Initializing database at {settings.database_url}...")
    await init_db()
    print("Database initialized successfully!")
    
    # Import uvicorn
    import uvicorn
    
    # Run server
    print(f"Starting server on 0.0.0.0:8001...")
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False,  # Disable reload
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown signal received")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
