#!/usr/bin/env python3
"""
Run all performance benchmarks and generate a comprehensive report
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path


def cleanup_db_files():
    """Clean up database files created by performance scripts"""
    db_files = [
        "n_plus_one_test.db",
        "pagination_test.db",
        "indexing_test.db",
        "bulk_operations_test.db",
        "performance_test.db",
    ]

    for db_file in db_files:
        db_path = Path(db_file)
        if db_path.exists():
            try:
                db_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors


async def run_script(script_path: str, script_name: str):
    """Run a benchmark script and capture output"""
    print(f"\n{'='*60}")
    print(f"Running {script_name}")
    print(f"{'='*60}")

    try:
        # Set PYTHONPATH to include the project root
        project_root = Path(__file__).parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )

        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Error running {script_name}:")
            print(result.stderr)

    except subprocess.TimeoutExpired:
        print(f"Timeout running {script_name}")
    except Exception as e:
        print(f"Exception running {script_name}: {e}")
    finally:
        # Clean up database files created by the script
        cleanup_db_files()


async def main():
    """Run all benchmark scripts"""
    scripts_dir = Path(__file__).parent

    scripts = [
        ("n_plus_one_queries.py", "N+1 Query Problem"),
        ("pagination_comparison.py", "Pagination Performance"),
        ("indexing_performance.py", "Indexing Impact"),
        ("bulk_operations.py", "Bulk Operations"),
    ]

    print("SQLAlchemy Performance Cookbook - Comprehensive Benchmark Report")
    print("=" * 80)

    for script_file, script_name in scripts:
        script_path = scripts_dir / script_file
        if script_path.exists():
            await run_script(str(script_path), script_name)
        else:
            print(f"Script not found: {script_path}")

    print(f"\n{'='*80}")
    print("All benchmarks completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
