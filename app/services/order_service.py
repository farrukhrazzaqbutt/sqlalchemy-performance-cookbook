from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import Order, OrderItem, Product
from app.schemas import OrderCreate, OrderUpdate
from typing import List, Optional
from decimal import Decimal

class OrderService:
    """Service layer for order operations"""
    
    @staticmethod
    async def create_order_with_validation(
        order_data: OrderCreate,
        user_id: int,
        db: AsyncSession
    ) -> Order:
        """Create order with comprehensive validation"""
        # Get all products in one query
        product_ids = [item.product_id for item in order_data.items]
        result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = {p.id: p for p in result.scalars().all()}
        
        if len(products) != len(product_ids):
            raise ValueError("One or more products not found")
        
        # Validate stock and calculate totals
        order_items = []
        total_amount = Decimal('0')
        
        for item_data in order_data.items:
            product = products[item_data.product_id]
            
            if product.stock_quantity < item_data.quantity:
                raise ValueError(f"Insufficient stock for product {product.name}")
            
            if not product.is_active:
                raise ValueError(f"Product {product.name} is not available")
            
            item_total = item_data.unit_price * item_data.quantity
            total_amount += item_total
            
            order_items.append(OrderItem(
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                total_price=item_total
            ))
        
        # Create order
        order = Order(
            user_id=user_id,
            total_amount=total_amount,
            shipping_address=order_data.shipping_address,
            notes=order_data.notes,
            status="pending",
            order_items=order_items
        )
        
        db.add(order)
        
        # Update product stock
        for item_data in order_data.items:
            product = products[item_data.product_id]
            product.stock_quantity -= item_data.quantity
        
        await db.commit()
        await db.refresh(order)
        
        return order
    
    @staticmethod
    async def get_order_statistics(
        user_id: Optional[int] = None,
        db: AsyncSession = None
    ) -> dict:
        """Get order statistics"""
        query = select(
            func.count(Order.id).label('total_orders'),
            func.sum(Order.total_amount).label('total_revenue'),
            func.avg(Order.total_amount).label('avg_order_value')
        )
        
        if user_id:
            query = query.where(Order.user_id == user_id)
        
        result = await db.execute(query)
        stats = result.first()
        
        return {
            'total_orders': stats.total_orders or 0,
            'total_revenue': float(stats.total_revenue or 0),
            'avg_order_value': float(stats.avg_order_value or 0)
        }
