"""
Inventory Endpoints

Product catalog and stock management.
"""

import csv
import io
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, BadRequestException, ForbiddenException
from app.models.inventory import Category, InventoryItem, StockMovement, MovementType
from app.models.location import Location
from app.models.supplier import Supplier
from app.schemas.inventory import (
    CategoryCreate,
    CategoryResponse,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    StockAdjustment,
    StockMovementResponse,
    StockMovementDetailResponse,
)
from app.api.deps import CurrentUser, DBSession, require_role, require_permission
from app.models.user import UserRole

router = APIRouter()


# ============== Categories ==============

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    db: DBSession,
    current_user: CurrentUser,
    is_active: Optional[bool] = True,
):
    """List all categories."""
    from sqlalchemy import func
    
    # Subquery to count products per category
    product_counts = (
        select(InventoryItem.category_id, func.count(InventoryItem.id).label("count"))
        .group_by(InventoryItem.category_id)
        .subquery()
    )
    
    query = (
        select(Category, func.coalesce(product_counts.c.count, 0).label("count"))
        .outerjoin(product_counts, Category.id == product_counts.c.category_id)
    )
    
    if is_active is not None:
        query = query.where(Category.is_active == is_active)
    
    result = await db.execute(query)
    categories_with_counts = result.all()
    
    output = []
    for cat, count in categories_with_counts:
        item = CategoryResponse.model_validate(cat)
        item.product_count = count
        output.append(item)
    
    return output


@router.post("/categories", response_model=CategoryResponse, status_code=201, dependencies=[Depends(require_permission("manage_inventory"))])
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
    query = select(
        InventoryItem, 
        Location.name.label("location_name"),
        Supplier.name.label("supplier_name")
    ).join(
        Location, InventoryItem.location_id == Location.id
    ).outerjoin(
        Supplier, InventoryItem.supplier_id == Supplier.id
    ).where(InventoryItem.is_active == True)
    
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
    items_with_locations = result.all()
    
    response_items = []
    for item, location_name, supplier_name in items_with_locations:
        item_dict = InventoryItemResponse.model_validate(item)
        item_dict.location_name = location_name
        item_dict.supplier_name = supplier_name
        item_dict.is_low_stock = item.is_low_stock
        
        # Calculate financials
        cost = float(item.cost_price or 0)
        selling = float(item.selling_price)
        item_dict.margin = selling - cost
        item_dict.margin_pct = (item_dict.margin / selling * 100) if selling > 0 else 0
        item_dict.markup_pct = (item_dict.margin / cost * 100) if cost > 0 else 0
        
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
        select(
            InventoryItem, 
            Location.name.label("location_name"),
            Supplier.name.label("supplier_name")
        )
        .join(Location, InventoryItem.location_id == Location.id)
        .outerjoin(Supplier, InventoryItem.supplier_id == Supplier.id)
        .where(InventoryItem.id == item_id)
    )
    row = result.one_or_none()
    
    if row is None:
        raise NotFoundException(f"Item {item_id} not found")
    
    item, location_name, supplier_name = row
    response = InventoryItemResponse.model_validate(item)
    response.location_name = location_name
    response.supplier_name = supplier_name
    response.is_low_stock = item.is_low_stock
    
    # Calculate financials
    cost = float(item.cost_price or 0)
    selling = float(item.selling_price)
    response.margin = selling - cost
    response.margin_pct = (response.margin / selling * 100) if selling > 0 else 0
    response.markup_pct = (response.margin / cost * 100) if cost > 0 else 0
    
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


@router.post("/items", response_model=InventoryItemResponse, status_code=201, dependencies=[Depends(require_permission("manage_inventory"))])
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


@router.patch("/items/{item_id}", response_model=InventoryItemResponse, dependencies=[Depends(require_permission("manage_inventory"))])
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

