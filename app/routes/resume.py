from fastapi import APIRouter, HTTPException, status

import app.services.resume as resume
from app.core.dependencies import CurrentUserDep, SessionDep
from app.schemas.base import ResumeData, ResumeRequest

resume_router = APIRouter(prefix="/resume")


@resume_router.post("/new")
async def generate_resume(
    session: SessionDep, current_user: CurrentUserDep, request: ResumeRequest
) -> ResumeData:
    try:
        result = await resume.generate_resume(
            session, current_user.id, request.filename, request.input
        )
    except resume.DuplicateFilenameError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI service failed",
        )
    return result


# get resume list
# get resume
