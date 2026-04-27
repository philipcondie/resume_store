from fastapi import APIRouter, HTTPException

from app.core.dependencies import CurrentUserDep, SessionDep
from app.core.exceptions import ResourceNotFoundError
from app.schemas.base import UserPromptUpdate
from app.services.prompt import get_user_prompt, upsert_user_prompt

prompt_router = APIRouter(prefix="/prompt")


@prompt_router.post("/update")
async def update_prompt(
    session: SessionDep,
    current_user: CurrentUserDep,
    prompt_update: UserPromptUpdate,
) -> UserPromptUpdate:
    try:
        result = await upsert_user_prompt(session, current_user.id, prompt_update)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@prompt_router.get("")
async def get_prompt(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserPromptUpdate:
    try:
        result = await get_user_prompt(session, current_user.id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result
