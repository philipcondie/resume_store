from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import UserProfile, UserPrompt
from app.schemas.base import PersonalInfo, UserPromptUpdate
from app.services.prompts import DEFAULT_USER_PROMPT

PROFILE_LIST_FIELDS = {"job_history", "education_history", "project_history", "skills"}


async def get_user_prompt(session: AsyncSession, user_id: int) -> UserPromptUpdate:
    query = select(UserPrompt).where(UserPrompt.user_id == user_id)
    user_prompt = (await session.scalars(query)).one_or_none()
    if not user_prompt:
        raise LookupError(f"No prompt found for user {user_id}")
    return UserPromptUpdate(prompt=user_prompt.prompt)


async def upsert_user_prompt(
    session: AsyncSession, user_id: int, prompt_update: UserPromptUpdate
) -> UserPromptUpdate:
    # get prompt. If no text is included then use to default prompt
    prompt_new = prompt_update.prompt.strip() or DEFAULT_USER_PROMPT

    query = select(UserPrompt).where(UserPrompt.user_id == user_id)
    existing = (await session.scalars(query)).one_or_none()
    if not existing:
        user_prompt = UserPrompt(user_id=user_id, prompt=prompt_new)
    else:
        user_prompt = existing
        user_prompt.prompt = prompt_new
    session.add(user_prompt)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise LookupError(f"No user found with id {user_id}")
    await session.refresh(user_prompt)

    return UserPromptUpdate(prompt=user_prompt.prompt)


async def _upsert_profile_field(
    session: AsyncSession, user_id: int, field: str, value: object
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
    session: AsyncSession, user_id: int, field: str, items: list[T]
) -> list[T]:
    if field not in PROFILE_LIST_FIELDS:
        raise ValueError(f"Invalid profile field: {field}")
    dumped = [item.model_dump() for item in items]
    profile = await _upsert_profile_field(session, user_id, field, dumped)
    return [type(items[0]).model_validate(x) for x in getattr(profile, field) or []]


async def upsert_personal_info(
    session: AsyncSession, user_id: int, data: PersonalInfo
) -> PersonalInfo:
    profile = await _upsert_profile_field(
        session, user_id, "personal_info", data.model_dump()
    )

    return PersonalInfo.model_validate(profile.personal_info)


async def _get_profile_field(session: AsyncSession, user_id: int) -> UserProfile | None:
    query = select(UserProfile).where(UserProfile.user_id == user_id)
    profile = (await session.scalars(query)).one_or_none()
    return profile


async def get_profile_list[T: BaseModel](
    session: AsyncSession, user_id: int, field: str, model: type[T]
) -> list[T]:
    if field not in PROFILE_LIST_FIELDS:
        raise ValueError(f"Invalid profile field: {field}")
    profile = await _get_profile_field(session, user_id)
    if not profile:
        return []
    return [model.model_validate(x) for x in getattr(profile, field) or []]


async def get_personal_info(session: AsyncSession, user_id: int) -> PersonalInfo:
    profile = await _get_profile_field(session, user_id)
    if not profile or not profile.personal_info:
        raise LookupError(f"No personal info found for user {user_id}")
    return PersonalInfo.model_validate(profile.personal_info)
