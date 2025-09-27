#!/usr/bin/env python3
"""
SQLAlchemy Performance Cookbook: Pagination Strategies

This script compares OFFSET/LIMIT vs Keyset (Seek) pagination performance
with different data sizes and page positions.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import and_, desc, select, text
from sqlalchemy.event import listen
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.models import Category, Order, OrderItem, Product, User

# Database URL - use SQLite if PostgreSQL is not available
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./pagination_test.db")

# Create engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Query counter
query_count = 0


def count_queries(conn, cursor, statement, parameters, context, executemany):
    global query_count
    query_count += 1


# Listen to queries
listen(engine.sync_engine, "before_cursor_execute", count_queries)


async def setup_data():
    """Setup test data with varying sizes"""
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

        # Create products (10,000 records)
        products = []
        for i in range(10000):
            products.append(
                Product(
                    name=f"Product {i:05d}",
                    description=f"Description for product {i}",
                    price=10.0 + (i % 1000),
                    stock_quantity=100,
                    category_id=(i % 3) + 1,
                    is_active=True,
                )
            )
        session.add_all(products)
        await session.commit()

        # Create users (1,000 records)
        users = []
        for i in range(1000):
            users.append(
                User(
                    email=f"user{i:04d}@example.com",
                    username=f"user{i:04d}",
                    hashed_password="hashed_password",
                    full_name=f"User {i}",
                    is_active=True,
                )
            )
        session.add_all(users)
        await session.commit()

        # Create orders (5,000 records)
        orders = []
        for i in range(5000):
            orders.append(
                Order(
                    user_id=(i % 1000) + 1,
                    total_amount=10.0 + (i % 500),
                    status="completed" if i % 10 != 0 else "pending",
                    shipping_address=f"Address for order {i}",
                    created_at=(
                        Base.metadata.tables["orders"].c.created_at.default.arg()
                        if hasattr(
                            Base.metadata.tables["orders"].c.created_at.default, "arg"
                        )
                        else None
                    ),
                )
            )
        session.add_all(orders)
        await session.commit()


async def offset_limit_pagination(page: int, page_size: int = 20):
    """Traditional OFFSET/LIMIT pagination"""
    global query_count
    query_count = 0

    start_time = time.perf_counter()

    async with AsyncSessionLocal() as session:
        # Count total records
        count_result = await session.execute(
            select(text("COUNT(*)")).select_from(Order)
        )
        total_count = count_result.scalar()

        # Get page data
        offset = (page - 1) * page_size
        result = await session.execute(
            select(Order)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        orders = result.scalars().all()

    end_time = time.perf_counter()

    return {
        "approach": "OFFSET/LIMIT",
        "page": page,
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
        "records_returned": len(orders),
        "total_count": total_count,
    }


async def keyset_pagination(last_id: int = None, page_size: int = 20):
    """Keyset (Seek) pagination using cursor"""
    global query_count
    query_count = 0

    start_time = time.perf_counter()

    async with AsyncSessionLocal() as session:
        # Build query with cursor condition
        query = select(Order).order_by(Order.id.desc())

        if last_id:
            query = query.where(Order.id < last_id)

        query = query.limit(
            page_size + 1
        )  # Get one extra to check if there's a next page

        result = await session.execute(query)
        orders = result.scalars().all()

        # Check if there are more records
        has_next = len(orders) > page_size
        if has_next:
            orders = orders[:page_size]  # Remove the extra record

        # Get next cursor
        next_cursor = orders[-1].id if orders and has_next else None

    end_time = time.perf_counter()

    return {
        "approach": "Keyset (Seek)",
        "cursor": last_id,
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
        "records_returned": len(orders),
        "has_next": has_next,
        "next_cursor": next_cursor,
    }


async def test_pagination_performance():
    """Test pagination performance at different positions"""
    print("Testing Pagination Performance...")
    print("=" * 80)

    results = []

    # Test different page positions
    test_pages = [1, 10, 50, 100, 200]

    print(
        f"{'Approach':<15} {'Page/Cursor':<12} {'Queries':<8} {'Time (ms)':<10} {'Records':<8}"
    )
    print("-" * 80)

    # Test OFFSET/LIMIT
    for page in test_pages:
        result = await offset_limit_pagination(page)
        results.append(result)
        print(
            f"{result['approach']:<15} {result['page']:<12} {result['queries']:<8} {result['time_ms']:<10} {result['records_returned']:<8}"
        )

    print()

    # Test Keyset pagination
    cursor = None
    for i, page in enumerate(test_pages):
        result = await keyset_pagination(cursor)
        results.append(result)
        print(
            f"{result['approach']:<15} {result['cursor'] or 'None':<12} {result['queries']:<8} {result['time_ms']:<10} {result['records_returned']:<8}"
        )
        cursor = result["next_cursor"]
        if not cursor:
            break

    return results


async def test_large_offset_performance():
    """Test performance with very large offsets"""
    print("\nTesting Large Offset Performance...")
    print("=" * 80)

    large_pages = [1000, 2000, 5000]

    print(
        f"{'Approach':<15} {'Page':<8} {'Queries':<8} {'Time (ms)':<10} {'Records':<8}"
    )
    print("-" * 80)

    for page in large_pages:
        result = await offset_limit_pagination(page)
        print(
            f"{result['approach']:<15} {result['page']:<8} {result['queries']:<8} {result['time_ms']:<10} {result['records_returned']:<8}"
        )


async def main():
    """Run the pagination benchmark"""
    print("Setting up test data...")
    await setup_data()

    # Run pagination tests
    results = await test_pagination_performance()

    # Test large offsets
    await test_large_offset_performance()

    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print("• OFFSET/LIMIT: Performance degrades with higher page numbers")
    print("• Keyset pagination: Consistent performance regardless of position")
    print("• Keyset is better for deep pagination and real-time feeds")
    print("• OFFSET/LIMIT is simpler but has performance limitations")
    print("• Keyset requires ordered, unique columns (usually primary key)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
