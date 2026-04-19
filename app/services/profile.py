import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import UserProfile
from app.schemas.base import PersonalInfo

PROFILE_LIST_FIELDS = {"jobs", "education", "projects", "skills"}


async def _upsert_profile_field(
    session: AsyncSession, user_id: uuid.UUID, field: str, value: object
) -> UserProfile:
    """Upsert a single field on UserProfile. Returns the refreshed profile."""
    query = select(UserProfile).where(UserProfile.user_id == user_id)
    profile = (await session.scalars(query)).one_or_none()
    if not profile:
        profile = UserProfile(user_id=user_id, **{field: value})
    else:
        setattr(profile, field, value)
    session.add(profile)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise LookupError(f"No user found with id {user_id}")
    await session.refresh(profile)
    return profile


async def upsert_profile_list[T: BaseModel](
    session: AsyncSession, user_id: uuid.UUID, field: str, items: list[T]
) -> list[T]:
    if field not in PROFILE_LIST_FIELDS:
        raise ValueError(f"Invalid profile field: {field}")
    dumped = [item.model_dump(by_alias=True) for item in items]
    profile = await _upsert_profile_field(session, user_id, field, dumped)
    return [type(items[0]).model_validate(x) for x in getattr(profile, field) or []]


async def upsert_personal_info(
    session: AsyncSession, user_id: uuid.UUID, data: PersonalInfo
) -> PersonalInfo:
    profile = await _upsert_profile_field(
        session, user_id, "personal_info", data.model_dump(by_alias=True)
    )

    return PersonalInfo.model_validate(profile.personal_info)


async def _get_profile_field(
    session: AsyncSession, user_id: uuid.UUID
) -> UserProfile | None:
    query = select(UserProfile).where(UserProfile.user_id == user_id)
    profile = (await session.scalars(query)).one_or_none()
    return profile


async def get_profile_list[T: BaseModel](
    session: AsyncSession, user_id: uuid.UUID, field: str, model: type[T]
) -> list[T]:
    if field not in PROFILE_LIST_FIELDS:
        raise ValueError(f"Invalid profile field: {field}")
    profile = await _get_profile_field(session, user_id)
    if not profile:
        return []
    return [model.model_validate(x) for x in getattr(profile, field) or []]


async def get_personal_info(session: AsyncSession, user_id: uuid.UUID) -> PersonalInfo:
    profile = await _get_profile_field(session, user_id)
    if not profile or not profile.personal_info:
        raise LookupError(f"No personal info found for user {user_id}")
    return PersonalInfo.model_validate(profile.personal_info)
