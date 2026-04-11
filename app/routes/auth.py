from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.dependencies import SessionDep
from app.schemas.base import Token, UserCreate, UserCreateResponse
from app.services import auth as auth_service

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/create_user")
async def create_user(session: SessionDep, user: UserCreate) -> UserCreateResponse:
    try:
        result = await auth_service.create_user(session, user)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
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
