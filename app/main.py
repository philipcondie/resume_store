from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.routes.auth import auth_router
from app.routes.health import health_router
from app.routes.profile import profile_router
from app.routes.prompt import prompt_router
from app.routes.resume import resume_router

settings = get_settings()
origins = settings.cors_origins
methods = (
    ["*"] if settings.environment.lower() == "dev" else ["GET", "PUT", "POST", "DELETE"]
)

log_level = "DEBUG" if settings.environment.lower() == "dev" else "INFO"
configure_logging(level=log_level)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=methods,
    allow_headers=["*"],
)

app.add_middleware(CorrelationIdMiddleware)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(prompt_router)
app.include_router(resume_router)
app.include_router(health_router)
