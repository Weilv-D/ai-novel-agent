"""Single-user helpers for personal deployments."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_api_key
from app.models.user import User

PERSONAL_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


@dataclass(frozen=True)
class PersonalUser:
    """Current single-user identity for personal deployments."""

    id: UUID
    email: str
    name: str | None
    api_key_required: bool


def get_personal_user() -> PersonalUser:
    """Return the configured single-user identity."""
    settings = get_settings()
    name = settings.personal_user_name.strip() or None
    return PersonalUser(
        id=PERSONAL_USER_ID,
        email=settings.personal_user_email.strip().lower(),
        name=name,
        api_key_required=bool(settings.admin_api_key),
    )


async def ensure_personal_user(session: AsyncSession) -> User:
    """Create or update the single-user record used by the application."""
    settings = get_settings()
    identity = get_personal_user()
    result = await session.execute(select(User).where(User.id == identity.id))
    user = result.scalar_one_or_none()
    api_key_hash = hash_api_key(settings.admin_api_key) if settings.admin_api_key else None

    if user is None:
        user = User(
            id=identity.id,
            email=identity.email,
            name=identity.name,
            api_key_hash=api_key_hash,
            meta={"mode": "personal"},
        )
        session.add(user)
    else:
        user.email = identity.email
        user.name = identity.name
        user.api_key_hash = api_key_hash
        user.meta = {**(user.meta or {}), "mode": "personal"}

    await session.flush()
    await session.refresh(user)
    return user
