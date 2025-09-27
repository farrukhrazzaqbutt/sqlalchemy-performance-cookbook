#!/usr/bin/env python3
"""
SQLAlchemy Performance Cookbook: Bulk Operations

This script demonstrates the performance difference between
row-by-row inserts vs bulk operations for large datasets.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import insert, text
from sqlalchemy.event import listen
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.db import Base
from app.models import Category, Order, OrderItem, Product, User

# Database URL - use SQLite if PostgreSQL is not available
DATABASE_URL = os.getenv(
    "DATABASE_URL", "sqlite+aiosqlite:///./bulk_operations_test.db"
)

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


async def setup_base_data():
    """Setup base data (categories and users)"""
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

        # Create some base users
        users = []
        for i in range(100):
            users.append(
                User(
                    email=f"base_user{i:03d}@example.com",
                    username=f"base_user{i:03d}",
                    hashed_password="hashed_password",
                    full_name=f"Base User {i}",
                    is_active=True,
                )
            )
        session.add_all(users)
        await session.commit()


async def row_by_row_inserts(record_count: int = 1000):
    """Insert records one by one"""
    global query_count
    query_count = 0

    start_time = time.perf_counter()

    async with AsyncSessionLocal() as session:
        for i in range(record_count):
            product = Product(
                name=f"Product {i:06d}",
                description=f"Description for product {i}",
                price=10.0 + (i % 1000),
                stock_quantity=100,
                category_id=(i % 3) + 1,
                is_active=True,
            )
            session.add(product)

            # Commit every 100 records to avoid memory issues
            if (i + 1) % 100 == 0:
                await session.commit()

    end_time = time.perf_counter()

    return {
        "approach": "Row-by-row inserts",
        "records": record_count,
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
    }


async def bulk_insert_objects(record_count: int = 1000):
    """Insert records using bulk_add_objects"""
    global query_count
    query_count = 0

    start_time = time.perf_counter()

    # Prepare all objects first
    products = []
    for i in range(record_count):
        products.append(
            Product(
                name=f"Product {i:06d}",
                description=f"Description for product {i}",
                price=10.0 + (i % 1000),
                stock_quantity=100,
                category_id=(i % 3) + 1,
                is_active=True,
            )
        )

    async with AsyncSessionLocal() as session:
        session.add_all(products)
        await session.commit()

    end_time = time.perf_counter()

    return {
        "approach": "Bulk add_all()",
        "records": record_count,
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
    }


async def bulk_insert_values(record_count: int = 1000):
    """Insert records using bulk_insert_mappings"""
    global query_count
    query_count = 0

    start_time = time.perf_counter()

    # Prepare data as dictionaries
    products_data = []
    for i in range(record_count):
        products_data.append(
            {
                "name": f"Product {i:06d}",
                "description": f"Description for product {i}",
                "price": 10.0 + (i % 1000),
                "stock_quantity": 100,
                "category_id": (i % 3) + 1,
                "is_active": True,
            }
        )

    async with AsyncSessionLocal() as session:
        await session.execute(insert(Product), products_data)
        await session.commit()

    end_time = time.perf_counter()

    return {
        "approach": "Bulk insert values",
        "records": record_count,
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
    }


async def bulk_insert_raw_sql(record_count: int = 1000):
    """Insert records using raw SQL with VALUES"""
    global query_count
    query_count = 0

    start_time = time.perf_counter()

    # Prepare data for raw SQL
    values_data = []
    for i in range(record_count):
        values_data.append(
            f"('Product {i:06d}', 'Description for product {i}', {10.0 + (i % 1000)}, 100, {(i % 3) + 1}, true)"
        )

    # Split into chunks to avoid SQL size limits
    chunk_size = 1000
    async with AsyncSessionLocal() as session:
        for i in range(0, len(values_data), chunk_size):
            chunk = values_data[i : i + chunk_size]
            values_sql = f"""
                INSERT INTO products (name, description, price, stock_quantity, category_id, is_active)
                VALUES {', '.join(chunk)}
            """
            await session.execute(text(values_sql))
        await session.commit()

    end_time = time.perf_counter()

    return {
        "approach": "Raw SQL VALUES",
        "records": record_count,
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
    }


async def test_bulk_update():
    """Test bulk update operations"""
    global query_count
    query_count = 0

    start_time = time.perf_counter()

    async with AsyncSessionLocal() as session:
        # Update all products with price > 500
        await session.execute(
            text(
                "UPDATE products SET stock_quantity = stock_quantity + 10 WHERE price > 500"
            )
        )
        await session.commit()

    end_time = time.perf_counter()

    return {
        "approach": "Bulk UPDATE",
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
    }


async def test_bulk_delete():
    """Test bulk delete operations"""
    global query_count
    query_count = 0

    start_time = time.perf_counter()

    async with AsyncSessionLocal() as session:
        # Delete products with price < 50
        await session.execute(text("DELETE FROM products WHERE price < 50"))
        await session.commit()

    end_time = time.perf_counter()

    return {
        "approach": "Bulk DELETE",
        "queries": query_count,
        "time_ms": round((end_time - start_time) * 1000, 2),
    }


async def run_insert_tests():
    """Run insert performance tests"""
    print("Testing Bulk Insert Performance...")
    print("=" * 80)

    test_sizes = [100, 1000, 5000]
    all_results = []

    for size in test_sizes:
        print(f"\nTesting with {size} records:")
        print("-" * 50)
        print(f"{'Approach':<20} {'Queries':<8} {'Time (ms)':<10} {'Records/sec':<12}")
        print("-" * 50)

        # Clear products table
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM products"))

        # Test each approach
        approaches = [
            row_by_row_inserts,
            bulk_insert_objects,
            bulk_insert_values,
            bulk_insert_raw_sql,
        ]

        for approach_func in approaches:
            result = await approach_func(size)
            result["test_size"] = size
            all_results.append(result)

            records_per_sec = (
                round(size / (result["time_ms"] / 1000), 2)
                if result["time_ms"] > 0
                else 0
            )
            print(
                f"{result['approach']:<20} {result['queries']:<8} {result['time_ms']:<10} {records_per_sec:<12}"
            )

    return all_results


async def run_update_delete_tests():
    """Run update and delete performance tests"""
    print("\nTesting Bulk Update/Delete Performance...")
    print("=" * 80)

    results = []

    # Test bulk update
    result = await test_bulk_update()
    results.append(result)
    print(f"{result['approach']:<20} {result['queries']:<8} {result['time_ms']:<10}")

    # Test bulk delete
    result = await test_bulk_delete()
    results.append(result)
    print(f"{result['approach']:<20} {result['queries']:<8} {result['time_ms']:<10}")

    return results


async def analyze_results(results):
    """Analyze and display results"""
    print("\n" + "=" * 80)
    print("PERFORMANCE ANALYSIS")
    print("=" * 80)

    # Group by test size
    by_size = {}
    for result in results:
        size = result.get("test_size", 0)
        if size not in by_size:
            by_size[size] = []
        by_size[size].append(result)

    for size, size_results in by_size.items():
        if size == 0:  # Skip non-insert tests
            continue

        print(f"\nResults for {size} records:")
        print("-" * 40)

        # Find fastest approach
        fastest = min(size_results, key=lambda x: x["time_ms"])
        slowest = max(size_results, key=lambda x: x["time_ms"])

        print(f"Fastest: {fastest['approach']} ({fastest['time_ms']}ms)")
        print(f"Slowest: {slowest['approach']} ({slowest['time_ms']}ms)")

        if slowest["time_ms"] > 0:
            improvement = round(
                (slowest["time_ms"] - fastest["time_ms"]) / slowest["time_ms"] * 100, 1
            )
            print(f"Improvement: {improvement}%")


async def main():
    """Run the bulk operations benchmark"""
    print("Setting up base data...")
    await setup_base_data()

    # Run insert tests
    insert_results = await run_insert_tests()

    # Run update/delete tests
    update_delete_results = await run_update_delete_tests()

    # Analyze results
    all_results = insert_results + update_delete_results
    await analyze_results(all_results)

    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print("• Row-by-row inserts are slowest due to individual commits")
    print("• Bulk operations (add_all, insert values) are much faster")
    print("• Raw SQL VALUES is fastest for very large datasets")
    print("• Bulk updates and deletes are much faster than individual operations")
    print("• Consider batch sizes to balance memory usage and performance")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
