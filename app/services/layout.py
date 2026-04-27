import logging
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models.base import UserLayout
from app.schemas.base import LayoutUpdateRequest, SectionConfig

logger = logging.getLogger(__name__)


async def get_user_layout(
    session: AsyncSession, user_id: uuid.UUID
) -> list[SectionConfig]:
    query = select(UserLayout).where(UserLayout.user_id == user_id)
    user_layout = (await session.scalars(query)).one_or_none()
    if not user_layout:
        logger.error("layout_lookup_failed", extra={"user_id": str(user_id)})
        raise ResourceNotFoundError(resource="layout", identifier=str(user_id))
    return [SectionConfig.model_validate(s) for s in user_layout.layout]


async def upsert_user_layout(
    session: AsyncSession, user_id: uuid.UUID, update: LayoutUpdateRequest
) -> list[SectionConfig]:
    layout_new = [s.model_dump() for s in update.layout]

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
