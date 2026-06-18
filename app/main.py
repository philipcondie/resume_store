from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.render import PDFManager
from app.routes.auth import auth_router
from app.routes.health import health_router
from app.routes.layout import layout_router
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = PDFManager(settings.max_concurrency_pdf)
    await manager.start()
    app.state.pdf_manager = manager
    yield
    await app.state.pdf_manager.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=methods,
    allow_headers=["*"],
    expose_headers=["x-resume-page-count", "content-disposition"],
)

app.add_middleware(CorrelationIdMiddleware)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(prompt_router)
app.include_router(resume_router)
app.include_router(health_router)
app.include_router(layout_router)
