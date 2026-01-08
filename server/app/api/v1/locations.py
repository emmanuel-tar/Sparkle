"""
Location Endpoints

CRUD operations for store locations.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, ForbiddenException
from app.models.location import Location
from app.models.user import UserRole
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from app.schemas.common import PaginatedResponse
from app.api.deps import CurrentUser, DBSession, require_role

router = APIRouter()


@router.get("", response_model=List[LocationResponse])
async def list_locations(
    db: DBSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: Optional[bool] = None,
):
    """
    List all locations.
    """
    query = select(Location)
    
    if is_active is not None:
        query = query.where(Location.is_active == is_active)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    locations = result.scalars().all()
    
    return [LocationResponse.model_validate(loc) for loc in locations]


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Get a specific location by ID.
    """
    result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if location is None:
        raise NotFoundException(f"Location {location_id} not found")
    
    return LocationResponse.model_validate(location)


@router.post("", response_model=LocationResponse, status_code=201, dependencies=[Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))])
async def create_location(
    request: LocationCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Create a new location (admin only).
    """
    # Check if code exists
    result = await db.execute(
        select(Location).where(Location.code == request.code)
    )
    if result.scalar_one_or_none():
        raise ConflictException(f"Location code '{request.code}' already exists")
    
    # Create location
    location = Location(
        name=request.name,
        code=request.code,
        description=request.description,
        address=request.address.model_dump() if request.address else None,
        phone=request.phone,
        email=request.email,
        settings=request.settings.model_dump() if request.settings else {},
        is_headquarters=request.is_headquarters,
    )
    
    db.add(location)
    await db.commit()
    await db.refresh(location)
    
    return LocationResponse.model_validate(location)


@router.patch("/{location_id}", response_model=LocationResponse, dependencies=[Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))])
async def update_location(
    location_id: UUID,
    request: LocationUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Update a location (admin only).
    """
    # Get location
    result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if location is None:
        raise NotFoundException(f"Location {location_id} not found")
    
    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    
    if "address" in update_data and update_data["address"]:
        update_data["address"] = update_data["address"].model_dump() if hasattr(update_data["address"], "model_dump") else update_data["address"]
    
    if "settings" in update_data and update_data["settings"]:
        update_data["settings"] = update_data["settings"].model_dump() if hasattr(update_data["settings"], "model_dump") else update_data["settings"]
    
    for field, value in update_data.items():
        setattr(location, field, value)
    
    await db.commit()
    await db.refresh(location)
    
    return LocationResponse.model_validate(location)


@router.delete("/{location_id}", dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))])
async def delete_location(
    location_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Soft delete a location (super admin only).
    """
    result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if location is None:
        raise NotFoundException(f"Location {location_id} not found")
    
    location.is_active = False
    await db.commit()
    
    return {"message": f"Location {location.name} has been deactivated"}
