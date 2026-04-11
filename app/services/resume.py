import logging
from pathlib import Path

from anthropic import APIError
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.claude import client
from app.models.base import Resume, UserProfile, UserPrompt
from app.schemas.base import (
    EducationEntry,
    JobEntry,
    LLMInput,
    LLMOutput,
    PersonalInfo,
    ProjectEntry,
    ResumeData,
    ResumeMetadata,
    SkillEntry,
)
from app.services.prompt import DEFAULT_USER_PROMPT

logger = logging.getLogger(__name__)

prompt_template_dir = Path(__file__).parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(prompt_template_dir))
base_prompt_template = jinja_env.get_template("base_prompt.j2")
user_message_template = jinja_env.get_template("user_message.j2")


class DuplicateFilenameError(Exception):
    """Excpection for when a user tries to add a duplicate filename"""

    def __init__(self, filename):
        super().__init__(f"Filename ({filename}) already exists")


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


async def generate_resume(
    session: AsyncSession, user_id: int, filename: str, llm_input: LLMInput
) -> ResumeData:
    # validate filename
    query = select(Resume).where(Resume.user_id == user_id, Resume.filename == filename)
    result = (await session.scalars(query)).one_or_none()
    if result:
        raise DuplicateFilenameError(filename)

    # verify user exists and get profile data
    profile_query = select(UserProfile).where(UserProfile.user_id == user_id)
    profile = (await session.scalars(profile_query)).one_or_none()
    if not profile:
        raise LookupError(f"No profile found for user {user_id}")
    if not profile.personal_info:
        raise ValueError(f"No personal info found for user {user_id}")
    # get llm output
    llm_output = await send_message(session, user_id, llm_input)

    # create entry in Resume table
    resume_data = ResumeData(
        summary=llm_output.summary,
        personal_info=PersonalInfo.model_validate(profile.personal_info),
        job_history=[JobEntry.model_validate(j) for j in llm_output.jobs],
        education_history=[
            EducationEntry.model_validate(e) for e in profile.education_history or []
        ],
        project_history=[
            ProjectEntry.model_validate(p) for p in profile.project_history or []
        ],
        skills=[SkillEntry.model_validate(s) for s in profile.skills or []],
    )
    resume = Resume(
        user_id=user_id,
        filename=filename,
        llm_input=llm_input.model_dump(),
        llm_output=llm_output.model_dump(),
        resume_data=resume_data.model_dump(),
    )

    session.add(resume)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise DuplicateFilenameError(filename)
    await session.refresh(resume)
    return resume_data


async def get_resume_list(session: AsyncSession, user_id: int) -> list[ResumeMetadata]:
    query = select(
        Resume.id, Resume.filename, Resume.created_at, Resume.updated_at
    ).where(Resume.user_id == user_id)
    resumes = (await session.execute(query)).all()
    return [
        ResumeMetadata(
            id=r.id,
            filename=r.filename,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in resumes
    ]
