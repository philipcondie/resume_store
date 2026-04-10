from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.models.base import User, UserPrompt
from app.schemas.base import LLMInput, LLMOutput, Token, UserCreate, UserPromptUpdate
from app.services.prompts import DEFAULT_USER_PROMPT
from app.services.resume import send_message
from app.services.user_data import upsert_user_prompt

settings = get_settings()
app = FastAPI()

SessionDep = Annotated[AsyncSession, Depends(get_session)]

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("DUMMY")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain: str, hash: str) -> bool:
    return password_hash.verify(plain, hash)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def authenticate_user(session: AsyncSession, email: str, password: str):
    result = await session.scalars(select(User).where(User.email == email))
    user = result.one_or_none()
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(
    session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    result = await session.scalars(select(User).where(User.email == username))
    user = result.one_or_none()
    if user is None:
        raise credentials_exception
    return user


@app.post("/create_user")
async def create_user(session: SessionDep, user: UserCreate):
    # hash password, then create user
    hashed_password = hash_password(user.password)
    result = await session.scalars(select(User).where(User.email == user.email))
    if result.one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user_new = User(email=user.email, hashed_password=hashed_password)
    session.add(user_new)
    await session.flush()
    session.add(UserPrompt(user_id=user_new.id, prompt=DEFAULT_USER_PROMPT))
    await session.commit()
    await session.refresh(user_new)
    return {"email": user.email}


@app.post("/login")
async def login(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.jwt_token_expires)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.post("/generate")
async def generate_resume(
    session: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
    input: LLMInput,
) -> LLMOutput:
    try:
        result = await send_message(session, current_user.id, input)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=502, detail="AI service unavailable")

    return result


@app.post("/prompt/update")
async def update_prompt(
    session: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
    prompt_update: UserPromptUpdate,
) -> UserPromptUpdate:
    try:
        result = await upsert_user_prompt(session, current_user.id, prompt_update)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result
