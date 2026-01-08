"""
Inventory Endpoints

Product catalog and stock management.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, BadRequestException
from app.models.inventory import Category, InventoryItem, StockMovement, MovementType
from app.schemas.inventory import (
    CategoryCreate,
    CategoryResponse,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    StockAdjustment,
    StockMovementResponse,
)
from app.api.deps import CurrentUser, DBSession

router = APIRouter()


# ============== Categories ==============

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    db: DBSession,
    current_user: CurrentUser,
    is_active: Optional[bool] = True,
):
    """List all categories."""
    query = select(Category)
    if is_active is not None:
        query = query.where(Category.is_active == is_active)
    
    result = await db.execute(query)
    categories = result.scalars().all()
    
    return [CategoryResponse.model_validate(cat) for cat in categories]


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    request: CategoryCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new category."""
    category = Category(**request.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    return CategoryResponse.model_validate(category)


# ============== Inventory Items ==============

@router.get("/items", response_model=List[InventoryItemResponse])
async def list_inventory_items(
    db: DBSession,
    current_user: CurrentUser,
    location_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    search: Optional[str] = None,
    low_stock_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """
    List inventory items with filtering and search.
    """
    query = select(InventoryItem).where(InventoryItem.is_active == True)
    
    # Location filter (required for non-super-admin)
    if location_id:
        query = query.where(InventoryItem.location_id == location_id)
    elif current_user.location_id:
        query = query.where(InventoryItem.location_id == current_user.location_id)
    
    # Category filter
    if category_id:
        query = query.where(InventoryItem.category_id == category_id)
    
    # Search
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                InventoryItem.name.ilike(search_pattern),
                InventoryItem.sku.ilike(search_pattern),
                InventoryItem.barcode.ilike(search_pattern),
            )
        )
    
    # Pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    response_items = []
    for item in items:
        item_dict = InventoryItemResponse.model_validate(item)
        item_dict.is_low_stock = item.is_low_stock
        response_items.append(item_dict)
    
    # Filter low stock if requested
    if low_stock_only:
        response_items = [i for i in response_items if i.is_low_stock]
    
    return response_items


@router.get("/items/{item_id}", response_model=InventoryItemResponse)
async def get_inventory_item(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get a specific inventory item."""
    result = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if item is None:
        raise NotFoundException(f"Item {item_id} not found")
    
    response = InventoryItemResponse.model_validate(item)
    response.is_low_stock = item.is_low_stock
    return response


@router.get("/items/barcode/{barcode}", response_model=InventoryItemResponse)
async def get_item_by_barcode(
    barcode: str,
    db: DBSession,
    current_user: CurrentUser,
    location_id: Optional[UUID] = None,
):
    """Get item by barcode (for POS scanning)."""
    query = select(InventoryItem).where(
        InventoryItem.barcode == barcode,
        InventoryItem.is_active == True,
    )
    
    if location_id:
        query = query.where(InventoryItem.location_id == location_id)
    elif current_user.location_id:
        query = query.where(InventoryItem.location_id == current_user.location_id)
    
    result = await db.execute(query)
    item = result.scalar_one_or_none()
    
    if item is None:
        raise NotFoundException(f"Item with barcode '{barcode}' not found")
    
    return InventoryItemResponse.model_validate(item)


@router.post("/items", response_model=InventoryItemResponse, status_code=201)
async def create_inventory_item(
    request: InventoryItemCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new inventory item."""
    # Check for duplicate SKU
    result = await db.execute(
        select(InventoryItem).where(InventoryItem.sku == request.sku)
    )
    if result.scalar_one_or_none():
        raise ConflictException(f"SKU '{request.sku}' already exists")
    
    # Check for duplicate barcode
    if request.barcode:
        result = await db.execute(
            select(InventoryItem).where(InventoryItem.barcode == request.barcode)
        )
        if result.scalar_one_or_none():
            raise ConflictException(f"Barcode '{request.barcode}' already exists")
    
    item = InventoryItem(**request.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    return InventoryItemResponse.model_validate(item)


@router.patch("/items/{item_id}", response_model=InventoryItemResponse)
async def update_inventory_item(
    item_id: UUID,
    request: InventoryItemUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Update an inventory item."""
    result = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if item is None:
        raise NotFoundException(f"Item {item_id} not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    await db.commit()
    await db.refresh(item)
    
    return InventoryItemResponse.model_validate(item)


@router.post("/items/{item_id}/adjust", response_model=StockMovementResponse)
async def adjust_stock(
    item_id: UUID,
    request: StockAdjustment,
    db: DBSession,
    current_user: CurrentUser,
):
    """Adjust stock level for an item."""
    if request.item_id != item_id:
        raise BadRequestException("Item ID mismatch")
    
    result = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if item is None:
        raise NotFoundException(f"Item {item_id} not found")
    
    stock_before = float(item.current_stock)
    new_stock = stock_before + request.quantity
    
    if new_stock < 0 and not item.allow_negative_stock:
        raise BadRequestException(
            f"Insufficient stock. Current: {stock_before}, Requested: {request.quantity}"
        )
    
    # Update stock
    item.current_stock = new_stock
    
    # Create movement record
    movement = StockMovement(
        item_id=item_id,
        movement_type=request.movement_type,
        quantity=request.quantity,
        unit_cost=request.unit_cost,
        stock_before=stock_before,
        stock_after=new_stock,
        notes=request.notes,
        batch_number=request.batch_number,
        expiry_date=request.expiry_date,
        performed_by=current_user.id,
    )
    
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    
    return StockMovementResponse.model_validate(movement)


@router.get("/items/{item_id}/movements", response_model=List[StockMovementResponse])
async def get_stock_movements(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Get stock movement history for an item."""
    result = await db.execute(
        select(StockMovement)
        .where(StockMovement.item_id == item_id)
        .order_by(StockMovement.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    movements = result.scalars().all()
    
    return [StockMovementResponse.model_validate(m) for m in movements]
