
import asyncio
import sys
from pathlib import Path

# Add the current directory to sys.path to import the app
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine
from app.models.base import Base
import app.models  # Ensure all models are loaded

async def init_db():
    print("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
