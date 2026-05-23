import logging
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models.base import UserLayout
from app.schemas.base import LayoutConfig, LayoutUpdateRequest, ResumeStyling

logger = logging.getLogger(__name__)


async def get_user_layout(session: AsyncSession, user_id: uuid.UUID) -> LayoutConfig:
    query = select(UserLayout).where(UserLayout.user_id == user_id)
    user_layout = (await session.scalars(query)).one_or_none()
    if not user_layout:
        logger.error("layout_lookup_failed", extra={"user_id": str(user_id)})
        raise ResourceNotFoundError(resource="layout", identifier=str(user_id))
    return LayoutConfig.model_validate(user_layout)


async def upsert_user_layout(
    session: AsyncSession, user_id: uuid.UUID, update: LayoutUpdateRequest
) -> LayoutConfig:
    layout_new = update.layout.model_dump()

    stmt = (
        insert(UserLayout)
        .values(user_id=user_id, layout=layout_new)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={"layout": layout_new},
        )
    )
    await session.execute(stmt)
    await session.commit()

    logger.info(
        "layout_updated",
        extra={"user_id": str(user_id)},
    )
    return update.layout


async def get_user_styling(session: AsyncSession, user_id: uuid.UUID) -> ResumeStyling:
    query = select(UserLayout).where(UserLayout.user_id == user_id)
    user_layout = (await session.scalars(query)).one_or_none()
    if not user_layout:
        logger.error("styling_lookup_failed", extra={"user_id": str(user_id)})
        raise ResourceNotFoundError(resource="styling", identifier=str(user_id))
    return ResumeStyling.model_validate(user_layout.styling)


async def upsert_user_styling(
    session: AsyncSession, user_id: uuid.UUID, update: ResumeStyling
) -> ResumeStyling:
    stmt = (
        insert(UserLayout)
        .values(user_id=user_id, styling=update.model_dump())
        .on_conflict_do_update(
            index_elements=["user_id"], set_={"styling": update.model_dump()}
        )
    )
    await session.execute(stmt)
    await session.commit()

    logger.info("styling_updated", extra={"user_id": str(user_id)})
    return update
