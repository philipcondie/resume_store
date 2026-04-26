import logging
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.defaults import DEFAULT_USER_PROMPT
from app.core.exceptions import ResourceNotFoundError
from app.models.base import UserPrompt
from app.schemas.base import UserPromptUpdate

logger = logging.getLogger(__name__)


async def get_user_prompt(
    session: AsyncSession, user_id: uuid.UUID
) -> UserPromptUpdate:
    query = select(UserPrompt).where(UserPrompt.user_id == user_id)
    user_prompt = (await session.scalars(query)).one_or_none()
    if not user_prompt:
        logger.warning(
            "prompt_lookup_failed",
            extra={"user_id": str(user_id), "reason": "prompt_not_found"},
        )
        raise ResourceNotFoundError(resource="prompt", identifier=user_id)
    return UserPromptUpdate(prompt=user_prompt.prompt)


async def upsert_user_prompt(
    session: AsyncSession, user_id: uuid.UUID, prompt_update: UserPromptUpdate
) -> UserPromptUpdate:
    # get prompt. If no text is included then use to default prompt
    prompt_new = prompt_update.prompt.strip() or DEFAULT_USER_PROMPT

    stmt = (
        insert(UserPrompt)
        .values(user_id=user_id, prompt=prompt_new)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={"prompt": prompt_new},
        )
    )
    await session.execute(stmt)
    await session.commit()
    used_default = not prompt_update.prompt.strip()
    logger.info(
        "prompt_updated",
        extra={"user_id": str(user_id), "reset_to_default": used_default},
    )
    return UserPromptUpdate(prompt=prompt_new)
