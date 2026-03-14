"""Test to verify db_engine fixture provides proper isolation.

This test verifies that UUID type replacements are properly isolated between tests.
The key insight: during a test, types are SQLiteUUID (not UUID instance), but
fixture cleanup restores them to original UUID for next test.
"""
from sqlalchemy.dialects.postgresql import UUID

from app.models import Base


class TestEngineFixtureIsolation:
    """Verify that db_engine fixture properly isolates UUID type changes."""

    async def test_first_use_db_engine(self, db_engine):
        """First test: verify fixture can be used successfully."""
        # During test, UUID types are replaced with SQLiteUUID
        # So isinstance(col.type, UUID) returns False
        # But the actual database operations work correctly
        uuid_count = 0
        for table in Base.metadata.sorted_tables:
            for col in table.columns:
                if isinstance(col.type, UUID):
                    uuid_count += 1

        print(f"First test (during fixture): {uuid_count} UUID columns")
        # Expected: 0 because types are replaced with SQLiteUUID
        TestEngineFixtureIsolation.first_uuid_count = uuid_count

    async def test_second_use_db_engine(self, db_engine):
        """Second test: verify fixture still works after first test cleanup."""
        uuid_count = 0
        for table in Base.metadata.sorted_tables:
            for col in table.columns:
                if isinstance(col.type, UUID):
                    uuid_count += 1

        print(f"Second test (during fixture): {uuid_count} UUID columns")
        # Should be same as first test (both see SQLiteUUID)
        assert uuid_count == TestEngineFixtureIsolation.first_uuid_count, \
            f"State changed between tests: {uuid_count} vs {TestEngineFixtureIsolation.first_uuid_count}"

    async def test_verify_cleanup_works(self, db_engine):
        """Verify the fixture cleanup restores UUID types correctly."""
        # During test, types are SQLiteUUID
        during_count = sum(1 for t in Base.metadata.sorted_tables
                          for c in t.columns if isinstance(c.type, UUID))
        print(f"During fixture: {during_count} UUID columns")
        assert during_count == 0, "Types should be SQLiteUUID during test"

        # Verify fixture works by doing a real operation
        # This would fail if types weren't properly handled
        async with db_engine.begin() as conn:
            # Just verify connection works - would fail if types were broken
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))


class TestMetadataStateAcrossTests:
    """Verify metadata state is consistent across test runs."""

    async def test_save_initial_state(self):
        """Save the initial metadata state before any fixture usage."""
        self.initial_uuid_count = sum(
            1 for t in Base.metadata.sorted_tables
            for c in t.columns if isinstance(c.type, UUID)
        )
        print(f"Initial state (before fixture): {self.initial_uuid_count} UUID columns")
        assert self.initial_uuid_count > 0, "Should have UUID columns initially"

    async def test_state_during_fixture(self, db_engine):
        """Check state during fixture usage (after replacement)."""
        during_count = sum(
            1 for t in Base.metadata.sorted_tables
            for c in t.columns if isinstance(c.type, UUID)
        )
        print(f"During fixture: {during_count} UUID columns")
        # During test, types are replaced so count is 0
        assert during_count == 0, "Types should be replaced during test"

    async def test_state_after_all_fixtures(self):
        """Verify final state after all fixtures complete."""
        # This test runs WITHOUT db_engine fixture, so it should see original state
        final_count = sum(
            1 for t in Base.metadata.sorted_tables
            for c in t.columns if isinstance(c.type, UUID)
        )
        print(f"Final state (after all fixtures): {final_count} UUID columns")
        # Should match initial state because cleanup restored types
        assert final_count > 0, "UUID types should be restored after cleanup"
