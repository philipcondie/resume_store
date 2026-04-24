import uuid

from fastapi import APIRouter, HTTPException, status

import app.services.resume as resume
from app.core.dependencies import CurrentUserDep, SessionDep
from app.core.exceptions import (
    DuplicateFilenameError,
    IncompleteResumeInputError,
    ResourceNotFoundError,
)
from app.schemas.base import (
    ResumeData,
    ResumeDuplicateRequest,
    ResumeMetadata,
    ResumeRequest,
)

resume_router = APIRouter(prefix="/resume")


@resume_router.post("/new")
async def generate_resume(
    session: SessionDep, current_user: CurrentUserDep, request: ResumeRequest
) -> ResumeMetadata:
    try:
        result = await resume.generate_resume(
            session, current_user.id, request.filename, request.input
        )
    except DuplicateFilenameError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IncompleteResumeInputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
        )
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI service failed",
        )
    return result


@resume_router.get("")
async def get_resumes(
    session: SessionDep, current_user: CurrentUserDep
) -> list[ResumeMetadata]:
    return await resume.get_resume_list(session, current_user.id)


@resume_router.get("/{resume_id}")
async def get_resume(
    session: SessionDep, current_user: CurrentUserDep, resume_id: uuid.UUID
) -> ResumeData:
    try:
        result = await resume.get_resume(session, current_user.id, resume_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return result


@resume_router.put("/{resume_id}")
async def update_resume(
    session: SessionDep,
    current_user: CurrentUserDep,
    resume_id: uuid.UUID,
    data: ResumeData,
) -> ResumeData:
    try:
        result = await resume.update_resume(session, current_user.id, resume_id, data)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return result


@resume_router.delete("/{resume_id}")
async def delete_resume(
    session: SessionDep, current_user: CurrentUserDep, resume_id: uuid.UUID
) -> None:
    try:
        await resume.delete_resume(session, current_user.id, resume_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@resume_router.post("/{resume_id}/duplicate")
async def duplicate_resume(
    session: SessionDep,
    current_user: CurrentUserDep,
    resume_id: uuid.UUID,
    request: ResumeDuplicateRequest,
) -> ResumeMetadata:
    try:
        result = await resume.duplicate_resume(
            session, current_user.id, resume_id, request.filename
        )
    except DuplicateFilenameError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return result
