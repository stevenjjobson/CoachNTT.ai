#!/usr/bin/env python3
"""
Simple test runner for the Cognitive Coding Partner safety tests.
"""
import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run the test suite."""
    print("🧪 Running Cognitive Coding Partner Safety Tests...")
    print("-" * 60)
    
    # Get project root
    project_root = Path(__file__).parent
    
    # Run pytest with coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        f"--cov={project_root}/src",
        "--cov-report=term-missing",
        f"{project_root}/tests/unit/core"
    ]
    
    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)