from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    environment: str
    invite_code: str
    jwt_secret: str
    jwt_algorithm: str
    jwt_token_expires: int
    anthropic_api_key: str
    cors_origins: list[str]
    model_config = {"env_file": ".env"}
    max_concurrency_pdf: int = 2
    render_timeout: float = 10
    pdf_manager_timeout: float = 10
    refresh_token_expires: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
