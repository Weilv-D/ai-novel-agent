#!/usr/bin/env python3
"""
API Integration Verification Script (DRAFT - UNVERIFIED)

Tests all API endpoints to ensure they work correctly.
Run this after starting the backend server to verify the integration.

NOTE: This script is currently UNVERIFIED and contains KNOWN ISSUES:
- Field names may not match actual backend schemas
  - Project: script uses 'title/description' but backend expects 'name'
  - Scene: script uses 'scene_number' but backend expects 'scene_order'
  - Character: script uses 'description/personality' but backend uses 'profile' dict
- Requires manual verification and fixes before use

TODO: Fix field names to match backend schemas, then run against live backend.
"""

import sys
import httpx
from typing import Any
import json

API_BASE_URL = "http://localhost:8000"
VERBOSE = True


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
                print_result("List projects", True, f"Found {data.get('total', 0)} projects")
                results["passed"] += 1
            else:
                print_result("List projects", False, f"Status: {response.status_code}")
                results["failed"] += 1

            # Create a project
            project_data = {
                "title": "Integration Test Project",
                "description": "A project for API integration testing",
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
                update_data = {"description": "Updated description"}
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
                response = await client.get(f"{API_BASE_URL}/api/v1/projects/{project_id}/characters")
                if response.status_code == 200:
                    characters = response.json()
                    print_result("List characters", True, f"Found {len(characters)} characters")
                    results["passed"] += 1
                else:
                    print_result("List characters", False, f"Status: {response.status_code}")
                    results["failed"] += 1

                # Create a character
                character_data = {
                    "name": "Test Character",
                    "description": "A test character for API integration testing",
                    "personality": "Brave and curious"
                }
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/projects/{project_id}/characters",
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
                    response = await client.get(f"{API_BASE_URL}/api/v1/projects/{project_id}/characters/{character_id}")
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
                response = await client.get(f"{API_BASE_URL}/api/v1/projects/{project_id}/chapters")
                if response.status_code == 200:
                    chapters = response.json()
                    print_result("List chapters", True, f"Found {len(chapters)} chapters")
                    results["passed"] += 1
                else:
                    print_result("List chapters", False, f"Status: {response.status_code}")
                    results["failed"] += 1

                # Create a chapter
                chapter_data = {
                    "title": "Test Chapter",
                    "content": "This is test content for API integration testing.",
                    "chapter_number": 1,
                    "status": "draft"
                }
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/projects/{project_id}/chapters",
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
                response = await client.get(f"{API_BASE_URL}/api/v1/chapters/{chapter_id}/scenes")
                if response.status_code == 200:
                    scenes = response.json()
                    print_result("List scenes", True, f"Found {len(scenes)} scenes")
                    results["passed"] += 1
                else:
                    print_result("List scenes", False, f"Status: {response.status_code}")
                    results["failed"] += 1

                # Create a scene
                scene_data = {
                    "title": "Test Scene",
                    "content": "This is test scene content for API integration testing.",
                    "scene_number": 1
                }
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/chapters/{chapter_id}/scenes",
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
                response = await client.get(f"{API_BASE_URL}/api/v1/projects/{project_id}/world-settings")
                if response.status_code == 200:
                    settings = response.json()
                    print_result("List world settings", True, f"Found {len(settings)} settings")
                    results["passed"] += 1
                else:
                    print_result("List world settings", False, f"Status: {response.status_code}")
                    results["failed"] += 1

                # Create a world setting
                setting_data = {
                    "name": "Test Setting",
                    "description": "A test world setting for API integration testing.",
                    "category": "location"
                }
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/projects/{project_id}/world-settings",
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
    print_section("AI Novel Agent - API Integration Verification")
    print(f"API Base URL: {API_BASE_URL}")
    print("Make sure the backend server is running before running this script.")

    results = await verify_api()

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
        print(f"\n  Some tests failed. Please check the backend server and database connection.")
        return 1
    else:
        print(f"\n  All tests passed! The API is working correctly.")
        return 0


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
