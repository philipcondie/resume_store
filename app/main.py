from fastapi import FastAPI, HTTPException

from app.core.dependencies import CurrentUserDep, SessionDep
from app.routes.auth import auth_router
from app.routes.profile import profile_router
from app.routes.prompt import prompt_router
from app.schemas.base import LLMInput, LLMOutput
from app.services.resume import send_message

app = FastAPI()
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(prompt_router)


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
