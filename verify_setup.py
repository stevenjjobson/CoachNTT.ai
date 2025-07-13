#!/usr/bin/env python3
"""
Verify the CoachNTT.ai setup is working correctly.
Run this before starting the next session.
"""
import sys
import os
from pathlib import Path

def check_files_exist():
    """Check that key files exist."""
    print("📁 Checking key files...")
    required_files = [
        "CLAUDE.md",
        "SESSION_LOG.md",
        ".env",
        "docker-compose.yml",
        "src/core/abstraction/concrete_engine.py",
        "migrations/000_safety_foundation.sql",
        "tests/unit/core/abstraction/test_engine.py"
    ]
    
    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
            all_exist = False
    
    return all_exist

def check_python_imports():
    """Check that Python modules can be imported."""
    print("\n🐍 Checking Python imports...")
    try:
        # Add src to path
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        
        # Try imports
        from core.abstraction.concrete_engine import ConcreteAbstractionEngine
        from core.safety.models import Reference, ReferenceType
        from core.validation.validator import SafetyValidator
        
        print("  ✅ All core modules import successfully")
        return True
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_abstraction_engine():
    """Quick test of the abstraction engine."""
    print("\n🔧 Testing abstraction engine...")
    try:
        from core.abstraction.concrete_engine import ConcreteAbstractionEngine
        
        engine = ConcreteAbstractionEngine()
        test_content = "User 12345 has file at /home/user/data.txt"
        result = engine.abstract(test_content)
        
        print(f"  Input:  {test_content}")
        print(f"  Output: {result.abstracted_content}")
        print(f"  Safety Score: {result.validation.safety_score:.2f}")
        
        if result.is_safe:
            print("  ✅ Abstraction engine working correctly")
            return True
        else:
            print("  ❌ Abstraction failed safety validation")
            return False
            
    except Exception as e:
        print(f"  ❌ Error testing engine: {e}")
        return False

def check_docker_files():
    """Check Docker configuration."""
    print("\n🐳 Checking Docker setup...")
    docker_files = [
        "docker-compose.yml",
        "docker/dockerfiles/postgres.Dockerfile",
        "docker/dockerfiles/postgresql.conf",
        "scripts/start-dev.sh",
        "scripts/stop-dev.sh"
    ]
    
    all_exist = True
    for file in docker_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
            all_exist = False
    
    return all_exist

def main():
    """Run all verification checks."""
    print("🔍 Verifying CoachNTT.ai Setup")
    print("=" * 50)
    
    checks = [
        check_files_exist(),
        check_python_imports(),
        test_abstraction_engine(),
        check_docker_files()
    ]
    
    print("\n" + "=" * 50)
    if all(checks):
        print("✅ All checks passed! Ready for next session.")
        print("\nNext steps:")
        print("1. Start Docker: ./scripts/start-dev.sh")
        print("2. Run tests: ./run_tests.py")
        print("3. Commit your work: git add -A && git commit -m 'Phase 0.1 Complete'")
        return 0
    else:
        print("❌ Some checks failed. Please fix issues before continuing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())