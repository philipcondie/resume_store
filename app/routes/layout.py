from fastapi import APIRouter, HTTPException

from app.core.dependencies import CurrentUserDep, SessionDep
from app.core.exceptions import ResourceNotFoundError
from app.schemas.base import UserLayoutUpdate
from app.services.layout import get_user_layout, upsert_user_layout

layout_router = APIRouter(prefix="/layout")


@layout_router.post("/update")
async def update_layout(
    session: SessionDep,
    current_user: CurrentUserDep,
    layout_update: UserLayoutUpdate,
) -> UserLayoutUpdate:
    try:
        result = await upsert_user_layout(session, current_user.id, layout_update)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@layout_router.get("")
async def get_layout(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserLayoutUpdate:
    try:
        result = await get_user_layout(session, current_user.id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result
