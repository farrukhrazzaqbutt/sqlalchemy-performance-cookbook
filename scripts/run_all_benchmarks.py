#!/usr/bin/env python3
"""
Run all performance benchmarks and generate a comprehensive report
"""

import asyncio
import subprocess
import sys
from pathlib import Path

async def run_script(script_path: str, script_name: str):
    """Run a benchmark script and capture output"""
    print(f"\n{'='*60}")
    print(f"Running {script_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([
            sys.executable, script_path
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Error running {script_name}:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print(f"Timeout running {script_name}")
    except Exception as e:
        print(f"Exception running {script_name}: {e}")

async def main():
    """Run all benchmark scripts"""
    scripts_dir = Path(__file__).parent
    
    scripts = [
        ("n_plus_one_queries.py", "N+1 Query Problem"),
        ("pagination_comparison.py", "Pagination Performance"),
        ("indexing_performance.py", "Indexing Impact"),
        ("bulk_operations.py", "Bulk Operations")
    ]
    
    print("SQLAlchemy Performance Cookbook - Comprehensive Benchmark Report")
    print("="*80)
    
    for script_file, script_name in scripts:
        script_path = scripts_dir / script_file
        if script_path.exists():
            await run_script(str(script_path), script_name)
        else:
            print(f"Script not found: {script_path}")
    
    print(f"\n{'='*80}")
    print("All benchmarks completed!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
