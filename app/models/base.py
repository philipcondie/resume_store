from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class UserPrompt(Base):
    __tablename__ = "user_prompt"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), unique=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)


class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), unique=True
    )
    personal_info: Mapped[dict | None] = mapped_column(JSON, default=None)
    job_history: Mapped[list | None] = mapped_column(JSON, default=None)
    education_history: Mapped[list | None] = mapped_column(JSON, default=None)
    project_history: Mapped[list | None] = mapped_column(JSON, default=None)
    skills: Mapped[list | None] = mapped_column(JSON, default=None)
