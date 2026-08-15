import logging
import uuid
from pathlib import Path

from anthropic import APIError
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.claude import client
from app.core.defaults import DEFAULT_USER_PROMPT
from app.core.exceptions import (
    DuplicateFilenameError,
    IncompleteResumeInputError,
    PDFGenerationError,
    PDFReaderError,
    PDFRendererConfigurationError,
    PDFRenderError,
    PDFRenderTimeoutError,
    RenderCapacityError,
    ResourceNotFoundError,
)
from app.core.render import RESUME_ASSET_BASE_URL, PDFManager, PDFResult
from app.models.base import Resume, UserLayout, UserProfile, UserPrompt
from app.schemas.base import (
    EducationEntry,
    JobEntry,
    LayoutConfig,
    LayoutUpdateRequest,
    LLMInput,
    LLMOutput,
    Panel,
    PersonalInfo,
    ProjectEntry,
    RenderedResume,
    ResumeData,
    ResumeListResponse,
    ResumeMetadata,
    ResumeResponse,
    ResumeStyling,
    ResumeUpdateRequest,
    SectionConfig,
    SectionName,
    SkillEntry,
    TemplateName,
)

logger = logging.getLogger(__name__)

prompt_template_dir = Path(__file__).parent.parent / "templates"
resume_template_dir = Path(__file__).parent.parent / "templates/resume_templates"
prompt_env = Environment(loader=FileSystemLoader(prompt_template_dir))
resume_env = Environment(loader=FileSystemLoader(resume_template_dir))

