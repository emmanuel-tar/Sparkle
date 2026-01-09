"""
Purchase Order API Endpoints
"""

import uuid
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api import deps
from app.database import get_db
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, POStatus
from app.models.inventory import InventoryItem, StockMovement, MovementType
from app.models.supplier import Supplier
from app.schemas import purchase_order as schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.PurchaseOrderSummary])
async def list_purchase_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[POStatus] = None,
    supplier_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_active_user),
):
    """
    Retrieve purchase orders.
    """
    query = select(PurchaseOrder).join(Supplier)
    
    if status:
        query = query.where(PurchaseOrder.status == status)
    if supplier_id:
        query = query.where(PurchaseOrder.supplier_id == supplier_id)
        
    query = query.offset(skip).limit(limit).order_by(PurchaseOrder.created_at.desc())
    result = await db.execute(query)
    results = result.scalars().all()
    
    # Map to summary schema
    summary_results = []
    for po in results:
        summary_results.append(schemas.PurchaseOrderSummary(
            id=po.id,
            order_number=po.order_number,
            supplier_name=po.supplier.name,
            status=po.status,
            total_amount=po.total_amount,
            expected_date=po.expected_date,
            created_at=po.created_at
        ))
    
    return summary_results


@router.post("/", response_model=schemas.PurchaseOrder, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    po_in: schemas.PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_active_user),
):
    """
    Create a new purchase order.
    """
    # Check if supplier exists
    supplier = await db.get(Supplier, po_in.supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    # Check for duplicate order number
    query = select(PurchaseOrder).where(PurchaseOrder.order_number == po_in.order_number)
    result = await db.execute(query)
    existing_po = result.scalar_one_or_none()
    
    if existing_po:
        raise HTTPException(status_code=400, detail="Order number already exists")

    total_amount = 0
    po = PurchaseOrder(
        supplier_id=po_in.supplier_id,
        order_number=po_in.order_number,
        expected_date=po_in.expected_date,
        notes=po_in.notes,
        created_by_id=current_user.id,
        status=POStatus.PENDING
    )
    
    db.add(po)
    await db.flush() # Get PO ID
    
    for item_in in po_in.items:
        # Check if inventory item exists
        inv_item = await db.get(InventoryItem, item_in.item_id)
        if not inv_item:
            await db.rollback()
            raise HTTPException(status_code=404, detail=f"Inventory item {item_in.item_id} not found")
            
        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            item_id=item_in.item_id,
            quantity=item_in.quantity,
            unit_cost=item_in.unit_cost
        )
        total_amount += (item_in.quantity * float(item_in.unit_cost))
        db.add(po_item)
        
    po.total_amount = total_amount
    await db.commit()
    await db.refresh(po)
    return po


@router.get("/{po_id}", response_model=schemas.PurchaseOrder)
async def get_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_active_user),
):
    """
    Get purchase order by ID.
    """
    po = await db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


from sqlalchemy.orm import selectinload

@router.patch("/{po_id}", response_model=schemas.PurchaseOrder)
async def update_purchase_order(
    po_id: uuid.UUID,
    po_in: schemas.PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_active_user),
):
    """
    Update a purchase order status or details.
    When moving to RECEIVED, inventory levels are updated.
    """
    # Explicitly load items and their inventory items to avoid MissingGreenlet
    query = select(PurchaseOrder).options(
        selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.inventory_item)
    ).where(PurchaseOrder.id == po_id)
    
    result = await db.execute(query)
    po = result.scalar_one_or_none()
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
        
    if po.status == POStatus.RECEIVED:
        raise HTTPException(status_code=400, detail="Cannot update a received order")

    # Update basic fields
    if po_in.status is not None:
        previous_status = po.status
        po.status = po_in.status
        
        # Handle transition to RECEIVED
        if po.status == POStatus.RECEIVED and previous_status != POStatus.RECEIVED:
            po.received_date = datetime.utcnow()
            
            # Update stock levels for each item
            # Note: po.items is available via lazy="selectin"
            for po_item in po.items:
                inv_item = po_item.inventory_item # also selectin loaded
                
                # Snapshot before
                stock_before = float(inv_item.current_stock)
                
                # Update stock
                inv_item.current_stock = float(inv_item.current_stock) + float(po_item.quantity)
                # Ensure it's marked as the received qty
                po_item.received_quantity = po_item.quantity
                
                # Record movement
                movement = StockMovement(
                    item_id=inv_item.id,
                    movement_type=MovementType.PURCHASE,
                    quantity=po_item.quantity,
                    unit_cost=float(po_item.unit_cost),
                    stock_before=stock_before,
                    stock_after=float(inv_item.current_stock),
                    reference_type="purchase_order",
                    reference_id=po.id,
                    notes=f"Received PO {po.order_number}",
                    performed_by=current_user.id
                )
                db.add(movement)

    if po_in.notes is not None:
        po.notes = po_in.notes
    if po_in.expected_date is not None:
        po.expected_date = po_in.expected_date
    if po_in.supplier_id is not None:
        po.supplier_id = po_in.supplier_id

    await db.commit()
    await db.refresh(po)
    return po


@router.delete("/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_active_user),
):
    """
    Delete a purchase order (only if PENDING or CANCELLED).
    """
    po = await db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
        
    if po.status == POStatus.RECEIVED:
        raise HTTPException(status_code=400, detail="Cannot delete a received order")
        
    await db.delete(po)
    await db.commit()
    return None


@router.get("/suggest/{supplier_id}", response_model=List[schemas.PurchaseOrderItemCreate])
async def suggest_po_items(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_active_user),
):
    """
    Suggest items to order from a supplier based on low stock levels.
    """
    # Find active items for this supplier that are below reorder point
    query = select(InventoryItem).where(
        InventoryItem.supplier_id == supplier_id,
        InventoryItem.is_active == True,
        InventoryItem.current_stock <= InventoryItem.reorder_point
    )
    
    result = await db.execute(query)
    items = result.scalars().all()
    suggestions = []
    
    for item in items:
        # Suggest quantity to reach max_stock_level or a default reorder_quantity
        qty_to_order = 0
        if item.max_stock_level is not None:
            qty_to_order = float(item.max_stock_level) - float(item.current_stock)
        elif item.reorder_quantity is not None:
            qty_to_order = float(item.reorder_quantity)
        else:
            # Default fallback: double the reorder point or 10
            qty_to_order = float(item.reorder_point or 10) * 2
            
        if qty_to_order > 0:
            suggestions.append(schemas.PurchaseOrderItemCreate(
                item_id=item.id,
                quantity=qty_to_order,
                unit_cost=Decimal(str(item.cost_price or 0))
            ))
            
    return suggestions