@router.delete("/items/{item_id}", status_code=204, dependencies=[Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))])
async def delete_inventory_item(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Deactivate an inventory item (soft delete)."""
    from app.core.exceptions import NotFoundException
    result = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if item is None:
        raise NotFoundException(f"Item {item_id} not found")
    
    # Simple soft delete by deactivating
    item.is_active = False
    await db.commit()
    return None


@router.post("/items/{item_id}/adjust", response_model=StockMovementResponse, dependencies=[Depends(require_permission("manage_inventory"))])
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


@router.get("/movements", response_model=List[StockMovementDetailResponse], dependencies=[Depends(require_permission("view_reports"))])
async def list_all_stock_movements(
    db: DBSession,
    current_user: CurrentUser,
    location_id: Optional[UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all stock movements (audit log)."""
    query = select(StockMovement, InventoryItem.name.label("item_name"), InventoryItem.sku.label("item_sku")).join(
        InventoryItem, StockMovement.item_id == InventoryItem.id
    )
    
    if location_id:
        query = query.where(InventoryItem.location_id == location_id)
    elif current_user.location_id and current_user.role != UserRole.SUPER_ADMIN:
        query = query.where(InventoryItem.location_id == current_user.location_id)
        
    result = await db.execute(
        query.order_by(StockMovement.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = result.all()
    
    output = []
    for mv, item_name, item_sku in rows:
        data = StockMovementDetailResponse.model_validate(mv)
        data.item_name = item_name
        data.item_sku = item_sku
        output.append(data)
        
    return output


# ============== Bulk Import/Export ==============

@router.get("/export", dependencies=[Depends(require_permission("view_reports"))])
async def export_inventory_csv(
    db: DBSession,
    current_user: CurrentUser,
    location_id: Optional[UUID] = None,
):
    """Export inventory to CSV."""
    query = select(
        InventoryItem, 
        Location.name.label("location_name"), 
        Category.name.label("category_name"),
        Supplier.name.label("supplier_name")
    ).join(
        Location, InventoryItem.location_id == Location.id
    ).outerjoin(
        Category, InventoryItem.category_id == Category.id
    ).outerjoin(
        Supplier, InventoryItem.supplier_id == Supplier.id
    ).where(InventoryItem.is_active == True)
    
    if location_id:
        query = query.where(InventoryItem.location_id == location_id)
    elif current_user.location_id:
        query = query.where(InventoryItem.location_id == current_user.location_id)
        
    result = await db.execute(query)
    items = result.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "SKU", "Barcode", "Name", "Description", "Category", 
        "Location", "Supplier", "Stock", "Min Stock", "Cost Price", "Selling Price", "Unit"
    ])
    
    for item, loc_name, cat_name, sup_name in items:
        writer.writerow([
            item.sku,
            item.barcode or "",
            item.name,
            item.description or "",
            cat_name or "",
            loc_name,
            sup_name or "",
            item.current_stock,
            item.min_stock_level or 0,
            item.cost_price or 0,
            item.selling_price,
            item.unit
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inventory_export_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


@router.get("/import-template")
async def get_import_template():
    """Download CSV template for inventory import."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "SKU", "Barcode", "Name", "Description", "Category", 
        "Location", "Supplier", "Stock", "Min Stock", "Cost Price", "Selling Price", "Unit"
    ])
    # Example Row
    writer.writerow([
        "PROD-001", "123456789", "Example Product", "Description here", "General",
        "Main Store", "Example Supplier", "100", "10", "500", "750", "pcs"
    ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_template.csv"}
    )


@router.post("/import", dependencies=[Depends(require_permission("manage_inventory"))])
async def import_inventory_csv(
    db: DBSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """Import inventory from CSV.
    
    Expected columns (case-insensitive):
    - SKU (required)
    - Name (required)
    - Selling Price (required)
    - Location (optional, defaults to user's location)
    - Barcode, Description, Category, Supplier, Stock, Min Stock, Cost Price, Unit (optional)
    """
    if not file.filename.endswith('.csv'):
        raise BadRequestException("Only CSV files are allowed")
    
    contents = await file.read()
    
    # Try decoding with different encodings
    text_content = None
    used_encoding = None
    for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            text_content = contents.decode(encoding)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
            
    if text_content is None:
        raise BadRequestException("Unable to decode file. Supported encodings: UTF-8, Latin-1, CP1252")

    buffer = io.StringIO(text_content)
    reader = csv.DictReader(buffer)
    
    # Validate that CSV has headers
    if not reader.fieldnames:
        raise BadRequestException("CSV file is empty or has no headers")
    
    # Normalize headers to support case-insensitive matching
    reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
    
    # Check for required columns
    required_cols = {"sku", "name", "selling price"}
    missing_cols = required_cols - set(reader.fieldnames)
    if missing_cols:
        raise BadRequestException(f"Missing required columns: {', '.join(missing_cols)}")
    
    imported_count = 0
    updated_count = 0
    errors = []
    
    # Pre-fetch locations and categories to avoid constant DB calls
    loc_result = await db.execute(select(Location))
    locations = {loc.name.lower(): loc.id for loc in loc_result.scalars().all()}
    
    cat_result = await db.execute(select(Category))
    categories = {cat.name.lower(): cat.id for cat in cat_result.scalars().all()}
    
    sup_result = await db.execute(select(Supplier))
    suppliers = {sup.name.lower(): sup.id for sup in sup_result.scalars().all()}
    
    # Check existing SKUs to detect duplicates
    existing_skus_result = await db.execute(select(InventoryItem.sku))
    existing_skus = {sku for (sku,) in existing_skus_result.all()}
    
    for row_idx, row in enumerate(reader, start=2):  # Start at 2 because row 1 is headers
        try:
            # Skip completely empty rows
            if not any(v and str(v).strip() for v in row.values()):
                continue

            # Extract and validate required fields
            sku = row.get("sku", "").strip()
            name = row.get("name", "").strip()
            selling_price_str = row.get("selling price", "").strip()
            
            if not sku:
                errors.append(f"Row {row_idx}: Missing or empty SKU")
                continue
            
            if not name:
                errors.append(f"Row {row_idx}: Missing or empty Name")
                continue
            
            if not selling_price_str:
                errors.append(f"Row {row_idx}: Missing or empty Selling Price")
                continue
            
            def parse_float(value, default=None):
                """Parse float value, handling comma separators."""
                if not value: 
                    return default
                try:
                    return float(str(value).strip().replace(',', '.'))
                except (ValueError, AttributeError):
                    return default
            
            # Parse prices
            selling_price = parse_float(selling_price_str)
            if selling_price is None or selling_price <= 0:
                errors.append(f"Row {row_idx}: Invalid Selling Price '{selling_price_str}' (must be > 0)")
                continue
            
            cost_price = parse_float(row.get("cost price"))
            
            # Find location
            loc_name = row.get("location", "").strip().lower()
            loc_id = locations.get(loc_name) if loc_name else None
            loc_id = loc_id or current_user.location_id
            
            if not loc_id:
                errors.append(f"Row {row_idx}: Location '{row.get('location')}' not found and user has no default location")
                continue
            
            # Find optional relationships
            cat_name = row.get("category", "").strip().lower()
            cat_id = categories.get(cat_name) if cat_name else None
            
            sup_name = row.get("supplier", "").strip().lower()
            sup_id = suppliers.get(sup_name) if sup_name else None
            
            # Check if item exists
            result = await db.execute(select(InventoryItem).where(InventoryItem.sku == sku))
            item = result.scalar_one_or_none()
            
            item_data = {
                "sku": sku,
                "barcode": row.get("barcode") or None,
                "name": name,
                "description": row.get("description") or None,
                "category_id": cat_id,
                "location_id": loc_id,
                "supplier_id": sup_id,
                "current_stock": parse_float(row.get("stock"), 0.0),
                "min_stock_level": parse_float(row.get("min stock")),
                "cost_price": cost_price,
                "selling_price": selling_price,
                "unit": (row.get("unit") or "pcs").strip(),
            }

            if item:
                # Update existing - only update non-null values from CSV
                for key, value in item_data.items():
                    if value is not None or key in ["barcode", "description"]:
                        setattr(item, key, value)
                updated_count += 1
            else:
                # Create new
                item = InventoryItem(**item_data)
                db.add(item)
                imported_count += 1
            
        except Exception as e:
            errors.append(f"Row {row_idx}: Unexpected error: {str(e)}")
    
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise BadRequestException(f"Database commit failed: {str(e)}")
    
    return {
        "success": len(errors) == 0,
        "imported_count": imported_count,
        "updated_count": updated_count,
        "total_processed": imported_count + updated_count,
        "errors": errors,
        "encoding_used": used_encoding,
        "message": f"Imported {imported_count} new items, updated {updated_count} existing items"
    }
