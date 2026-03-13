#!/usr/bin/env python3
"""
SQLite Integration Verification Script

Tests all API endpoints using SQLite database (no PostgreSQL required).
This script starts a temporary FastAPI server and runs HTTP requests against it.

REQUIREMENTS:
- Python 3.11+ with SQLite support
- All backend dependencies installed

USAGE:
    python scripts/verify_sqlite_integration.py
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


API_BASE_URL = "http://localhost:8765"
VERBOSE = True
SERVER_PROCESS = None
TEST_DB_PATH = Path(__file__).parent.parent / "test_integration.db"


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(test_name: str, passed: bool, details: str = "") -> None:
    """Print test result."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"  {status}: {test_name}")
    if details and VERBOSE:
        print(f"    {details}")


def start_server() -> subprocess.Popen:
    """Start the FastAPI server with SQLite database."""
    print_section("Starting Server")

    # Set environment for SQLite
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
    env["ENVIRONMENT"] = "development"
    env["DEBUG"] = "true"

    # Remove old test database
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    # Run migrations first
    print("  Running database migrations...")
    migrate_result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).parent.parent,
        env=env,
        capture_output=True,
        text=True
    )

    if migrate_result.returncode != 0:
        print(f"  ✗ Migration failed: {migrate_result.stderr}")
        return None

    print("  ✓ Migrations complete")

    # Create test user
    print("  Creating test user...")
    create_user_script = Path(__file__).parent / "create_test_user.py"
    create_user_result = subprocess.run(
        [sys.executable, str(create_user_script), str(TEST_DB_PATH)],
        cwd=Path(__file__).parent.parent,
        env=env,
        capture_output=True,
        text=True
    )
    if create_user_result.returncode == 0:
        print(f"  ✓ {create_user_result.stdout.strip()}")
    else:
        print(f"  ! Warning: Could not create test user: {create_user_result.stderr}")

    # Start server
    print(f"  Starting server on {API_BASE_URL}...")
    server = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "localhost",
            "--port", "8765"
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent.parent
    )

    # Wait for server to start
    for _ in range(30):
        try:
            response = httpx.get(f"{API_BASE_URL}/api/v1/health", timeout=1.0)
            if response.status_code == 200:
                print("  ✓ Server is ready")
                return server
        except Exception:
            time.sleep(0.5)
        except KeyboardInterrupt:
            break

    print("  ✗ Server failed to start")
    server.terminate()
    return None


def stop_server(server: subprocess.Popen) -> None:
    """Stop the server and cleanup."""
    print_section("Cleanup")
    print("  Stopping server...")
    server.terminate()
    server.wait(timeout=5)

    # Remove test database
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
        print("  ✓ Test database removed")


