from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routes.auth import auth_router
from app.routes.profile import profile_router
from app.routes.prompt import prompt_router
from app.routes.resume import resume_router

settings = get_settings()
origins = settings.cors_origins
methods = ["*"] if settings.environment == "dev" else ["GET", "PUT", "POST", "DELETE"]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=methods,
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(prompt_router)
app.include_router(resume_router)
