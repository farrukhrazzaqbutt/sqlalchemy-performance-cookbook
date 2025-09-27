from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.deps import get_current_active_user, get_db
from app.models import Order, OrderItem, Product, User
from app.schemas import Order as OrderSchema
from app.schemas import OrderCreate
from app.schemas import OrderItem as OrderItemSchema
from app.schemas import OrderUpdate, PaginatedResponse, PaginationParams

router = APIRouter()


@router.post("/", response_model=OrderSchema)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new order"""
    # Verify all products exist and have sufficient stock
    product_ids = [item.product_id for item in order_data.items]
    result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
    products = {p.id: p for p in result.scalars().all()}

    if len(products) != len(product_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more products not found",
        )

    # Check stock and calculate totals
    order_items = []
    total_amount = Decimal("0")

    for item_data in order_data.items:
        product = products[item_data.product_id]

        if product.stock_quantity < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {product.name}",
            )

        item_total = item_data.unit_price * item_data.quantity
        total_amount += item_total

        order_items.append(
            OrderItem(
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                total_price=item_total,
            )
        )

    # Create order
    order = Order(
        user_id=current_user.id,
        total_amount=total_amount,
        shipping_address=order_data.shipping_address,
        notes=order_data.notes,
        status="pending",
        order_items=order_items,
    )

    db.add(order)

    # Update product stock
    for item_data in order_data.items:
        product = products[item_data.product_id]
        product.stock_quantity -= item_data.quantity

    await db.commit()
    await db.refresh(order)

    return order


@router.get("/", response_model=PaginatedResponse)
async def get_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get paginated list of orders"""
    # Build query with eager loading
    query = select(Order).options(
        selectinload(Order.order_items).joinedload(OrderItem.product),
        joinedload(Order.user),
    )

    # Apply filters
    filters = []

    # Non-admin users can only see their own orders
    if not current_user.is_admin:
        filters.append(Order.user_id == current_user.id)

    if status:
        filters.append(Order.status == status)

    if filters:
        query = query.where(and_(*filters))

    # Apply sorting
    if sort_by and hasattr(Order, sort_by):
        sort_column = getattr(Order, sort_by)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(Order.created_at))

    # Get total count
    count_query = select(func.count(Order.id))
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    # Execute query
    result = await db.execute(query)
    orders = result.unique().scalars().all()

    # Calculate pages
    pages = (total + size - 1) // size

    return PaginatedResponse(
        items=[OrderSchema.model_validate(order) for order in orders],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/{order_id}", response_model=OrderSchema)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get order by ID"""
    query = (
        select(Order)
        .options(
            selectinload(Order.order_items).joinedload(OrderItem.product),
            joinedload(Order.user),
        )
        .where(Order.id == order_id)
    )

    # Non-admin users can only see their own orders
    if not current_user.is_admin:
        query = query.where(Order.user_id == current_user.id)

    result = await db.execute(query)
    order = result.unique().scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    return order


@router.put("/{order_id}", response_model=OrderSchema)
async def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update order (admin only for status changes)"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # Non-admin users can only update their own orders and only certain fields
    if not current_user.is_admin and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Update fields
    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        # Non-admin users can't change status
        if field == "status" and not current_user.is_admin:
            continue
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)

    return order
