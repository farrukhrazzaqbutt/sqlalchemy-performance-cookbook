#!/usr/bin/env python3
"""
SQLAlchemy Performance Cookbook: Indexing Performance

This script demonstrates the impact of indexes on query performance,
comparing queries with and without proper indexing.
"""

import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text, and_, or_, func, Index
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
            Category(name="Home", description="Home and garden"),
            Category(name="Sports", description="Sports and fitness"),
        ]
        session.add_all(categories)
        await session.commit()
        
        # Create products (50,000 records)
        products = []
        for i in range(50000):
            products.append(Product(
                name=f"Product {i:06d}",
                description=f"Description for product {i}",
                price=10.0 + (i % 1000),
                stock_quantity=100 + (i % 500),
                category_id=(i % 5) + 1,
                is_active=True if i % 10 != 0 else False
            ))
        session.add_all(products)
        await session.commit()
        
        # Create users (10,000 records)
        users = []
        for i in range(10000):
            users.append(User(
                email=f"user{i:05d}@example.com",
                username=f"user{i:05d}",
                hashed_password="hashed_password",
                full_name=f"User {i}",
                is_active=True if i % 20 != 0 else False,
                is_admin=True if i % 1000 == 0 else False
            ))
        session.add_all(users)
        await session.commit()
        
        # Create orders (100,000 records)
        orders = []
        for i in range(100000):
            orders.append(Order(
                user_id=(i % 10000) + 1,
                total_amount=10.0 + (i % 1000),
                status=["pending", "completed", "shipped", "cancelled"][i % 4],
                shipping_address=f"Address for order {i}"
            ))
        session.add_all(orders)
        await session.commit()
        
        # Create order items (200,000 records)
        order_items = []
        for i in range(200000):
            order_items.append(OrderItem(
                order_id=(i % 100000) + 1,
                product_id=(i % 50000) + 1,
                quantity=1 + (i % 5),
                unit_price=10.0 + (i % 100),
                total_price=(10.0 + (i % 100)) * (1 + (i % 5))
            ))
        session.add_all(order_items)
        await session.commit()

async def drop_indexes():
    """Drop all custom indexes for testing"""
    async with engine.begin() as conn:
        # Drop custom indexes
        indexes_to_drop = [
            "idx_user_email_active",
            "idx_user_created_at", 
            "idx_product_category_active",
            "idx_product_price",
            "idx_product_created_at",
            "idx_order_user_status",
            "idx_order_created_at",
            "idx_order_status",
            "idx_order_item_order",
            "idx_order_item_product"
        ]
        
        for index_name in indexes_to_drop:
            try:
                await conn.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
            except Exception as e:
                print(f"Could not drop index {index_name}: {e}")

async def create_indexes():
    """Create custom indexes for testing"""
    async with engine.begin() as conn:
        # Create custom indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_user_email_active ON users (email, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_user_created_at ON users (created_at)",
            "CREATE INDEX IF NOT EXISTS idx_product_category_active ON products (category_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_product_price ON products (price)",
            "CREATE INDEX IF NOT EXISTS idx_product_created_at ON products (created_at)",
            "CREATE INDEX IF NOT EXISTS idx_order_user_status ON orders (user_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_order_created_at ON orders (created_at)",
            "CREATE INDEX IF NOT EXISTS idx_order_status ON orders (status)",
            "CREATE INDEX IF NOT EXISTS idx_order_item_order ON order_items (order_id)",
            "CREATE INDEX IF NOT EXISTS idx_order_item_product ON order_items (product_id)"
        ]
        
        for index_sql in indexes:
            try:
                await conn.execute(text(index_sql))
            except Exception as e:
                print(f"Could not create index: {e}")

async def test_query_performance(query_name: str, query_func, *args, **kwargs):
    """Test query performance"""
    global query_count
    query_count = 0
    
    start_time = time.perf_counter()
    result = await query_func(*args, **kwargs)
    end_time = time.perf_counter()
    
    return {
        "query": query_name,
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
        "result_count": len(result) if hasattr(result, '__len__') else 1
    }

async def query_users_by_email_and_status(session):
    """Query users by email and active status"""
    result = await session.execute(
        select(User).where(
            and_(
                User.email.like("%user1%"),
                User.is_active == True
            )
        ).limit(100)
    )
    return result.scalars().all()

