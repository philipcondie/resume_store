import logging
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.defaults import DEFAULT_USER_PROMPT
from app.models.base import User, UserLayout, UserPrompt
from app.schemas.base import Token, UserCreate

settings = get_settings()
password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("DUMMY")

logger = logging.getLogger(__name__)


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


async def create_user(session: AsyncSession, user: UserCreate) -> Token:
    # check if the user gave the new user code
    if user.invite_code != settings.invite_code:
        logger.warning("user_create_failed", extra={"reason": "invite_code_invalid"})
        raise ValueError("Incorrect code")
    # hash password, then create user
    hashed_password = hash_password(user.password)
    result = await session.scalars(select(User).where(User.email == user.email))
    if result.one_or_none():
        logger.warning("user_create_failed", extra={"reason": "duplicate_email"})
        raise LookupError("Email already registered")

    user_new = User(email=user.email, hashed_password=hashed_password)
    session.add(user_new)
    await session.flush()

    session.add(UserPrompt(user_id=user_new.id, prompt=DEFAULT_USER_PROMPT))
    session.add(UserLayout(user_id=user_new.id))
    await session.commit()
    await session.refresh(user_new)

    access_token_expires = timedelta(minutes=settings.jwt_token_expires)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info("user_created", extra={"user_id": str(user_new.id)})
    return Token(access_token=access_token, token_type="bearer")


async def login(session: AsyncSession, email: str, password: str) -> Token:
    user = await authenticate_user(session, email, password)
    if not user:
        logger.warning("user_login_failed", extra={"reason": "credentials_invalid"})
        raise LookupError("Incorrect username or password")
    access_token_expires = timedelta(minutes=settings.jwt_token_expires)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info("user_authenticated", extra={"user_id": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")
