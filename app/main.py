from fastapi import FastAPI

from app.routes.auth import auth_router
from app.routes.profile import profile_router
from app.routes.prompt import prompt_router
from app.routes.resume import resume_router

app = FastAPI()
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(prompt_router)
app.include_router(resume_router)
