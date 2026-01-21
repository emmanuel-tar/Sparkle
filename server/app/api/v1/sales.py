"""
Sales Endpoints

POS transaction processing and sales history.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.sales import Sale, SaleItem, SaleStatus, PaymentMethod
from app.models.inventory import InventoryItem, StockMovement, MovementType
from app.models.customer import Customer
from app.models.user import UserRole
from app.schemas.sales import SaleCreate, SaleResponse, SaleItemResponse
from app.api.deps import CurrentUser, DBSession, require_role, require_permission

router = APIRouter()


def generate_receipt_number(location_code: str = "HQ") -> str:
    """Generate unique receipt number."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = uuid.uuid4().hex[:4].upper()
    return f"RCP-{location_code}-{timestamp}-{random_suffix}"


@router.get("", response_model=List[SaleResponse])
async def list_sales(
    db: DBSession,
    current_user: CurrentUser,
    location_id: Optional[UUID] = None,
    customer_id: Optional[UUID] = None,
    status: Optional[SaleStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List sales with filters."""
    from sqlalchemy.orm import selectinload
    query = select(Sale).options(
        selectinload(Sale.items),
        selectinload(Sale.customer)
    )
    
    # Location filter
    if location_id:
        query = query.where(Sale.location_id == location_id)
    elif current_user.location_id:
        query = query.where(Sale.location_id == current_user.location_id)
    
    if customer_id:
        query = query.where(Sale.customer_id == customer_id)
    
    if status:
        query = query.where(Sale.status == status)
    
    if date_from:
        query = query.where(Sale.created_at >= date_from)
    
    if date_to:
        query = query.where(Sale.created_at <= date_to)
    
    query = query.order_by(Sale.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    sales = result.scalars().all()
    
    return [SaleResponse.model_validate(sale) for sale in sales]


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get a specific sale by ID."""
    result = await db.execute(
        select(Sale).where(Sale.id == sale_id)
    )
    sale = result.scalar_one_or_none()
    
    if sale is None:
        raise NotFoundException(f"Sale {sale_id} not found")
    
    return SaleResponse.model_validate(sale)


@router.get("/receipt/{receipt_number}", response_model=SaleResponse)
async def get_sale_by_receipt(
    receipt_number: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get a sale by receipt number."""
    result = await db.execute(
        select(Sale).where(Sale.receipt_number == receipt_number)
    )
    sale = result.scalar_one_or_none()
    
    if sale is None:
        raise NotFoundException(f"Sale with receipt '{receipt_number}' not found")
    
    return SaleResponse.model_validate(sale)


@router.post("", response_model=SaleResponse, status_code=201, dependencies=[Depends(require_permission("manage_sales"))])
async def create_sale(
    request: SaleCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Create a new sale (POS transaction).

    This endpoint:
    1. Validates all items exist and have sufficient stock
    2. Calculates totals with tax and discounts
    3. Deducts inventory
    4. Awards loyalty points if customer is provided
    5. Creates the sale record
    """
    # Determine location ID
    final_location_id = request.location_id
    if final_location_id is None:
        final_location_id = current_user.location_id

    if final_location_id is None:
        raise BadRequestException("Location ID is required for sales")

    # Validate items and calculate totals
    sale_items = []
    subtotal = 0.0
    total_tax = 0.0
    items_snapshot = []
    
    for item_data in request.items:
        # Get inventory item
        result = await db.execute(
            select(InventoryItem).where(InventoryItem.id == item_data.item_id)
        )
        inv_item = result.scalar_one_or_none()
        
        if inv_item is None:
            raise BadRequestException(f"Item {item_data.item_id} not found")
        
        # Check stock
        available = float(inv_item.current_stock) - float(inv_item.reserved_stock)
        if item_data.quantity > available and not inv_item.allow_negative_stock:
            raise BadRequestException(
                f"Insufficient stock for {inv_item.name}. Available: {available}"
            )
        
        # Calculate line totals
        line_subtotal = item_data.quantity * item_data.unit_price
        line_discount = item_data.discount_amount + (line_subtotal * item_data.discount_percent / 100)
        line_taxable = line_subtotal - line_discount
        line_tax = line_taxable * float(inv_item.tax_rate) / 100 if inv_item.is_taxable else 0
        line_total = line_taxable + line_tax
        
        subtotal += line_subtotal
        total_tax += line_tax
        
        # Create sale item
        sale_item = SaleItem(
            item_id=inv_item.id,
            sku=inv_item.sku,
            name=inv_item.name,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            cost_price=float(inv_item.cost_price) if inv_item.cost_price else None,
            discount_percent=item_data.discount_percent,
            discount_amount=line_discount,
            tax_rate=float(inv_item.tax_rate),
            tax_amount=line_tax,
            line_total=line_total,
        )
        sale_items.append(sale_item)
        
        # Snapshot for denormalization
        items_snapshot.append({
            "sku": inv_item.sku,
            "name": inv_item.name,
            "quantity": item_data.quantity,
            "unit_price": item_data.unit_price,
            "line_total": line_total,
        })
        
        # Deduct stock
        stock_before = float(inv_item.current_stock)
        inv_item.current_stock = stock_before - item_data.quantity
        
        # Create stock movement
        movement = StockMovement(
            item_id=inv_item.id,
            movement_type=MovementType.SALE,
            quantity=-item_data.quantity,
            stock_before=stock_before,
            stock_after=float(inv_item.current_stock),
            performed_by=current_user.id,
        )
        db.add(movement)
    
    # Calculate totals
    total_amount = subtotal - request.discount_amount + total_tax
    change_given = None
    if request.amount_tendered and request.payment_method == PaymentMethod.CASH:
        change_given = request.amount_tendered - total_amount
        if change_given < 0:
            raise BadRequestException("Amount tendered is less than total")
    
    # Generate receipt number
    receipt_number = generate_receipt_number()
    
    # Handle customer loyalty
    points_earned = 0
    if request.customer_id:
        result = await db.execute(
            select(Customer).where(Customer.id == request.customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if customer:
            # Award points (1 point per 100 spent)
            points_earned = int(total_amount // 100)
            customer.add_points(points_earned)
            
            # Handle points redemption
            if request.points_redeemed > 0:
                if not customer.redeem_points(request.points_redeemed):
                    raise BadRequestException("Insufficient loyalty points")
            
            # Update customer stats
            customer.total_purchases += 1
            customer.total_spent = float(customer.total_spent) + total_amount
            customer.average_order_value = float(customer.total_spent) / customer.total_purchases
            customer.last_purchase_date = datetime.now(timezone.utc)
    
    # Create sale
    sale = Sale(
        receipt_number=receipt_number,
        location_id=final_location_id,
        terminal_id=request.terminal_id,
        customer_id=request.customer_id,
        cashier_id=current_user.id,
        subtotal=subtotal,
        tax_amount=total_tax,
        discount_amount=request.discount_amount,
        discount_reason=request.discount_reason,
        total_amount=total_amount,
        payment_method=request.payment_method,
        payment_details=request.payment_details,
        amount_tendered=request.amount_tendered,
        change_given=change_given,
        status=SaleStatus.COMPLETED,
        is_synced=not request.offline_created,
        sync_id=request.sync_id,
        offline_created=request.offline_created,
        points_earned=points_earned,
        points_redeemed=request.points_redeemed,
        notes=request.notes,
        items_snapshot=items_snapshot,
    )
    
    # Add items to sale
    for sale_item in sale_items:
        sale_item.sale_id = sale.id
        sale.items.append(sale_item)
    
    db.add(sale)
    await db.commit()
    await db.refresh(sale)
    
    # Convert to dict to avoid SQLAlchemy relationship lazy loading issues
    # Pydantic will try to access relationships which causes async errors
    sale_data = {
        "id": sale.id,
        "receipt_number": sale.receipt_number,
        "location_id": sale.location_id,
        "terminal_id": sale.terminal_id,
        "customer_id": sale.customer_id,
        "cashier_id": sale.cashier_id,
        "subtotal": float(sale.subtotal),
        "tax_amount": float(sale.tax_amount),
        "discount_amount": float(sale.discount_amount),
        "discount_reason": sale.discount_reason,
        "total_amount": float(sale.total_amount),
        "payment_method": sale.payment_method,
        "payment_details": sale.payment_details,
        "amount_tendered": float(sale.amount_tendered) if sale.amount_tendered else None,
        "change_given": float(sale.change_given) if sale.change_given else None,
        "status": sale.status,
        "is_synced": sale.is_synced,
        "points_earned": sale.points_earned,
        "points_redeemed": sale.points_redeemed,
        "items_snapshot": sale.items_snapshot,
        "created_at": sale.created_at,
        "items": [
            {
                "id": item.id,
                "item_id": item.item_id,
                "sku": item.sku,
                "name": item.name,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "cost_price": float(item.cost_price) if item.cost_price else None,
                "discount_percent": float(item.discount_percent),
                "discount_amount": float(item.discount_amount),
                "tax_rate": float(item.tax_rate),
                "tax_amount": float(item.tax_amount),
                "line_total": float(item.line_total),
            }
            for item in sale.items  # Use the items from the refreshed sale
        ],
        "customer": None,  # Customer is optional and not loaded here
    }
    
    return SaleResponse.model_validate(sale_data)


@router.post("/{sale_id}/void", response_model=SaleResponse, dependencies=[Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))])
async def void_sale(
    sale_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Void a sale transaction.
    
    This reverses inventory deductions and marks the sale as void.
    """
    result = await db.execute(
        select(Sale).where(Sale.id == sale_id)
    )
    sale = result.scalar_one_or_none()
    
    if sale is None:
        raise NotFoundException(f"Sale {sale_id} not found")
    
    if sale.status == SaleStatus.VOID:
        raise BadRequestException("Sale is already voided")
    
    # Reverse inventory deductions
    for sale_item in sale.items:
        result = await db.execute(
            select(InventoryItem).where(InventoryItem.id == sale_item.item_id)
        )
        inv_item = result.scalar_one_or_none()
        
        if inv_item:
            stock_before = float(inv_item.current_stock)
            inv_item.current_stock = stock_before + float(sale_item.quantity)
            
            # Create reversal movement
            movement = StockMovement(
                item_id=inv_item.id,
                movement_type=MovementType.RETURN_IN,
                quantity=float(sale_item.quantity),
                stock_before=stock_before,
                stock_after=float(inv_item.current_stock),
                reference_type="sale_void",
                reference_id=sale.id,
                performed_by=current_user.id,
            )
            db.add(movement)
    
    # Reverse loyalty points if applicable
    if sale.customer_id and sale.points_earned > 0:
        result = await db.execute(
            select(Customer).where(Customer.id == sale.customer_id)
        )
        customer = result.scalar_one_or_none()
        if customer:
            customer.loyalty_points -= sale.points_earned
            customer.lifetime_points -= sale.points_earned
    
    sale.status = SaleStatus.VOID
    await db.commit()
    await db.refresh(sale)
    
    return SaleResponse.model_validate(sale)
