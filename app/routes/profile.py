from fastapi import APIRouter, HTTPException

from app.core.dependencies import CurrentUserDep, SessionDep
from app.schemas.base import (
    EducationEntry,
    JobEntry,
    PersonalInfo,
    ProjectEntry,
    SkillEntry,
)
from app.services.user_data import (
    get_personal_info,
    get_profile_list,
    upsert_personal_info,
    upsert_profile_list,
)

profile_router = APIRouter(prefix="/profile", tags=["profile"])


@profile_router.get("/personal_info")
async def personal_info(
    session: SessionDep, current_user: CurrentUserDep
) -> PersonalInfo:
    try:
        result = await get_personal_info(session, current_user.id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@profile_router.post("/personal_info")
async def set_personal_info(
    session: SessionDep, current_user: CurrentUserDep, personal_info: PersonalInfo
) -> PersonalInfo:
    try:
        result = await upsert_personal_info(session, current_user.id, personal_info)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@profile_router.get("/jobs")
async def get_job_history(
    session: SessionDep, current_user: CurrentUserDep
) -> list[JobEntry]:
    return await get_profile_list(session, current_user.id, "job_history", JobEntry)


@profile_router.post("/jobs")
async def set_job_history(
    session: SessionDep, current_user: CurrentUserDep, job_history: list[JobEntry]
) -> list[JobEntry]:
    try:
        result = await upsert_profile_list(
            session, current_user.id, "job_history", job_history
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result


@profile_router.get("/education")
async def get_education_history(
    session: SessionDep, current_user: CurrentUserDep
) -> list[EducationEntry]:
    return await get_profile_list(
        session, current_user.id, "education_history", EducationEntry
    )


@profile_router.post("/education")
async def set_education_history(
    session: SessionDep,
    current_user: CurrentUserDep,
    education_history: list[EducationEntry],
) -> list[EducationEntry]:
    try:
        result = await upsert_profile_list(
            session, current_user.id, "education_history", education_history
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result


@profile_router.get("/projects")
async def get_project_history(
    session: SessionDep, current_user: CurrentUserDep
) -> list[ProjectEntry]:
    return await get_profile_list(
        session, current_user.id, "project_history", ProjectEntry
    )


@profile_router.post("/projects")
async def set_project_history(
    session: SessionDep,
    current_user: CurrentUserDep,
    project_history: list[ProjectEntry],
) -> list[ProjectEntry]:
    try:
        result = await upsert_profile_list(
            session, current_user.id, "project_history", project_history
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result


@profile_router.get("/skills")
async def get_skills(
    session: SessionDep, current_user: CurrentUserDep
) -> list[SkillEntry]:
    return await get_profile_list(session, current_user.id, "skills", SkillEntry)


@profile_router.post("/skills")
async def set_skills(
    session: SessionDep, current_user: CurrentUserDep, skills: list[SkillEntry]
) -> list[SkillEntry]:
    try:
        result = await upsert_profile_list(session, current_user.id, "skills", skills)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result
