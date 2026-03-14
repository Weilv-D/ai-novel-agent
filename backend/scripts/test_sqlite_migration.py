#!/usr/bin/env python3
"""SQLite migration compatibility test.

This script verifies that Alembic migrations work correctly with SQLite,
ensuring the dialect-aware changes (UUID, JSON, timestamp defaults) are
properly handled for both PostgreSQL and SQLite.

Run with: DATABASE_URL="sqlite+aiosqlite:///test.db" python scripts/test_sqlite_migration.py
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


def test_sqlite_migration():
    """Test that Alembic migrations work with SQLite."""
    # Clear settings cache to pick up DATABASE_URL
    get_settings.cache_clear()

    # Create a temporary SQLite database
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        # Configure DATABASE_URL for SQLite
        os.environ['DATABASE_URL'] = f'sqlite+aiosqlite:///{db_path}'
        get_settings.cache_clear()

        # Configure Alembic
        alembic_cfg = Config()
        alembic_cfg.set_main_option('sqlalchemy.url', f'sqlite+aiosqlite:///{db_path}')
        alembic_cfg.set_main_option(
            'script_location',
            str(Path(__file__).parent.parent / 'alembic')
        )

        print('Running Alembic migration with SQLite...')
        command.upgrade(alembic_cfg, 'head')
        print('✓ Migration completed successfully')

        # Verify we can insert data without explicit timestamps
        async def verify_data_insert():
            engine = create_async_engine(f'sqlite+aiosqlite:///{db_path}', echo=False)
            async with engine.begin() as conn:
                # Insert a user without explicit created_at/updated_at
                # This tests that CURRENT_TIMESTAMP default works
                await conn.execute(text("""
                    INSERT INTO users (id, email)
                    VALUES ('123e4567-e89b-12d3-a456-426614174000', 'test@example.com')
                """))

                # Verify timestamps were auto-generated
                result = await conn.execute(text("""
                    SELECT created_at, updated_at FROM users WHERE email = 'test@example.com'
                """))
                row = result.fetchone()

                if row[0] is None or row[1] is None:
                    print('✗ FAILED: Timestamps are NULL (CURRENT_TIMESTAMP not working)')
                    return False

                print(f'✓ Data insert works: created_at={row[0]}, updated_at={row[1]}')

                # Verify JSON column works
                await conn.execute(text("""
                    UPDATE users SET metadata = '{"key": "value"}' WHERE email = 'test@example.com'
                """))
                result = await conn.execute(text("""
                    SELECT metadata FROM users WHERE email = 'test@example.com'
                """))
                row = result.fetchone()
                print(f'✓ JSON column works: metadata={row[0]}')

                return True

            await engine.dispose()

        import asyncio
        success = asyncio.run(verify_data_insert())

        if success:
            print('\n✅ All SQLite compatibility tests passed!')
            return 0
        else:
            print('\n❌ SQLite compatibility test failed')
            return 1

    except Exception as e:
        print(f'\n❌ Error: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == '__main__':
    sys.exit(test_sqlite_migration())
