"""
Supplier Endpoints

CRUD operations for managing inventory suppliers.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, Depends
from sqlalchemy import select, or_

from app.core.exceptions import ConflictException, NotFoundException, BadRequestException, ForbiddenException
from app.models.supplier import Supplier
from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
)
from app.api.deps import CurrentUser, DBSession, require_role, require_permission
from app.models.user import UserRole

router = APIRouter()


@router.get("", response_model=List[SupplierResponse])
async def list_suppliers(
    db: DBSession,
    current_user: CurrentUser,
    is_active: Optional[bool] = True,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """
    List suppliers with search and filtering.
    """
    query = select(Supplier)
    
    if is_active is not None:
        query = query.where(Supplier.is_active == is_active)
        
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Supplier.name.ilike(search_pattern),
                Supplier.contact_name.ilike(search_pattern),
                Supplier.email.ilike(search_pattern),
            )
        )
        
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    suppliers = result.scalars().all()
    
    return [SupplierResponse.model_validate(s) for s in suppliers]


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get a specific supplier."""
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    
    if supplier is None:
        raise NotFoundException(f"Supplier {supplier_id} not found")
        
    return SupplierResponse.model_validate(supplier)


@router.post("", response_model=SupplierResponse, status_code=201, dependencies=[Depends(require_permission("manage_inventory"))])
async def create_supplier(
    request: SupplierCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new supplier."""
    # Check for duplicate name
    result = await db.execute(
        select(Supplier).where(Supplier.name == request.name)
    )
    if result.scalar_one_or_none():
        raise ConflictException(f"Supplier with name '{request.name}' already exists")
        
    supplier = Supplier(**request.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    
    return SupplierResponse.model_validate(supplier)


@router.patch("/{supplier_id}", response_model=SupplierResponse, dependencies=[Depends(require_permission("manage_inventory"))])
async def update_supplier(
    supplier_id: UUID,
    request: SupplierUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Update a supplier."""
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    
    if supplier is None:
        raise NotFoundException(f"Supplier {supplier_id} not found")
        
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
        
    await db.commit()
    await db.refresh(supplier)
    
    return SupplierResponse.model_validate(supplier)


@router.delete("/{supplier_id}", status_code=204, dependencies=[Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))])
async def deactivate_supplier(
    supplier_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Deactivate a supplier (soft delete)."""
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    
    if supplier is None:
        raise NotFoundException(f"Supplier {supplier_id} not found")
        
    supplier.is_active = False
    await db.commit()
    return None
