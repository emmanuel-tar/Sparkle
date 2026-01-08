"""
Customer Endpoints

Customer management and loyalty program.
"""

import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse, LoyaltyPointsAdjustment
from app.api.deps import CurrentUser, DBSession

router = APIRouter()


def generate_loyalty_card_number() -> str:
    """Generate unique loyalty card number."""
    return f"LYL-{uuid.uuid4().hex[:12].upper()}"


@router.get("", response_model=List[CustomerResponse])
async def list_customers(
    db: DBSession,
    current_user: CurrentUser,
    search: Optional[str] = None,
    is_active: Optional[bool] = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List customers with search."""
    query = select(Customer)
    
    if is_active is not None:
        query = query.where(Customer.is_active == is_active)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Customer.first_name.ilike(search_pattern),
                Customer.last_name.ilike(search_pattern),
                Customer.phone.ilike(search_pattern),
                Customer.email.ilike(search_pattern),
                Customer.loyalty_card_number.ilike(search_pattern),
            )
        )
    
    query = query.order_by(Customer.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    customers = result.scalars().all()
    
    return [CustomerResponse.model_validate(c) for c in customers]


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get a specific customer."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if customer is None:
        raise NotFoundException(f"Customer {customer_id} not found")
    
    return CustomerResponse.model_validate(customer)


@router.get("/phone/{phone}", response_model=CustomerResponse)
async def get_customer_by_phone(
    phone: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get customer by phone number (for POS lookup)."""
    result = await db.execute(
        select(Customer).where(Customer.phone == phone)
    )
    customer = result.scalar_one_or_none()
    
    if customer is None:
        raise NotFoundException(f"Customer with phone '{phone}' not found")
    
    return CustomerResponse.model_validate(customer)


@router.get("/loyalty/{card_number}", response_model=CustomerResponse)
async def get_customer_by_loyalty_card(
    card_number: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get customer by loyalty card number."""
    result = await db.execute(
        select(Customer).where(Customer.loyalty_card_number == card_number)
    )
    customer = result.scalar_one_or_none()
    
    if customer is None:
        raise NotFoundException(f"Customer with card '{card_number}' not found")
    
    return CustomerResponse.model_validate(customer)


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    request: CustomerCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new customer."""
    # Check for duplicate phone
    result = await db.execute(
        select(Customer).where(Customer.phone == request.phone)
    )
    if result.scalar_one_or_none():
        raise ConflictException(f"Phone number '{request.phone}' already registered")
    
    # Check for duplicate email
    if request.email:
        result = await db.execute(
            select(Customer).where(Customer.email == request.email)
        )
        if result.scalar_one_or_none():
            raise ConflictException(f"Email '{request.email}' already registered")
    
    # Create customer with loyalty card
    customer_data = request.model_dump()
    customer_data["loyalty_card_number"] = generate_loyalty_card_number()
    
    customer = Customer(**customer_data)
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    
    return CustomerResponse.model_validate(customer)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    request: CustomerUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Update a customer."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if customer is None:
        raise NotFoundException(f"Customer {customer_id} not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    await db.commit()
    await db.refresh(customer)
    
    return CustomerResponse.model_validate(customer)


@router.post("/{customer_id}/points", response_model=CustomerResponse)
async def adjust_loyalty_points(
    customer_id: UUID,
    request: LoyaltyPointsAdjustment,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Manually adjust customer loyalty points.
    
    Use positive value to add points, negative to deduct.
    """
    if request.customer_id != customer_id:
        from app.core.exceptions import BadRequestException
        raise BadRequestException("Customer ID mismatch")
    
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if customer is None:
        raise NotFoundException(f"Customer {customer_id} not found")
    
    if request.points > 0:
        customer.add_points(request.points)
    else:
        if not customer.redeem_points(abs(request.points)):
            from app.core.exceptions import BadRequestException
            raise BadRequestException("Insufficient points for redemption")
    
    await db.commit()
    await db.refresh(customer)
    
    return CustomerResponse.model_validate(customer)
