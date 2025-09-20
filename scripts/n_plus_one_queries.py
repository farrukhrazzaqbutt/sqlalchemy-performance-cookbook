#!/usr/bin/env python3
"""
SQLAlchemy Performance Cookbook: N+1 Query Problem

This script demonstrates the N+1 query problem and how to solve it using
selectinload and joinedload strategies.
"""

import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.event import listen
from app.models import User, Order, OrderItem, Product, Category
from app.db import Base
import os

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5432/app")

# Create engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Query counter
query_count = 0

def count_queries(conn, cursor, statement, parameters, context, executemany):
    global query_count
    query_count += 1

# Listen to queries
listen(engine.sync_engine, "before_cursor_execute", count_queries)

async def setup_data():
    """Setup test data"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        # Create categories
        categories = [
            Category(name="Electronics", description="Electronic devices"),
            Category(name="Books", description="Books and literature"),
            Category(name="Clothing", description="Clothing and accessories"),
        ]
        session.add_all(categories)
        await session.commit()
        
        # Create products
        products = []
        for i in range(100):
            products.append(Product(
                name=f"Product {i}",
                description=f"Description for product {i}",
                price=10.0 + (i % 50),
                stock_quantity=100,
                category_id=(i % 3) + 1,
                is_active=True
            ))
        session.add_all(products)
        await session.commit()
        
        # Create users
        users = []
        for i in range(50):
            users.append(User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                hashed_password="hashed_password",
                full_name=f"User {i}",
                is_active=True
            ))
        session.add_all(users)
        await session.commit()
        
        # Create orders with items
        orders = []
        for user_id in range(1, 51):
            for order_num in range(3):  # 3 orders per user
                order = Order(
                    user_id=user_id,
                    total_amount=100.0 + (order_num * 50),
                    status="completed",
                    shipping_address=f"Address for user {user_id}"
                )
                orders.append(order)
        
        session.add_all(orders)
        await session.commit()
        
        # Create order items
        order_items = []
        for order_id in range(1, 151):  # 150 orders
            for item_num in range(2):  # 2 items per order
                order_items.append(OrderItem(
                    order_id=order_id,
                    product_id=(order_id + item_num) % 100 + 1,
                    quantity=1 + (item_num % 3),
                    unit_price=10.0 + (order_id % 20),
                    total_price=(10.0 + (order_id % 20)) * (1 + (item_num % 3))
                ))
        
        session.add_all(order_items)
        await session.commit()

async def naive_approach():
    """Naive approach - causes N+1 queries"""
    global query_count
    query_count = 0
    
    start_time = time.perf_counter()
    
    async with AsyncSessionLocal() as session:
        # Get all orders
        result = await session.execute(select(Order).limit(20))
        orders = result.scalars().all()
        
        # Access related data (triggers N+1 queries)
        for order in orders:
            # This will trigger a query for each order
            user = await session.get(User, order.user_id)
            # This will trigger a query for each order
            order_items = await session.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            items = order_items.scalars().all()
            
            # This will trigger a query for each order item
            for item in items:
                product = await session.get(Product, item.product_id)
    
    end_time = time.perf_counter()
    
    return {
        "approach": "Naive (N+1 queries)",
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
        "orders_processed": 20
    }

async def selectinload_approach():
    """Optimized approach using selectinload"""
    global query_count
    query_count = 0
    
    start_time = time.perf_counter()
    
    async with AsyncSessionLocal() as session:
        # Get orders with eager loading
        result = await session.execute(
            select(Order)
            .options(
                selectinload(Order.user),
                selectinload(Order.order_items).selectinload(OrderItem.product)
            )
            .limit(20)
        )
        orders = result.scalars().all()
        
        # Access related data (no additional queries)
        for order in orders:
            user = order.user
            for item in order.order_items:
                product = item.product
    
    end_time = time.perf_counter()
    
    return {
        "approach": "Selectinload",
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
        "orders_processed": 20
    }

async def joinedload_approach():
    """Optimized approach using joinedload"""
    global query_count
    query_count = 0
    
    start_time = time.perf_counter()
    
    async with AsyncSessionLocal() as session:
        # Get orders with eager loading using joins
        result = await session.execute(
            select(Order)
            .options(
                joinedload(Order.user),
                joinedload(Order.order_items).joinedload(OrderItem.product)
            )
            .limit(20)
        )
        orders = result.unique().scalars().all()
        
        # Access related data (no additional queries)
        for order in orders:
            user = order.user
            for item in order.order_items:
                product = item.product
    
    end_time = time.perf_counter()
    
    return {
        "approach": "Joinedload",
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
        "orders_processed": 20
    }

async def main():
    """Run the N+1 query benchmark"""
    print("Setting up test data...")
    await setup_data()
    
    print("\nRunning N+1 Query Performance Tests...")
    print("=" * 60)
    
    # Run tests
    results = []
    
    print("1. Testing naive approach (N+1 queries)...")
    results.append(await naive_approach())
    
    print("2. Testing selectinload approach...")
    results.append(await selectinload_approach())
    
    print("3. Testing joinedload approach...")
    results.append(await joinedload_approach())
    
    # Print results table
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"{'Approach':<20} {'Queries':<10} {'Time (ms)':<12} {'Orders':<10}")
    print("-" * 60)
    
    for result in results:
        print(f"{result['approach']:<20} {result['queries']:<10} {result['time_ms']:<12} {result['orders_processed']:<10}")
    
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    print("• Naive approach: Each order and order item triggers separate queries")
    print("• Selectinload: Uses separate SELECT queries for each relationship")
    print("• Joinedload: Uses JOINs to load all data in fewer queries")
    print("\n• Selectinload is better for one-to-many relationships")
    print("• Joinedload is better for many-to-one relationships")
    print("• Both approaches eliminate N+1 queries effectively")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
