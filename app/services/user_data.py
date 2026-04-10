from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import UserPrompt
from app.schemas.base import UserPromptUpdate
from app.services.prompts import DEFAULT_USER_PROMPT


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