async def query_products_by_category_and_price(session):
    """Query products by category and price range"""
    result = await session.execute(
        select(Product).where(
            and_(
                Product.category_id == 1,
                Product.price.between(100, 500),
                Product.is_active == True
            )
        ).limit(100)
    )
    return result.scalars().all()

async def query_orders_by_user_and_status(session):
    """Query orders by user and status"""
    result = await session.execute(
        select(Order).where(
            and_(
                Order.user_id == 1000,
                Order.status == "completed"
            )
        ).limit(100)
    )
    return result.scalars().all()

async def query_orders_by_date_range(session):
    """Query orders by date range"""
    result = await session.execute(
        select(Order).where(
            and_(
                Order.created_at >= text("NOW() - INTERVAL '30 days'"),
                Order.created_at <= text("NOW()")
            )
        ).limit(100)
    )
    return result.scalars().all()

async def query_products_with_joins(session):
    """Query products with category joins"""
    result = await session.execute(
        select(Product, Category).join(Category).where(
            and_(
                Product.is_active == True,
                Category.name == "Electronics"
            )
        ).limit(100)
    )
    return result.all()

async def query_order_items_with_aggregation(session):
    """Query order items with aggregation"""
    result = await session.execute(
        select(
            OrderItem.order_id,
            func.count(OrderItem.id).label('item_count'),
            func.sum(OrderItem.total_price).label('total_amount')
        ).group_by(OrderItem.order_id).having(
            func.count(OrderItem.id) > 2
        ).limit(100)
    )
    return result.all()

async def run_performance_tests():
    """Run all performance tests"""
    print("Running Index Performance Tests...")
    print("=" * 80)
    
    test_queries = [
        ("Users by email and status", query_users_by_email_and_status),
        ("Products by category and price", query_products_by_category_and_price),
        ("Orders by user and status", query_orders_by_user_and_status),
        ("Orders by date range", query_orders_by_date_range),
        ("Products with category joins", query_products_with_joins),
        ("Order items aggregation", query_order_items_with_aggregation),
    ]
    
    results = []
    
    # Test without indexes
    print("Testing WITHOUT custom indexes...")
    print("-" * 80)
    print(f"{'Query':<30} {'Queries':<8} {'Time (ms)':<10} {'Results':<8}")
    print("-" * 80)
    
    async with AsyncSessionLocal() as session:
        for query_name, query_func in test_queries:
            result = await test_query_performance(query_name, query_func, session)
            results.append({**result, "indexed": False})
            print(f"{result['query']:<30} {result['queries']:<8} {result['time_ms']:<10} {result['result_count']:<8}")
    
    # Create indexes
    print("\nCreating custom indexes...")
    await create_indexes()
    
    # Test with indexes
    print("\nTesting WITH custom indexes...")
    print("-" * 80)
    print(f"{'Query':<30} {'Queries':<8} {'Time (ms)':<10} {'Results':<8}")
    print("-" * 80)
    
    async with AsyncSessionLocal() as session:
        for query_name, query_func in test_queries:
            result = await test_query_performance(query_name, query_func, session)
            results.append({**result, "indexed": True})
            print(f"{result['query']:<30} {result['queries']:<8} {result['time_ms']:<10} {result['result_count']:<8}")
    
    return results

async def analyze_results(results):
    """Analyze and display results"""
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)
    
    # Group results by query
    query_groups = {}
    for result in results:
        query = result['query']
        if query not in query_groups:
            query_groups[query] = {}
        query_groups[query][result['indexed']] = result
    
    print(f"{'Query':<30} {'Without Index':<15} {'With Index':<15} {'Improvement':<12}")
    print("-" * 80)
    
    for query, data in query_groups.items():
        without = data.get(False, {})
        with_index = data.get(True, {})
        
        without_time = without.get('time_ms', 0)
        with_time = with_index.get('time_ms', 0)
        
        if without_time > 0 and with_time > 0:
            improvement = round((without_time - with_time) / without_time * 100, 1)
        else:
            improvement = 0
        
        print(f"{query:<30} {without_time:<15} {with_time:<15} {improvement}%")

async def main():
    """Run the indexing benchmark"""
    print("Setting up test data...")
    await setup_data()
    
    # Run performance tests
    results = await run_performance_tests()
    
    # Analyze results
    await analyze_results(results)
    
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print("• Indexes significantly improve query performance")
    print("• Composite indexes are most effective for multi-column WHERE clauses")
    print("• Indexes on foreign keys improve JOIN performance")
    print("• Date range queries benefit greatly from date column indexes")
    print("• Consider index maintenance overhead for write operations")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