async def verify_api() -> dict[str, Any]:
    """Verify all API endpoints."""
    results = {
        "passed": 0,
        "failed": 0,
        "errors": [],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health Check
        print_section("1. Health Check")
        try:
            response = await client.get(f"{API_BASE_URL}/api/v1/health")
            if response.status_code == 200:
                data = response.json()
                print_result("Health endpoint", True, f"Status: {data.get('status')}, Version: {data.get('version')}")
                results["passed"] += 1
            else:
                print_result("Health endpoint", False, f"Status: {response.status_code}")
                results["failed"] += 1
        except Exception as e:
            print_result("Health endpoint", False, str(e))
            results["failed"] += 1
            results["errors"].append(f"Health check: {e}")

        # 2. Projects API
        print_section("2. Projects API")
        project_id = None

        try:
            # List projects
            response = await client.get(f"{API_BASE_URL}/api/v1/projects")
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', len(data)) if isinstance(data, dict) else len(data)
                print_result("List projects", True, f"Found {total} projects")
                results["passed"] += 1
            else:
                print_result("List projects", False, f"Status: {response.status_code}")
                results["failed"] += 1

            # Create a project
            project_data = {
                "name": "Integration Test Project",
                "genre": "fiction"
            }
            response = await client.post(
                f"{API_BASE_URL}/api/v1/projects",
                json=project_data
            )
            if response.status_code in (200, 201):
                project = response.json()
                project_id = project.get("id")
                print_result("Create project", True, f"ID: {project_id}")
                results["passed"] += 1
            else:
                print_result("Create project", False, f"Status: {response.status_code}, {response.text}")
                results["failed"] += 1

            # Get project by ID
            if project_id:
                response = await client.get(f"{API_BASE_URL}/api/v1/projects/{project_id}")
                if response.status_code == 200:
                    print_result("Get project by ID", True)
                    results["passed"] += 1
                else:
                    print_result("Get project by ID", False, f"Status: {response.status_code}")
                    results["failed"] += 1

                # Update project
                update_data = {"genre": "fantasy"}
                response = await client.patch(
                    f"{API_BASE_URL}/api/v1/projects/{project_id}",
                    json=update_data
                )
                if response.status_code == 200:
                    print_result("Update project", True)
                    results["passed"] += 1
                else:
                    print_result("Update project", False, f"Status: {response.status_code}")
                    results["failed"] += 1

        except Exception as e:
            print_result("Projects API", False, str(e))
            results["failed"] += 1
            results["errors"].append(f"Projects API: {e}")

        # 3. Characters API
        print_section("3. Characters API")
        character_id = None

        try:
            if project_id:
                # List characters
                response = await client.get(f"{API_BASE_URL}/api/v1/characters/project/{project_id}")
                if response.status_code == 200:
                    characters = response.json()
                    print_result("List characters", True, f"Found {len(characters)} characters")
                    results["passed"] += 1
                else:
                    print_result("List characters", False, f"Status: {response.status_code}")
                    results["failed"] += 1

                # Create a character
                character_data = {
                    "project_id": str(project_id),
                    "name": "Test Character",
                    "role": "protagonist",
                    "profile": {
                        "personality": "Brave and curious",
                        "appearance": "Tall with dark hair"
                    }
                }
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/characters",
                    json=character_data
                )
                if response.status_code in (200, 201):
                    character = response.json()
                    character_id = character.get("id")
                    print_result("Create character", True, f"ID: {character_id}")
                    results["passed"] += 1
                else:
                    print_result("Create character", False, f"Status: {response.status_code}, {response.text}")
                    results["failed"] += 1

                # Get character by ID
                if character_id:
                    response = await client.get(f"{API_BASE_URL}/api/v1/characters/{character_id}")
                    if response.status_code == 200:
                        print_result("Get character by ID", True)
                        results["passed"] += 1
                    else:
                        print_result("Get character by ID", False, f"Status: {response.status_code}")
                        results["failed"] += 1

        except Exception as e:
            print_result("Characters API", False, str(e))
            results["failed"] += 1
            results["errors"].append(f"Characters API: {e}")

        # 4. Chapters API
        print_section("4. Chapters API")
        chapter_id = None

        try:
            if project_id:
                # List chapters
                response = await client.get(f"{API_BASE_URL}/api/v1/chapters/project/{project_id}")
                if response.status_code == 200:
                    data = response.json()
                    chapters = data.get("items", data) if isinstance(data, dict) else data
                    print_result("List chapters", True, f"Found {len(chapters)} chapters")
                    results["passed"] += 1
                else:
                    print_result("List chapters", False, f"Status: {response.status_code}")
                    results["failed"] += 1

                # Create a chapter
                chapter_data = {
                    "project_id": str(project_id),
                    "chapter_number": 1,
                    "title": "Test Chapter",
                    "status": "draft"
                }
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/chapters",
                    json=chapter_data
                )
                if response.status_code in (200, 201):
                    chapter = response.json()
                    chapter_id = chapter.get("id")
                    print_result("Create chapter", True, f"ID: {chapter_id}")
                    results["passed"] += 1
                else:
                    print_result("Create chapter", False, f"Status: {response.status_code}, {response.text}")
                    results["failed"] += 1

        except Exception as e:
            print_result("Chapters API", False, str(e))
            results["failed"] += 1
            results["errors"].append(f"Chapters API: {e}")

        # 5. Scenes API
        print_section("5. Scenes API")
        scene_id = None

        try:
            if chapter_id:
                # List scenes
                response = await client.get(f"{API_BASE_URL}/api/v1/scenes/chapter/{chapter_id}")
                if response.status_code == 200:
                    scenes = response.json()
                    print_result("List scenes", True, f"Found {len(scenes)} scenes")
                    results["passed"] += 1
                else:
                    print_result("List scenes", False, f"Status: {response.status_code}")
                    results["failed"] += 1

                # Create a scene
                scene_data = {
                    "chapter_id": str(chapter_id),
                    "scene_order": 1,
                    "location": "Test Location",
                    "content": "Test scene content for API integration testing."
                }
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/scenes",
                    json=scene_data
                )
                if response.status_code in (200, 201):
                    scene = response.json()
                    scene_id = scene.get("id")
                    print_result("Create scene", True, f"ID: {scene_id}")
                    results["passed"] += 1
                else:
                    print_result("Create scene", False, f"Status: {response.status_code}, {response.text}")
                    results["failed"] += 1

        except Exception as e:
            print_result("Scenes API", False, str(e))
            results["failed"] += 1
            results["errors"].append(f"Scenes API: {e}")

        # 6. WorldSettings API
        print_section("6. WorldSettings API")
        setting_id = None

        try:
            if project_id:
                # List world settings
                response = await client.get(f"{API_BASE_URL}/api/v1/world-settings/project/{project_id}")
                if response.status_code == 200:
                    settings = response.json()
                    print_result("List world settings", True, f"Found {len(settings)} settings")
                    results["passed"] += 1
                else:
                    print_result("List world settings", False, f"Status: {response.status_code}")
                    results["failed"] += 1

                # Create a world setting
                setting_data = {
                    "project_id": str(project_id),
                    "name": "Test Location",
                    "category": "geography",
                    "content": "A test world setting for API integration testing."
                }
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/world-settings",
                    json=setting_data
                )
                if response.status_code in (200, 201):
                    setting = response.json()
                    setting_id = setting.get("id")
                    print_result("Create world setting", True, f"ID: {setting_id}")
                    results["passed"] += 1
                else:
                    print_result("Create world setting", False, f"Status: {response.status_code}, {response.text}")
                    results["failed"] += 1

        except Exception as e:
            print_result("WorldSettings API", False, str(e))
            results["failed"] += 1
            results["errors"].append(f"WorldSettings API: {e}")

        # Cleanup: Delete test project
        print_section("7. Cleanup")
        try:
            if project_id:
                response = await client.delete(f"{API_BASE_URL}/api/v1/projects/{project_id}")
                if response.status_code in (200, 204):
                    print_result("Delete test project", True)
                    results["passed"] += 1
                else:
                    print_result("Delete test project", False, f"Status: {response.status_code}")
                    results["failed"] += 1
        except Exception as e:
            print_result("Cleanup", False, str(e))
            results["failed"] += 1

    return results


