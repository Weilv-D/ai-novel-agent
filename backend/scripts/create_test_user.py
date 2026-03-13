#!/usr/bin/env python3
"""Create a test user for integration testing."""

import asyncio
import sys
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.user import User


async def create_test_user(db_path: str) -> None:
    """Create a test user in the database."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with maker() as session:
        result = await session.execute(
            select(User).where(User.email == "test@example.com")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("Test user already exists")
            return

        test_user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            email="test@example.com",
            name="Test User",
            meta={}
        )
        session.add(test_user)
        await session.commit()
        print("Test user created")

    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "test_integration.db"

    asyncio.run(create_test_user(db_path))
