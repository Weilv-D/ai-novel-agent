#!/usr/bin/env python3
"""
SQLite Integration Verification Script

Tests all API endpoints using SQLite database (no PostgreSQL required).
This script starts a temporary FastAPI server and runs HTTP requests against it using curl.

REQUIREMENTS:
- Python 3.11+ with SQLite support
- curl command-line tool
- All backend dependencies installed

USAGE:
    python scripts/verify_sqlite_integration.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


API_BASE_URL = "http://localhost:8765"
VERBOSE = True
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


def curl_request(method: str, url: str, data: dict[str, Any] | None = None) -> tuple[int, str]:
    """Make HTTP request using curl to avoid connection pool timeouts."""
    cmd = ["curl", "-s", "-w", "\n%{http_code}", url]
    if method == "POST":
        cmd.extend(["-X", "POST"])
        if data:
            cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(data)])
    elif method == "PATCH":
        cmd.extend(["-X", "PATCH"])
        if data:
            cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(data)])
    elif method == "DELETE":
        cmd.extend(["-X", "DELETE"])
    elif method == "GET":
        cmd.extend(["-X", "GET"])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    output = result.stdout.strip()
    # Last line is status code, rest is body
    lines = output.split('\n')
    if len(lines) >= 2:
        status_code = int(lines[-1])
        body = '\n'.join(lines[:-1])
        return status_code, body
    return -1, output


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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=Path(__file__).parent.parent
    )

    # Wait for server to start
    for attempt in range(30):
        try:
            status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/health")
            if status == 200:
                print("  ✓ Server is ready")
                return server
            else:
                print(f"  ! Attempt {attempt+1}: Health check returned {status}")
        except Exception as e:
            if attempt < 5:  # Only print first few attempts
                print(f"  ! Attempt {attempt+1}: {e}")
        time.sleep(0.5)

    print("  ✗ Server failed to start after 15 seconds")
    # Try to get stderr output
    try:
        server.stderr.flush()
        stderr_output = server.stderr.read().decode(errors='replace')
        if stderr_output:
            print(f"  Server stderr: {stderr_output[:500]}")
    except Exception:
        pass
    server.terminate()
    return None


def stop_server(server: subprocess.Popen) -> None:
    """Stop the server and cleanup."""
    print_section("Cleanup")
    print("  Stopping server...")
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()
    print("  ✓ Server stopped")

    # Remove test database
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
        print("  ✓ Test database removed")


def verify_api() -> dict[str, Any]:
    """Verify all API endpoints using curl."""
    results = {
        "passed": 0,
        "failed": 0,
        "errors": [],
    }

    # 1. Health Check
    print_section("1. Health Check")
    try:
        status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/health")
        if status == 200:
            data = json.loads(body)
            print_result("Health endpoint", True, f"Status: {data.get('status')}, Version: {data.get('version')}")
            results["passed"] += 1
        else:
            print_result("Health endpoint", False, f"Status: {status}")
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
        status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/projects")
        if status == 200:
            data = json.loads(body)
            total = data.get('total', len(data)) if isinstance(data, dict) else len(data)
            print_result("List projects", True, f"Found {total} projects")
            results["passed"] += 1
        else:
            print_result("List projects", False, f"Status: {status}")
            results["failed"] += 1

        # Create a project
        project_data = {
            "name": "Integration Test Project",
            "genre": "fiction"
        }
        status, body = curl_request("POST", f"{API_BASE_URL}/api/v1/projects", project_data)
        if status in (200, 201):
            project = json.loads(body)
            project_id = project.get("id")
            print_result("Create project", True, f"ID: {project_id}")
            results["passed"] += 1
        else:
            print_result("Create project", False, f"Status: {status}")
            results["failed"] += 1

        # Get project by ID
        if project_id:
            status, _ = curl_request("GET", f"{API_BASE_URL}/api/v1/projects/{project_id}")
            if status == 200:
                print_result("Get project by ID", True)
                results["passed"] += 1
            else:
                print_result("Get project by ID", False, f"Status: {status}")
                results["failed"] += 1

            # Update project
            update_data = {"genre": "fantasy"}
            status, _ = curl_request("PATCH", f"{API_BASE_URL}/api/v1/projects/{project_id}", update_data)
            if status == 200:
                print_result("Update project", True)
                results["passed"] += 1
            else:
                print_result("Update project", False, f"Status: {status}")
                results["failed"] += 1

    except Exception as e:
        print_result("Projects API", False, str(e))
        results["failed"] += 1
        results["errors"].append(f"Projects API: {e}")

    # 3. Volumes API
    print_section("3. Volumes API")
    volume_id = None

    try:
        if project_id:
            # List volumes
            status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/volumes/project/{project_id}")
            if status == 200:
                volumes = json.loads(body)
                print_result("List volumes", True, f"Found {len(volumes)} volumes")
                results["passed"] += 1
            else:
                print_result("List volumes", False, f"Status: {status}")
                results["failed"] += 1

            # Create a volume
            volume_data = {
                "project_id": str(project_id),
                "volume_number": 1,
                "title": "Test Volume"
            }
            status, body = curl_request("POST", f"{API_BASE_URL}/api/v1/volumes", volume_data)
            if status in (200, 201):
                volume = json.loads(body)
                volume_id = volume.get("id")
                print_result("Create volume", True, f"ID: {volume_id}")
                results["passed"] += 1
            else:
                print_result("Create volume", False, f"Status: {status}, Body: {body[:200]}")
                results["failed"] += 1

            # Get volume by ID
            if volume_id:
                status, _ = curl_request("GET", f"{API_BASE_URL}/api/v1/volumes/{volume_id}")
                if status == 200:
                    print_result("Get volume by ID", True)
                    results["passed"] += 1
                else:
                    print_result("Get volume by ID", False, f"Status: {status}")
                    results["failed"] += 1

                # Update volume
                update_data = {"title": "Updated Test Volume"}
                status, _ = curl_request("PATCH", f"{API_BASE_URL}/api/v1/volumes/{volume_id}", update_data)
                if status == 200:
                    print_result("Update volume", True)
                    results["passed"] += 1
                else:
                    print_result("Update volume", False, f"Status: {status}")
                    results["failed"] += 1

                # Delete volume
                status, _ = curl_request("DELETE", f"{API_BASE_URL}/api/v1/volumes/{volume_id}")
                if status in (200, 204):
                    print_result("Delete volume", True)
                    results["passed"] += 1
                else:
                    print_result("Delete volume", False, f"Status: {status}")
                    results["failed"] += 1

    except Exception as e:
        print_result("Volumes API", False, str(e))
        results["failed"] += 1
        results["errors"].append(f"Volumes API: {e}")

    # 4. Characters API
    print_section("4. Characters API")
    character_id = None

    try:
        if project_id:
            # List characters
            status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/characters/project/{project_id}")
            if status == 200:
                characters = json.loads(body)
                print_result("List characters", True, f"Found {len(characters)} characters")
                results["passed"] += 1
            else:
                print_result("List characters", False, f"Status: {status}")
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
            status, body = curl_request("POST", f"{API_BASE_URL}/api/v1/characters", character_data)
            if status in (200, 201):
                character = json.loads(body)
                character_id = character.get("id")
                print_result("Create character", True, f"ID: {character_id}")
                results["passed"] += 1
            else:
                print_result("Create character", False, f"Status: {status}")
                results["failed"] += 1

            # Get character by ID
            if character_id:
                status, _ = curl_request("GET", f"{API_BASE_URL}/api/v1/characters/{character_id}")
                if status == 200:
                    print_result("Get character by ID", True)
                    results["passed"] += 1
                else:
                    print_result("Get character by ID", False, f"Status: {status}")
                    results["failed"] += 1

                # Update character
                update_data = {"role": "antagonist"}
                status, _ = curl_request("PATCH", f"{API_BASE_URL}/api/v1/characters/{character_id}", update_data)
                if status == 200:
                    print_result("Update character", True)
                    results["passed"] += 1
                else:
                    print_result("Update character", False, f"Status: {status}")
                    results["failed"] += 1

                # Delete character
                status, _ = curl_request("DELETE", f"{API_BASE_URL}/api/v1/characters/{character_id}")
                if status in (200, 204):
                    print_result("Delete character", True)
                    results["passed"] += 1
                else:
                    print_result("Delete character", False, f"Status: {status}")
                    results["failed"] += 1

    except Exception as e:
        print_result("Characters API", False, str(e))
        results["failed"] += 1
        results["errors"].append(f"Characters API: {e}")

    # 5. Chapters API
    print_section("5. Chapters API")
    crud_chapter_id = None  # For CRUD tests (will be deleted)
    scene_chapter_id = None  # For scene tests (will be kept)

    try:
        if project_id:
            # List chapters
            status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/chapters/project/{project_id}")
            if status == 200:
                data = json.loads(body)
                chapters = data.get("items", data) if isinstance(data, dict) else data
                print_result("List chapters", True, f"Found {len(chapters)} chapters")
                results["passed"] += 1
            else:
                print_result("List chapters", False, f"Status: {status}")
                results["failed"] += 1

            # Create a chapter for scene tests (kept for later use)
            chapter_data = {
                "project_id": str(project_id),
                "chapter_number": 1,
                "title": "Test Chapter for Scenes",
                "status": "draft"
            }
            status, body = curl_request("POST", f"{API_BASE_URL}/api/v1/chapters", chapter_data)
            if status in (200, 201):
                chapter = json.loads(body)
                scene_chapter_id = chapter.get("id")
                print_result("Create chapter (for scenes)", True, f"ID: {scene_chapter_id}")
                results["passed"] += 1
            else:
                print_result("Create chapter (for scenes)", False, f"Status: {status}")
                results["failed"] += 1

            # Create a chapter for CRUD tests (will be deleted)
            chapter_data = {
                "project_id": str(project_id),
                "chapter_number": 2,
                "title": "Test Chapter for CRUD",
                "status": "draft"
            }
            status, body = curl_request("POST", f"{API_BASE_URL}/api/v1/chapters", chapter_data)
            if status in (200, 201):
                chapter = json.loads(body)
                crud_chapter_id = chapter.get("id")
                print_result("Create chapter (for CRUD)", True, f"ID: {crud_chapter_id}")
                results["passed"] += 1
            else:
                print_result("Create chapter (for CRUD)", False, f"Status: {status}")
                results["failed"] += 1

            # Get chapter by ID
            if crud_chapter_id:
                status, _ = curl_request("GET", f"{API_BASE_URL}/api/v1/chapters/{crud_chapter_id}")
                if status == 200:
                    print_result("Get chapter by ID", True)
                    results["passed"] += 1
                else:
                    print_result("Get chapter by ID", False, f"Status: {status}")
                    results["failed"] += 1

                # Update chapter
                update_data = {"title": "Updated Test Chapter"}
                status, _ = curl_request("PATCH", f"{API_BASE_URL}/api/v1/chapters/{crud_chapter_id}", update_data)
                if status == 200:
                    print_result("Update chapter", True)
                    results["passed"] += 1
                else:
                    print_result("Update chapter", False, f"Status: {status}")
                    results["failed"] += 1

                # Delete chapter
                status, _ = curl_request("DELETE", f"{API_BASE_URL}/api/v1/chapters/{crud_chapter_id}")
                if status in (200, 204):
                    print_result("Delete chapter", True)
                    results["passed"] += 1
                else:
                    print_result("Delete chapter", False, f"Status: {status}")
                    results["failed"] += 1

    except Exception as e:
        print_result("Chapters API", False, str(e))
        results["failed"] += 1
        results["errors"].append(f"Chapters API: {e}")

    # 6. Scenes API
    print_section("6. Scenes API")
    scene_id = None

    try:
        if scene_chapter_id:
            # List scenes
            status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/scenes/chapter/{scene_chapter_id}")
            if status == 200:
                scenes = json.loads(body)
                print_result("List scenes", True, f"Found {len(scenes)} scenes")
                results["passed"] += 1
            else:
                print_result("List scenes", False, f"Status: {status}")
                results["failed"] += 1

            # Create a scene
            scene_data = {
                "chapter_id": str(scene_chapter_id),
                "scene_order": 1,
                "location": "Test Location",
                "content": "Test scene content for API integration testing."
            }
            status, body = curl_request("POST", f"{API_BASE_URL}/api/v1/scenes", scene_data)
            if status in (200, 201):
                scene = json.loads(body)
                scene_id = scene.get("id")
                print_result("Create scene", True, f"ID: {scene_id}")
                results["passed"] += 1
            else:
                print_result("Create scene", False, f"Status: {status}")
                results["failed"] += 1

            # Get scene by ID
            if scene_id:
                status, _ = curl_request("GET", f"{API_BASE_URL}/api/v1/scenes/{scene_id}")
                if status == 200:
                    print_result("Get scene by ID", True)
                    results["passed"] += 1
                else:
                    print_result("Get scene by ID", False, f"Status: {status}")
                    results["failed"] += 1

                # Update scene
                update_data = {"location": "Updated Location"}
                status, _ = curl_request("PATCH", f"{API_BASE_URL}/api/v1/scenes/{scene_id}", update_data)
                if status == 200:
                    print_result("Update scene", True)
                    results["passed"] += 1
                else:
                    print_result("Update scene", False, f"Status: {status}")
                    results["failed"] += 1

                # Delete scene
                status, _ = curl_request("DELETE", f"{API_BASE_URL}/api/v1/scenes/{scene_id}")
                if status in (200, 204):
                    print_result("Delete scene", True)
                    results["passed"] += 1
                else:
                    print_result("Delete scene", False, f"Status: {status}")
                    results["failed"] += 1

    except Exception as e:
        print_result("Scenes API", False, str(e))
        results["failed"] += 1
        results["errors"].append(f"Scenes API: {e}")

    # 7. WorldSettings API
    print_section("7. WorldSettings API")
    setting_id = None

    try:
        if project_id:
            # List world settings
            status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/world-settings/project/{project_id}")
            if status == 200:
                settings = json.loads(body)
                print_result("List world settings", True, f"Found {len(settings)} settings")
                results["passed"] += 1
            else:
                print_result("List world settings", False, f"Status: {status}")
                results["failed"] += 1

            # Create a world setting
            setting_data = {
                "project_id": str(project_id),
                "name": "Test Location",
                "category": "geography",
                "content": "A test world setting for API integration testing."
            }
            status, body = curl_request("POST", f"{API_BASE_URL}/api/v1/world-settings", setting_data)
            if status in (200, 201):
                setting = json.loads(body)
                setting_id = setting.get("id")
                print_result("Create world setting", True, f"ID: {setting_id}")
                results["passed"] += 1
            else:
                print_result("Create world setting", False, f"Status: {status}")
                results["failed"] += 1

            # Get world setting by ID
            if setting_id:
                status, _ = curl_request("GET", f"{API_BASE_URL}/api/v1/world-settings/{setting_id}")
                if status == 200:
                    print_result("Get world setting by ID", True)
                    results["passed"] += 1
                else:
                    print_result("Get world setting by ID", False, f"Status: {status}")
                    results["failed"] += 1

                # Update world setting
                update_data = {"name": "Updated Test Location"}
                status, _ = curl_request("PATCH", f"{API_BASE_URL}/api/v1/world-settings/{setting_id}", update_data)
                if status == 200:
                    print_result("Update world setting", True)
                    results["passed"] += 1
                else:
                    print_result("Update world setting", False, f"Status: {status}")
                    results["failed"] += 1

                # Delete world setting
                status, _ = curl_request("DELETE", f"{API_BASE_URL}/api/v1/world-settings/{setting_id}")
                if status in (200, 204):
                    print_result("Delete world setting", True)
                    results["passed"] += 1
                else:
                    print_result("Delete world setting", False, f"Status: {status}")
                    results["failed"] += 1

    except Exception as e:
        print_result("WorldSettings API", False, str(e))
        results["failed"] += 1
        results["errors"].append(f"WorldSettings API: {e}")

    # 8. Memories API
    print_section("8. Memories API")
    memory_id = None

    try:
        if project_id:
            # List memories (uses query parameter, not path parameter)
            status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/memories?project_id={project_id}")
            if status == 200:
                memories = json.loads(body)
                print_result("List memories", True, f"Found {len(memories)} memories")
                results["passed"] += 1
            else:
                print_result("List memories", False, f"Status: {status}")
                results["failed"] += 1

            # Create a memory (use correct schema: memory_type, content, project_id)
            memory_data = {
                "project_id": str(project_id),
                "memory_type": "fact",
                "content": "The hero possesses a magical amulet that glows in darkness."
            }
            status, body = curl_request("POST", f"{API_BASE_URL}/api/v1/memories", memory_data)
            if status in (200, 201):
                memory = json.loads(body)
                memory_id = memory.get("id")
                print_result("Create memory", True, f"ID: {memory_id}")
                results["passed"] += 1
            else:
                print_result("Create memory", False, f"Status: {status}, Body: {body[:200]}")
                results["failed"] += 1

            # Get memory by ID
            if memory_id:
                status, _ = curl_request("GET", f"{API_BASE_URL}/api/v1/memories/{memory_id}")
                if status == 200:
                    print_result("Get memory by ID", True)
                    results["passed"] += 1
                else:
                    print_result("Get memory by ID", False, f"Status: {status}")
                    results["failed"] += 1

                # Update memory
                update_data = {"content": "The hero possesses a magical amulet that glows in darkness and pulses when danger is near."}
                status, _ = curl_request("PATCH", f"{API_BASE_URL}/api/v1/memories/{memory_id}", update_data)
                if status == 200:
                    print_result("Update memory", True)
                    results["passed"] += 1
                else:
                    print_result("Update memory", False, f"Status: {status}")
                    results["failed"] += 1

                # Delete memory
                status, _ = curl_request("DELETE", f"{API_BASE_URL}/api/v1/memories/{memory_id}")
                if status in (200, 204):
                    print_result("Delete memory", True)
                    results["passed"] += 1
                else:
                    print_result("Delete memory", False, f"Status: {status}")
                    results["failed"] += 1

    except Exception as e:
        print_result("Memories API", False, str(e))
        results["failed"] += 1
        results["errors"].append(f"Memories API: {e}")

    # 9. Snapshots API
    print_section("9. Snapshots API")
    snapshot_id = None

    try:
        if project_id:
            # List snapshots
            status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/snapshots?project_id={project_id}")
            if status == 200:
                snapshots = json.loads(body)
                print_result("List snapshots", True, f"Found {len(snapshots)} snapshots")
                results["passed"] += 1
            else:
                print_result("List snapshots", False, f"Status: {status}")
                results["failed"] += 1

            # Create a snapshot
            snapshot_data = {
                "project_id": str(project_id),
                "target_type": "project",
                "target_id": str(project_id),
                "data": {"name": "Test Project Snapshot", "genre": "Fantasy"}
            }
            status, body = curl_request("POST", f"{API_BASE_URL}/api/v1/snapshots", snapshot_data)
            if status in (200, 201):
                snapshot = json.loads(body)
                snapshot_id = snapshot.get("id")
                print_result("Create snapshot", True, f"ID: {snapshot_id}")
                results["passed"] += 1
            else:
                print_result("Create snapshot", False, f"Status: {status}")
                results["failed"] += 1

            # Get snapshot by ID
            if snapshot_id:
                status, _ = curl_request("GET", f"{API_BASE_URL}/api/v1/snapshots/{snapshot_id}")
                if status == 200:
                    print_result("Get snapshot by ID", True)
                    results["passed"] += 1
                else:
                    print_result("Get snapshot by ID", False, f"Status: {status}")
                    results["failed"] += 1

                # Delete snapshot
                status, _ = curl_request("DELETE", f"{API_BASE_URL}/api/v1/snapshots/{snapshot_id}")
                if status in (200, 204):
                    print_result("Delete snapshot", True)
                    results["passed"] += 1
                else:
                    print_result("Delete snapshot", False, f"Status: {status}")
                    results["failed"] += 1

    except Exception as e:
        print_result("Snapshots API", False, str(e))
        results["failed"] += 1
        results["errors"].append(f"Snapshots API: {e}")

    # 10. Suggestions API
    print_section("10. Suggestions API")
    suggestion_id = None

    try:
        if project_id:
            # List suggestions
            status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/suggestions?project_id={project_id}")
            if status == 200:
                suggestions = json.loads(body)
                print_result("List suggestions", True, f"Found {len(suggestions)} suggestions")
                results["passed"] += 1
            else:
                print_result("List suggestions", False, f"Status: {status}")
                results["failed"] += 1

            # Create a suggestion (use correct schema - target_type must be character/world_setting/chapter/scene)
            suggestion_data = {
                "project_id": str(project_id),
                "target_type": "chapter",
                "target_id": str(scene_chapter_id),
                "type": "content_gen",
                "content": {"suggested": "Suggested new chapter content"}
            }
            status, body = curl_request("POST", f"{API_BASE_URL}/api/v1/suggestions", suggestion_data)
            if status in (200, 201):
                suggestion = json.loads(body)
                suggestion_id = suggestion.get("id")
                print_result("Create suggestion", True, f"ID: {suggestion_id}")
                results["passed"] += 1
            else:
                print_result("Create suggestion", False, f"Status: {status}")
                results["failed"] += 1

            # Get suggestion by ID
            if suggestion_id:
                status, _ = curl_request("GET", f"{API_BASE_URL}/api/v1/suggestions/{suggestion_id}")
                if status == 200:
                    print_result("Get suggestion by ID", True)
                    results["passed"] += 1
                else:
                    print_result("Get suggestion by ID", False, f"Status: {status}")
                    results["failed"] += 1

                # Discard suggestion (action endpoint)
                action_data = {"action": "discard"}
                status, _ = curl_request("POST", f"{API_BASE_URL}/api/v1/suggestions/{suggestion_id}/action", action_data)
                if status == 200:
                    print_result("Discard suggestion", True)
                    results["passed"] += 1
                else:
                    print_result("Discard suggestion", False, f"Status: {status}")
                    results["failed"] += 1

    except Exception as e:
        print_result("Suggestions API", False, str(e))
        results["failed"] += 1
        results["errors"].append(f"Suggestions API: {e}")

    # 11. Dependencies API
    print_section("11. Dependencies API")
    dependency_id = None

    try:
        if project_id and character_id:
            # Query dependencies
            status, body = curl_request("GET", f"{API_BASE_URL}/api/v1/dependencies?project_id={project_id}")
            if status == 200:
                dependencies = json.loads(body)
                print_result("Query dependencies", True, f"Found {len(dependencies)} dependencies")
                results["passed"] += 1
            else:
                print_result("Query dependencies", False, f"Status: {status}")
                results["failed"] += 1

            # Create a dependency (chapter references character)
            dependency_data = {
                "project_id": str(project_id),
                "source_type": "chapter",
                "source_id": str(scene_chapter_id),
                "target_type": "character",
                "target_id": str(character_id),
                "dependency_type": "references"
            }
            status, body = curl_request("POST", f"{API_BASE_URL}/api/v1/dependencies", dependency_data)
            if status in (200, 201):
                dependency = json.loads(body)
                dependency_id = dependency.get("id")
                print_result("Create dependency", True, f"ID: {dependency_id}")
                results["passed"] += 1
            else:
                print_result("Create dependency", False, f"Status: {status}")
                results["failed"] += 1

            # Get dependency by ID
            if dependency_id:
                status, _ = curl_request("GET", f"{API_BASE_URL}/api/v1/dependencies/{dependency_id}")
                if status == 200:
                    print_result("Get dependency by ID", True)
                    results["passed"] += 1
                else:
                    print_result("Get dependency by ID", False, f"Status: {status}")
                    results["failed"] += 1

                # Delete dependency
                status, _ = curl_request("DELETE", f"{API_BASE_URL}/api/v1/dependencies/{dependency_id}")
                if status in (200, 204):
                    print_result("Delete dependency", True)
                    results["passed"] += 1
                else:
                    print_result("Delete dependency", False, f"Status: {status}")
                    results["failed"] += 1

    except Exception as e:
        print_result("Dependencies API", False, str(e))
        results["failed"] += 1
        results["errors"].append(f"Dependencies API: {e}")

    # Cleanup: Delete test project
    print_section("12. Cleanup")
    try:
        if project_id:
            status, _ = curl_request("DELETE", f"{API_BASE_URL}/api/v1/projects/{project_id}")
            if status in (200, 204):
                print_result("Delete test project", True)
                results["passed"] += 1
            else:
                print_result("Delete test project", False, f"Status: {status}")
                results["failed"] += 1
    except Exception as e:
        print_result("Cleanup", False, str(e))
        results["failed"] += 1

    return results


def main() -> int:
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
        results = verify_api()

        # Note: Server stderr/output is available but not displayed to keep test output clean

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
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user")
        sys.exit(130)
