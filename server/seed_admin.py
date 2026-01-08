
import asyncio
import sys
from pathlib import Path

# Add the current directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session_factory
from app.models.user import User, UserRole
from app.models.location import Location
from app.core.security import get_password_hash

async def seed_admin():
    print("Seeding initial data...")
    async with async_session_factory() as session:
        # Create a default location if none exists
        from sqlalchemy import select
        res = await session.execute(select(Location).limit(1))
        location = res.scalar_one_or_none()
        
        if not location:
            location = Location(
                name="Main Warehouse",
                code="WH01",
                is_active=True
            )
            session.add(location)
            await session.flush()
        
        # Check for existing admin
        res = await session.execute(select(User).where(User.username == "admin"))
        admin = res.scalar_one_or_none()
        
        if not admin:
            admin = User(
                username="admin",
                email="admin@retailpro.local",
                hashed_password=get_password_hash("admin123"),
                first_name="System",
                last_name="Administrator",
                role=UserRole.SUPER_ADMIN,
                location_id=location.id,
                is_active=True,
                is_verified=True
            )
            session.add(admin)
        else:
            admin.location_id = location.id
            
        try:
            await session.commit()
            print("Seeding successful!")
            print(f"Admin ('{admin.username}') assigned to location: {location.name}")
        except Exception as e:
            await session.rollback()
            print(f"Error seeding: {e}")

if __name__ == "__main__":
    asyncio.run(seed_admin())
