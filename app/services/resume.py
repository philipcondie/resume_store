import logging
import uuid
from pathlib import Path

from anthropic import APIError
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.claude import client
from app.core.defaults import DEFAULT_USER_PROMPT
from app.core.exceptions import (
    DuplicateFilenameError,
    IncompleteResumeInputError,
    ResourceNotFoundError,
)
from app.models.base import Resume, UserLayout, UserProfile, UserPrompt
from app.schemas.base import (
    EducationEntry,
    JobEntry,
    LayoutUpdateRequest,
    LLMInput,
    LLMOutput,
    PersonalInfo,
    ProjectEntry,
    ResumeData,
    ResumeMetadata,
    ResumeResponse,
    SkillEntry,
)

logger = logging.getLogger(__name__)

prompt_template_dir = Path(__file__).parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(prompt_template_dir))
base_prompt_template = jinja_env.get_template("base_prompt.j2")
user_message_template = jinja_env.get_template("user_message.j2")


async def send_message(
    session: AsyncSession, user_id: uuid.UUID, input: LLMInput
) -> LLMOutput:
    # get base prompt
    base_prompt = base_prompt_template.render()

    # find user prompt based on user.id
    query = select(UserPrompt).where(UserPrompt.user_id == user_id)
    result = await session.scalars(query)
    user_prompt = result.one_or_none()
    if not user_prompt:
        logger.warning(
            "user_prompt_missing",
            extra={"user_id": str(user_id)},
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
    except APIError:
        logger.exception("anthropic_api_error", extra={"user_id": str(user_id)})
        raise RuntimeError("Anthropic API call failed")

    if not response.parsed_output:
        logger.error(
            "parsed_output_missing",
            extra={"user_id": str(user_id), "response_id": str(response.id)},
        )
        raise RuntimeError("Anthropic API response missing parsed output")
    logger.info(
        "anthropic_api_succeeded",
        extra={
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    )
    return response.parsed_output


async def generate_resume(
    session: AsyncSession, user_id: uuid.UUID, filename: str, llm_input: LLMInput
) -> ResumeMetadata:
    # validate filename
    query = select(Resume).where(Resume.user_id == user_id, Resume.filename == filename)
    result = (await session.scalars(query)).one_or_none()
    if result:
        logger.warning(
            "resume_generation_failed",
            extra={
                "user_id": str(user_id),
                "file_name": filename,
                "reason": "duplicate_filename",
            },
        )
        raise DuplicateFilenameError(filename)

    # verify user exists and get profile data
    profile_query = select(UserProfile).where(UserProfile.user_id == user_id)
    profile = (await session.scalars(profile_query)).one_or_none()
    if not profile or not profile.personal_info:
        logger.warning(
            "resume_input_incomplete",
            extra={"user_id": str(user_id), "input": "personal_info"},
        )
        raise IncompleteResumeInputError(identifier=str(user_id), input="personal_info")

    # get llm output
    llm_output = await send_message(session, user_id, llm_input)

    # create entry in Resume table
    resume_data = ResumeData(
        summary=llm_output.summary,
        personal_info=PersonalInfo.model_validate(profile.personal_info),
        jobs=[JobEntry.model_validate(j) for j in llm_output.jobs],
        education=[EducationEntry.model_validate(e) for e in profile.education or []],
        projects=[ProjectEntry.model_validate(p) for p in profile.projects or []],
        skills=[SkillEntry.model_validate(s) for s in profile.skills or []],
    )

    # get layout
    layout_query = select(UserLayout).where(UserLayout.user_id == user_id)
    user_layout = (await session.scalars(layout_query)).one_or_none()
    if not user_layout:
        logger.error("layout_lookup_failed", extra={"user_id": str(user_id)})
        raise ResourceNotFoundError(resource="layout", identifier=str(user_id))
    layout = user_layout.layout

    resume = Resume(
        user_id=user_id,
        filename=filename,
        llm_input=llm_input.model_dump(by_alias=True),
        llm_output=llm_output.model_dump(by_alias=True),
        resume_data=resume_data.model_dump(by_alias=True),
        layout=layout,
    )

    session.add(resume)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.warning(
            "resume_generation_failed",
            extra={
                "user_id": str(user_id),
                "file_name": filename,
                "reason": "duplicate_filename",
            },
        )
        raise DuplicateFilenameError(filename)
    await session.refresh(resume)
    logger.info(
        "resume_generated",
        extra={
            "user_id": str(user_id),
            "file_name": filename,
            "resume_id": str(resume.id),
        },
    )
    return ResumeMetadata(
        id=resume.id,
        filename=resume.filename,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )


async def get_resume_list(
    session: AsyncSession, user_id: uuid.UUID
) -> list[ResumeMetadata]:
    query = select(
        Resume.id, Resume.filename, Resume.created_at, Resume.updated_at
    ).where(Resume.user_id == user_id)
    resumes = (await session.execute(query)).all()
    logger.info(
        "resumes_listed", extra={"user_id": str(user_id), "count": len(resumes)}
    )
    return [
        ResumeMetadata(
            id=r.id,
            filename=r.filename,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in resumes
    ]


async def get_resume(
    session: AsyncSession, user_id: uuid.UUID, resume_id: uuid.UUID
) -> ResumeResponse:
    query = select(Resume).where(Resume.user_id == user_id, Resume.id == resume_id)
    resume = (await session.execute(query)).scalar_one_or_none()
    if not resume:
        logger.warning(
            "resume_get_failed",
            extra={
                "user_id": str(user_id),
                "resume_id": str(resume_id),
                "reason": "resume_not_found",
            },
        )
        raise ResourceNotFoundError(resource="resume", identifier=str(resume_id))
    logger.info(
        "resume_retrieved", extra={"user_id": str(user_id), "resume_id": str(resume_id)}
    )
    return ResumeResponse(
        filename=resume.filename, resume_data=resume.resume_data, layout=resume.layout
    )


async def update_resume(
    session: AsyncSession, user_id: uuid.UUID, resume_id: uuid.UUID, data: ResumeData
) -> ResumeResponse:
    query = select(Resume).where(Resume.user_id == user_id, Resume.id == resume_id)
    resume = (await session.scalars(query)).one_or_none()
    if not resume:
        logger.warning(
            "resume_update_failed",
            extra={
                "user_id": str(user_id),
                "resume_id": str(resume_id),
                "reason": "resume_not_found",
            },
        )
        raise ResourceNotFoundError(resource="resume", identifier=str(resume_id))
    resume.resume_data = data.model_dump(by_alias=True)
    await session.commit()
    await session.refresh(resume)
    logger.info(
        "resume_data_updated",
        extra={"user_id": str(user_id), "resume_id": str(resume_id)},
    )
    return ResumeResponse(
        filename=resume.filename, resume_data=resume.resume_data, layout=resume.layout
    )


async def update_resume_layout(
    session: AsyncSession,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
    update: LayoutUpdateRequest,
) -> ResumeResponse:
    query = select(Resume).where(Resume.user_id == user_id, Resume.id == resume_id)
    resume = (await session.scalars(query)).one_or_none()
    if not resume:
        logger.warning(
            "resume_update_failed",
            extra={
                "user_id": str(user_id),
                "resume_id": str(resume_id),
                "reason": "resume_not_found",
            },
        )
        raise ResourceNotFoundError(resource="resume", identifier=str(resume_id))
    resume.layout = [s.model_dump() for s in update.layout]
    await session.commit()
    await session.refresh(resume)
    logger.info(
        "resume_layout_updated",
        extra={"user_id": str(user_id), "resume_id": str(resume_id)},
    )
    return ResumeResponse(
        filename=resume.filename, resume_data=resume.resume_data, layout=resume.layout
    )


async def delete_resume(
    session: AsyncSession, user_id: uuid.UUID, resume_id: uuid.UUID
) -> None:
    query = select(Resume).where(Resume.user_id == user_id, Resume.id == resume_id)
    resume = (await session.scalars(query)).one_or_none()
    if not resume:
        logger.warning(
            "resume_delete_failed",
            extra={
                "user_id": str(user_id),
                "resume_id": str(resume_id),
                "reason": "resume_not_found",
            },
        )
        raise ResourceNotFoundError(resource="resume", identifier=str(resume_id))
    await session.delete(resume)
    await session.commit()
    logger.info(
        "resume_deleted",
        extra={"user_id": str(user_id), "resume_id": str(resume_id)},
    )


async def duplicate_resume(
    session: AsyncSession, user_id: uuid.UUID, resume_id: uuid.UUID, filename: str
) -> ResumeMetadata:
    query = select(Resume).where(Resume.user_id == user_id, Resume.id == resume_id)
    source = (await session.scalars(query)).one_or_none()
    if not source:
        logger.warning(
            "resume_duplicate_failed",
            extra={
                "user_id": str(user_id),
                "resume_id": str(resume_id),
                "reason": "resume_not_found",
            },
        )
        raise ResourceNotFoundError(resource="resume", identifier=str(resume_id))
    new_resume = Resume(
        user_id=user_id,
        filename=filename,
        llm_input=source.llm_input,
        llm_output=source.llm_output,
        resume_data=source.resume_data,
        layout=source.layout,
    )
    session.add(new_resume)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.warning(
            "resume_duplicate_failed",
            extra={
                "user_id": str(user_id),
                "resume_id": str(resume_id),
                "reason": "duplicate_filename",
            },
        )
        raise DuplicateFilenameError(filename)
    await session.refresh(new_resume)
    logger.info(
        "resume_duplicated",
        extra={
            "user_id": str(user_id),
            "resume_id": str(new_resume.id),
            "file_name": new_resume.filename,
        },
    )
    return ResumeMetadata(
        id=new_resume.id,
        filename=new_resume.filename,
        created_at=new_resume.created_at,
        updated_at=new_resume.updated_at,
    )
