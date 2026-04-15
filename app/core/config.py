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


@lru_cache
def get_settings() -> Settings:
    return Settings()
