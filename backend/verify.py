#!/usr/bin/env python3
"""Quick verification script for AI Novel Agent backend.

This script performs basic verification checks without requiring a database.
"""

import sys


def check_imports() -> bool:
    """Check that all core modules can be imported."""
    print("Checking imports...")
    try:
        from app.main import app
        from app.models import Base, Character, Project
        print("  ✓ All core imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def check_openapi() -> bool:
    """Check that OpenAPI schema can be generated."""
    print("Checking OpenAPI schema generation...")
    try:
        from app.main import app
        schema = app.openapi()
        if schema.get("openapi") and schema.get("info"):
            print(f"  ✓ OpenAPI {schema.get('openapi')} - {schema['info'].get('title')}")
            return True
        print("  ✗ Invalid OpenAPI schema")
        return False
    except Exception as e:
        print(f"  ✗ OpenAPI generation failed: {e}")
        return False


def check_routes() -> bool:
    """Check that API routes are registered."""
    print("Checking API routes...")
    try:
        from app.main import app
        routes = [route.path for route in app.routes]
        expected = ["/", "/api/v1/health", "/docs", "/openapi.json"]
        found = sum(1 for r in expected if r in routes)
        print(f"  ✓ {found}/{len(expected)} expected routes found")
        for r in expected:
            if r in routes:
                print(f"    - {r}")
        return found == len(expected)
    except Exception as e:
        print(f"  ✗ Route check failed: {e}")
        return False


def check_models_metadata() -> bool:
    """Check that SQLAlchemy models have metadata for Alembic."""
    print("Checking model metadata...")
    try:
        from app.models import Base

        tables = Base.metadata.tables.keys()
        table_names = sorted(tables)
        expected_tables = [
            "projects", "characters", "world_settings",
            "volumes", "chapters", "scenes",
            "memories", "suggestions", "snapshots", "dependencies",
            "agent_threads", "agent_messages", "agent_runs", "agent_operations",
            "agent_subtasks", "agent_thread_checkpoints",
        ]

        missing = set(expected_tables) - set(table_names)
        extra = set(table_names) - set(expected_tables)

        if missing or extra:
            if missing:
                print(f"  ✗ Missing tables: {missing}")
            if extra:
                print(f"  ! Extra tables: {extra}")
            return False

        print(f"  ✓ All {len(expected_tables)} model tables defined")
        return True
    except Exception as e:
        print(f"  ✗ Model metadata check failed: {e}")
        return False


def check_alembic() -> bool:
    """Check that Alembic migration exists."""
    print("Checking Alembic migration...")
    try:
        from pathlib import Path
        import re

        versions_dir = Path(__file__).parent / "alembic" / "versions"
        migration_files = list(versions_dir.glob("*.py"))
        migration_files = [f for f in migration_files if f.name != "__init__.py"]

        if not migration_files:
            print("  ✗ No migration files found")
            return False

        print(f"  ✓ Found {len(migration_files)} migration file(s)")
        for f in migration_files:
            # Extract revision info
            content = f.read_text()
            revision_match = re.search(r'revision: str = "([^"]+)"', content)
            if revision_match:
                print(f"    - {f.name}: revision {revision_match.group(1)}")
        return True
    except Exception as e:
        print(f"  ✗ Alembic check failed: {e}")
        return False


def main() -> int:
    """Run all verification checks."""
    print("=" * 60)
    print("AI Novel Agent - Backend Verification")
    print("=" * 60)

    results = {
        "Imports": check_imports(),
        "OpenAPI": check_openapi(),
        "Routes": check_routes(),
        "Models": check_models_metadata(),
        "Alembic": check_alembic(),
    }

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")

    all_passed = all(results.values())
    print("=" * 60)

    if all_passed:
        print("\n✓ All verification checks passed!")
        print("\nNext steps:")
        print("  1. Run tests: pytest")
        print("  2. Start dev server: uvicorn app.main:app --reload")
        return 0
    else:
        print("\n✗ Some verification checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
