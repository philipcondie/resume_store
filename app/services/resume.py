import logging
from pathlib import Path

from anthropic import APIError
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.claude import client
from app.models.base import UserPrompt
from app.schemas.base import LLMInput, LLMOutput
from app.services.prompt import DEFAULT_USER_PROMPT

logger = logging.getLogger(__name__)

prompt_template_dir = Path(__file__).parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(prompt_template_dir))
base_prompt_template = jinja_env.get_template("base_prompt.j2")
user_message_template = jinja_env.get_template("user_message.j2")


async def send_message(
    session: AsyncSession, user_id: int, input: LLMInput
) -> LLMOutput:
    # get base prompt
    base_prompt = base_prompt_template.render()

    # find user prompt based on user.id
    query = select(UserPrompt).where(UserPrompt.user_id == user_id)
    result = await session.scalars(query)
    user_prompt = result.one_or_none()
    if not user_prompt:
        logger.warning(
            "No user prompt record for user_id=%s; falling back to default prompt",
            user_id,
        )
    prompt_text = user_prompt.prompt if user_prompt else DEFAULT_USER_PROMPT
    system_prompt = base_prompt + "\n\n" + prompt_text

    user_message = user_message_template.render(input.model_dump())

    try:
        response = await client.messages.parse(
            model="claude-opus-4-6",
            max_tokens=5096,
            system=system_prompt,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": user_message}],
            output_config={"effort": "medium"},
            output_format=LLMOutput,
        )
    except APIError as e:
        raise RuntimeError("Anthropic API call failed") from e

    if not response.parsed_output:
        raise RuntimeError("Anthropic API response missing parsed output")
    return response.parsed_output
