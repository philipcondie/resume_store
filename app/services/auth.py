import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.defaults import DEFAULT_USER_PROMPT
from app.core.exceptions import InvalidRefreshTokenError, UserNotFoundError
from app.models.base import RefreshToken, User, UserLayout, UserPrompt
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


def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)


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
    refresh_token = create_refresh_token()
    await upsert_refresh_token(
        session=session,
        user_id=user_new.id,
        refresh_token=refresh_token,
        expires_delta=timedelta(days=settings.refresh_token_expires),
        commit=False,
    )
    await session.commit()
    await session.refresh(user_new)

    access_token_expires = timedelta(minutes=settings.jwt_token_expires)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info("user_created", extra={"user_id": str(user_new.id)})
    return Token(
        access_token=access_token, token_type="bearer", refresh_token=refresh_token
    )


async def upsert_refresh_token(
    session: AsyncSession,
    user_id: uuid.UUID,
    refresh_token: str,
    expires_delta: timedelta | None = None,
    commit: bool = True,
):
    hashed_token = hashlib.sha256(refresh_token.encode()).hexdigest()
    created_at = datetime.now(UTC)
    if expires_delta:
        expires_at = datetime.now(UTC) + expires_delta
    else:
        expires_at = datetime.now(UTC) + timedelta(days=30)
    stmt = (
        insert(RefreshToken)
        .values(
            user_id=user_id,
            hashed_token=hashed_token,
            created_at=created_at,
            expires_at=expires_at,
        )
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "hashed_token": hashed_token,
                "created_at": created_at,
                "expires_at": expires_at,
            },
        )
    )

    await session.execute(stmt)
    if commit:
        await session.commit()
    logger.info("refresh_token_updated", extra={"user_id": str(user_id)})


async def get_user_by_refresh_token(session: AsyncSession, refresh_token: str) -> bool:
    hashed_token = hashlib.sha256(refresh_token.encode()).hexdigest()

    row = await session.scalars(
        select(RefreshToken).where(RefreshToken.hashed_token == hashed_token)
    )
    result = row.one_or_none()
    if not result:
        return False

    if datetime.now(UTC) > result.expires_at:
        return False

    return True


async def login(session: AsyncSession, email: str, password: str) -> Token:
    user = await authenticate_user(session, email, password)
    if not user:
        logger.warning("user_login_failed", extra={"reason": "credentials_invalid"})
        raise LookupError("Incorrect username or password")

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.jwt_token_expires),
    )
    logger.info("user_authenticated", extra={"user_id": str(user.id)})

    refresh_token = create_refresh_token()
    await upsert_refresh_token(
        session=session,
        user_id=user.id,
        refresh_token=refresh_token,
        expires_delta=timedelta(days=settings.refresh_token_expires),
    )
    return Token(
        access_token=access_token, token_type="bearer", refresh_token=refresh_token
    )


async def logout(session: AsyncSession, user_id: uuid.UUID):
    query = select(RefreshToken).where(RefreshToken.user_id == user_id)
    row = (await session.scalars(query)).one_or_none()
    if not row:
        logger.warning(
            "refresh_token_missing",
            extra={
                "user_id": str(user_id),
            },
        )
    else:
        await session.delete(row)
        await session.commit()
    logger.info("user_logged_out", extra={"user_id": str(user_id)})


async def refresh_access_token(
    session: AsyncSession, refresh_token: str
) -> Token | None:
    hashed_token = hashlib.sha256(refresh_token.encode()).hexdigest()

    token_row = await session.scalars(
        select(RefreshToken).where(RefreshToken.hashed_token == hashed_token)
    )
    token = token_row.one_or_none()
    if not token:
        logger.error(
            "refresh_access_token_failed", extra={"reason": "refresh_token_not_found"}
        )
        raise InvalidRefreshTokenError()

    if datetime.now(UTC) > token.expires_at:
        logger.error(
            "refresh_access_token_failed", extra={"reason": "refresh_token_expired"}
        )
        raise InvalidRefreshTokenError()

    user_row = await session.scalars(select(User).where(User.id == token.user_id))
    user = user_row.one_or_none()

    if not user:
        logger.error("refresh_access_token_failed", extra={"reason": "user_not_found"})
        raise UserNotFoundError()

    new_refresh_token = create_refresh_token()
    await upsert_refresh_token(
        session=session,
        user_id=user.id,
        refresh_token=new_refresh_token,
        expires_delta=timedelta(days=settings.refresh_token_expires),
    )
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.jwt_token_expires),
    )

    logger.info("access_token_refreshed", extra={"user_id": str(user.id)})
    return Token(
        access_token=access_token, token_type="bearer", refresh_token=new_refresh_token
    )
