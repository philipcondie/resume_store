from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.dependencies import CurrentUserDep, SessionDep
from app.schemas.base import Token, UserCreate
from app.services import auth as auth_service

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/signup")
async def create_user(session: SessionDep, user: UserCreate) -> Token:
    try:
        result = await auth_service.create_user(session, user)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return result


@auth_router.post("/login")
async def login(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    try:
        result = await auth_service.login(
            session, form_data.username, form_data.password
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result


@auth_router.post("/logout")
async def logout(session: SessionDep, current_user: CurrentUserDep):
    await auth_service.logout(session, current_user.id)


@auth_router.post("/refresh")
async def refresh(
    session: SessionDep,
    current_user: CurrentUserDep,
    refresh_token: Annotated[str, Body(alias="refreshToken")],
) -> Token:
    token = await auth_service.refresh_access_token(
        session, current_user.id, refresh_token
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed refresh request",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
