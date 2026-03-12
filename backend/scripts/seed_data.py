#!/usr/bin/env python3
"""Seed development data for testing."""

import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_maker
from app.models import Character, Project, User, WorldSetting


async def create_test_user(session: AsyncSession) -> User:
    """Create a test user."""
    result = await session.execute(select(User).where(User.email == "test@example.com"))
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    user = User(
        email="test@example.com",
        name="Test User",
        api_key_hash="test_hash",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_test_project(session: AsyncSession, user_id: str) -> Project:
    """Create a test project."""
    project = Project(
        user_id=user_id,
        name="Test Novel",
        genre="Fantasy",
        target_audience="Young Adult",
        target_word_count=80000,
        summary="A test fantasy novel",
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def create_test_characters(session: AsyncSession, project_id: str) -> list[Character]:
    """Create test characters."""
    characters = [
        Character(
            project_id=project_id,
            name="Hero",
            role="protagonist",
            profile={"personality": "brave", "appearance": "tall"},
        ),
        Character(
            project_id=project_id,
            name="Villain",
            role="antagonist",
            profile={"personality": "cunning", "appearance": "dark"},
        ),
    ]
    for char in characters:
        session.add(char)
    await session.commit()
    return characters


async def create_test_world_settings(session: AsyncSession, project_id: str) -> list[WorldSetting]:
    """Create test world settings."""
    settings = [
        WorldSetting(
            project_id=project_id,
            category="magic_system",
            name="Mana Magic",
            content="Magic powered by mana energy",
        ),
        WorldSetting(
            project_id=project_id,
            category="geography",
            name="The Kingdom",
            content="A prosperous kingdom",
        ),
    ]
    for setting in settings:
        session.add(setting)
    await session.commit()
    return settings


async def main() -> None:
    """Main seeding function."""
    async with async_session_maker() as session:
        print("Creating test data...")

        user = await create_test_user(session)
        print(f"Created user: {user.email}")

        project = await create_test_project(session, str(user.id))
        print(f"Created project: {project.name}")

        characters = await create_test_characters(session, str(project.id))
        print(f"Created {len(characters)} characters")

        world_settings = await create_test_world_settings(session, str(project.id))
        print(f"Created {len(world_settings)} world settings")

        print("Seed data created successfully!")


if __name__ == "__main__":
    asyncio.run(main())
