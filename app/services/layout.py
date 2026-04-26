import logging
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.defaults import DEFAULT_LAYOUT
from app.core.exceptions import ResourceNotFoundError
from app.models.base import UserLayout
from app.schemas.base import UserLayoutUpdate

logger = logging.getLogger(__name__)


async def get_user_layout(
    session: AsyncSession, user_id: uuid.UUID
) -> UserLayoutUpdate:
    query = select(UserLayout).where(UserLayout.user_id == user_id)
    user_layout = (await session.scalars(query)).one_or_none()
    if not user_layout:
        logger.warning("layout_lookup_failed", extra={"user_id": str(user_id)})
        raise ResourceNotFoundError(resource="layout", identifier=str(user_id))
    return UserLayoutUpdate(layout=user_layout.layout)


async def upsert_user_layout(
    session: AsyncSession, user_id: uuid.UUID, layout_update: UserLayoutUpdate
) -> UserLayoutUpdate:
    layout_new = (
        layout_update.layout if len(layout_update.layout) > 0 else DEFAULT_LAYOUT
    )

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
    used_default = not (len(layout_update.layout) == 0)
    logger.info(
        "layout_updated",
        extra={"user_id": str(user_id), "reset_to_default": used_default},
    )
    return UserLayoutUpdate(layout=layout_new)
