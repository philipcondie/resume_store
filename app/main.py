from fastapi import FastAPI, HTTPException

from app.core.config import get_settings
from app.core.dependencies import CurrentUserDep, SessionDep
from app.routes.auth import auth_router
from app.routes.profile import profile_router
from app.schemas.base import LLMInput, LLMOutput, UserPromptUpdate
from app.services.resume import send_message
from app.services.user_data import get_user_prompt, upsert_user_prompt

settings = get_settings()
app = FastAPI()
app.include_router(auth_router)
app.include_router(profile_router)


@app.post("/generate")
async def generate_resume(
    session: SessionDep,
    current_user: CurrentUserDep,
    input: LLMInput,
) -> LLMOutput:
    try:
        result = await send_message(session, current_user.id, input)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="AI service unavailable")

    return result


@app.post("/prompt/update")
async def update_prompt(
    session: SessionDep,
    current_user: CurrentUserDep,
    prompt_update: UserPromptUpdate,
) -> UserPromptUpdate:
    try:
        result = await upsert_user_prompt(session, current_user.id, prompt_update)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@app.get("/prompt")
async def get_prompt(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserPromptUpdate:
    try:
        result = await get_user_prompt(session, current_user.id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result
