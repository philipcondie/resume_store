from fastapi import APIRouter, HTTPException

from app.core.dependencies import CurrentUserDep, SessionDep
from app.schemas.base import (
    EducationEntry,
    JobEntry,
    PersonalInfo,
    ProjectEntry,
    SkillEntry,
)
from app.services.profile import (
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
async def get_jobs(session: SessionDep, current_user: CurrentUserDep) -> list[JobEntry]:
    return await get_profile_list(session, current_user.id, "jobs", JobEntry)


@profile_router.post("/jobs")
async def set_jobs(
    session: SessionDep, current_user: CurrentUserDep, jobs: list[JobEntry]
) -> list[JobEntry]:
    try:
        result = await upsert_profile_list(session, current_user.id, "jobs", jobs)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result


@profile_router.get("/education")
async def get_education(
    session: SessionDep, current_user: CurrentUserDep
) -> list[EducationEntry]:
    return await get_profile_list(session, current_user.id, "education", EducationEntry)


@profile_router.post("/education")
async def set_education(
    session: SessionDep,
    current_user: CurrentUserDep,
    education: list[EducationEntry],
) -> list[EducationEntry]:
    try:
        result = await upsert_profile_list(
            session, current_user.id, "education", education
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result


@profile_router.get("/projects")
async def get_projects(
    session: SessionDep, current_user: CurrentUserDep
) -> list[ProjectEntry]:
    return await get_profile_list(session, current_user.id, "projects", ProjectEntry)


@profile_router.post("/projects")
async def set_project(
    session: SessionDep,
    current_user: CurrentUserDep,
    projects: list[ProjectEntry],
) -> list[ProjectEntry]:
    try:
        result = await upsert_profile_list(
            session, current_user.id, "projects", projects
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
