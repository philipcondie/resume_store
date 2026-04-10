from anthropic import AsyncAnthropic

from app.core.config import get_settings

settings = get_settings()

client = AsyncAnthropic(api_key=settings.anthropic_api_key)
