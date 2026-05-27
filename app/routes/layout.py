from fastapi import APIRouter, HTTPException

from app.core.dependencies import CurrentUserDep, SessionDep
from app.core.exceptions import ResourceNotFoundError
from app.schemas.base import LayoutConfig, LayoutUpdateRequest, ResumeStyling
from app.services.layout import (
    get_user_layout,
    get_user_styling,
    upsert_user_layout,
    upsert_user_styling,
)

layout_router = APIRouter(prefix="/layout")


@layout_router.post("/update")
async def update_layout(
    session: SessionDep,
    current_user: CurrentUserDep,
    layout_update: LayoutUpdateRequest,
) -> LayoutConfig:
    try:
        result = await upsert_user_layout(session, current_user.id, layout_update)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@layout_router.get("")
async def get_layout(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> LayoutConfig:
    try:
        result = await get_user_layout(session, current_user.id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@layout_router.get("/styling")
async def get_styling(
    session: SessionDep, current_user: CurrentUserDep
) -> ResumeStyling:
    try:
        result = await get_user_styling(session, current_user.id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@layout_router.post("/styling/update")
async def update_styling(
    session: SessionDep, current_user: CurrentUserDep, update: ResumeStyling
) -> ResumeStyling:
    try:
        result = await upsert_user_styling(session, current_user.id, update)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result