async def main() -> int:
    """Main entry point."""
    print_section("AI Novel Agent - SQLite Integration Verification")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test Database: {TEST_DB_PATH}")
    print("Using SQLite for integration testing (no PostgreSQL required)")

    # Start server
    server = start_server()
    if not server:
        print("\n✗ Failed to start server")
        return 1

    try:
        # Run tests
        results = await verify_api()

        # Check server stderr for errors after tests
        if server.stderr:
            import select
            # Check if there's data to read without blocking
            if select.select([server.stderr], [], [], 0)[0]:
                stderr_output = server.stderr.read().decode(errors='replace')
                if stderr_output and 'ERROR' in stderr_output:
                    print(f"\n  Server errors detected:")
                    for line in stderr_output.split('\n'):
                        if 'ERROR' in line or 'Exception' in line or 'Traceback' in line:
                            print(f"    {line}")

        # Print summary
        print_section("Summary")
        total = results["passed"] + results["failed"]
        print(f"  Total tests: {total}")
        print(f"  Passed: {results['passed']}")
        print(f"  Failed: {results['failed']}")

        if results["errors"]:
            print("\n  Errors:")
            for error in results["errors"]:
                print(f"    - {error}")

        if results["failed"] > 0:
            print(f"\n  Some tests failed. Please check the logs above.")
            return 1
        else:
            print(f"\n  All tests passed! The API is working correctly.")
            return 0
    finally:
        # Always stop the server
        stop_server(server)


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user")
        sys.exit(130)