base_prompt_template = prompt_env.get_template("base_prompt.j2")
user_message_template = prompt_env.get_template("user_message.j2")


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

    resume = Resume(
        user_id=user_id,
        filename=filename,
        llm_input=llm_input.model_dump(by_alias=True),
        llm_output=llm_output.model_dump(by_alias=True),
        resume_data=resume_data.model_dump(by_alias=True),
        layout=user_layout.layout,
        styling=user_layout.styling,
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
    session: AsyncSession, user_id: uuid.UUID, offset: int, limit: int
) -> ResumeListResponse:
    query = (
        select(Resume.id, Resume.filename, Resume.created_at, Resume.updated_at)
        .where(Resume.user_id == user_id)
        .order_by(Resume.filename, Resume.created_at)
        .offset(offset)
        .limit(limit)
    )
    resumes = (await session.execute(query)).all()
    logger.info(
        "resumes_listed", extra={"user_id": str(user_id), "count": len(resumes)}
    )
    resumes = [
        ResumeMetadata(
            id=r.id,
            filename=r.filename,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in resumes
    ]
    resume_count = (
        await session.execute(
            select(func.count()).select_from(Resume).where(Resume.user_id == user_id)
        )
    ).scalar_one()
    logger.info(
        "resumes_available", extra={"user_id": str(user_id), "count": resume_count}
    )
    return ResumeListResponse(resume_count=resume_count, resumes=resumes)


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

    job_desc = LLMInput.model_validate(resume.llm_input).job_description
    return ResumeResponse(
        filename=resume.filename,
        resume_data=ResumeData.model_validate(resume.resume_data),
        layout=LayoutConfig.model_validate(resume.layout),
        job_description=job_desc,
        styling=ResumeStyling.model_validate(resume.styling),
    )


async def update_resume(
    session: AsyncSession,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
    data: ResumeUpdateRequest,
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

    for key, value in data.model_dump().items():
        setattr(resume, key, value)

    await session.commit()
    await session.refresh(resume)
    logger.info(
        "resume_data_updated",
        extra={"user_id": str(user_id), "resume_id": str(resume_id)},
    )
    job_desc = LLMInput.model_validate(resume.llm_input).job_description
    return ResumeResponse(
        filename=resume.filename,
        resume_data=ResumeData.model_validate(resume.resume_data),
        layout=LayoutConfig.model_validate(resume.layout),
        job_description=job_desc,
        styling=ResumeStyling.model_validate(resume.styling),
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
    resume.layout = update.layout.model_dump()
    await session.commit()
    await session.refresh(resume)
    logger.info(
        "resume_layout_updated",
        extra={"user_id": str(user_id), "resume_id": str(resume_id)},
    )
    job_desc = LLMInput.model_validate(resume.llm_input).job_description
    return ResumeResponse(
        filename=resume.filename,
        resume_data=ResumeData.model_validate(resume.resume_data),
        layout=LayoutConfig.model_validate(resume.layout),
        job_description=job_desc,
        styling=ResumeStyling.model_validate(resume.styling),
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
        styling=source.styling,
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


TEMPLATE_REGISTRY: dict[TemplateName, tuple[str, list[Panel]]] = {
    TemplateName.classic: ("classic_layout.html.j2", [Panel.main]),
    TemplateName.sidebar: ("sidebar_layout.html.j2", [Panel.main, Panel.sidebar]),
    TemplateName.multipanel: (
        "multipanel_layout.html.j2",
        [Panel.main, Panel.left, Panel.right],
    ),
}


def verify_section(resume_data: ResumeData, section_name: SectionName) -> bool:
    section_data = getattr(resume_data, section_name, None)
    if section_data and (section_name != SectionName.summary or section_data.strip()):
        return True
    return False


def create_html_string(source_resume: Resume) -> str:
    resume_layout = LayoutConfig.model_validate(source_resume.layout)
    resume_data = ResumeData.model_validate(source_resume.resume_data)
    resume_styling = ResumeStyling.model_validate(source_resume.styling)
    sections: list[SectionConfig] = getattr(
        resume_layout.templates, resume_layout.selected_template.value
    ).sections
    sections.sort(key=lambda x: x.ordering)

    def panel(p: Panel) -> list[SectionConfig]:
        return [
            s
            for s in sections
            if s.enabled and s.panel == p and verify_section(resume_data, s.name)
        ]

    filename, panels = TEMPLATE_REGISTRY[resume_layout.selected_template]
    panels_data = {p.value + "_sections": panel(p) for p in panels}
    return resume_env.get_template(filename).render(
        **panels_data,
        **(resume_styling).model_dump(),
        resume_data=resume_data,
        asset_base_url=RESUME_ASSET_BASE_URL,
    )


async def render_resume_playwright(
    session: AsyncSession,
    pdf_manager: PDFManager,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
) -> RenderedResume:
    query = select(Resume).where(Resume.user_id == user_id, Resume.id == resume_id)
    source = (await session.scalars(query)).one_or_none()
    if not source:
        logger.warning(
            "render_resume_failed",
            extra={
                "user_id": str(user_id),
                "resume_id": str(resume_id),
                "reason": "resume_not_found",
            },
        )
        raise ResourceNotFoundError(resource="resume", identifier=str(resume_id))

    html_string = create_html_string(source_resume=source)

    try:
        result: PDFResult = await pdf_manager.create_pdf(html_string)
    except PDFRendererConfigurationError:
        logger.error(
            "pdf_render_not_configured",
            extra={
                "user_id": str(user_id),
                "resume_id": str(source.id),
                "file_name": source.filename,
            },
        )
        raise
    except RenderCapacityError:
        logger.error(
            "pdf_renderer_acquisition_timed_out",
            extra={
                "user_id": str(user_id),
                "resume_id": str(source.id),
                "file_name": source.filename,
            },
        )
        raise
    except PDFReaderError:
        logger.error(
            "pdf_reader_failed",
            extra={
                "user_id": str(user_id),
                "resume_id": str(source.id),
                "file_name": source.filename,
            },
        )
        raise
    except PDFRenderTimeoutError:
        logger.error(
            "pdf_render_timed_out",
            extra={
                "user_id": str(user_id),
                "resume_id": str(source.id),
                "file_name": source.filename,
            },
        )
        raise
    except PDFRenderError:
        logger.error(
            "pdf_render_failed",
            extra={
                "user_id": str(user_id),
                "resume_id": str(source.id),
                "file_name": source.filename,
            },
        )
        raise PDFGenerationError(filename=source.filename)

    if result.pages > 1:
        logger.info(
            "pdf_length_exceeds_1",
            extra={
                "user_id": str(user_id),
                "resume_id": str(resume_id),
                "length": result.pages,
            },
        )

    logger.info(
        "resume_pdf_downloaded",
        extra={
            "user_id": str(user_id),
            "resume_id": str(source.id),
            "file_name": source.filename,
        },
    )
    return RenderedResume(
        filename=source.filename, pdf=result.pdf, page_count=result.pages
    )
