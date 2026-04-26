import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid_utils import uuid7

from app.core.defaults import DEFAULT_LAYOUT


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    email: Mapped[str] = mapped_column(unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class UserPrompt(Base):
    __tablename__ = "user_prompt"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), unique=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)


class UserLayout(Base):
    __tablename__ = "user_layout"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), unique=True
    )
    layout: Mapped[list] = mapped_column(
        JSON, default=lambda: [s.model_dump for s in DEFAULT_LAYOUT]
    )


class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), unique=True
    )
    personal_info: Mapped[dict | None] = mapped_column(JSON, default=None)
    jobs: Mapped[list | None] = mapped_column(JSON, default=None)
    education: Mapped[list | None] = mapped_column(JSON, default=None)
    projects: Mapped[list | None] = mapped_column(JSON, default=None)
    skills: Mapped[list | None] = mapped_column(JSON, default=None)


class Resume(Base):
    __tablename__ = "resume"
    __table_args__ = (UniqueConstraint("user_id", "filename", name="user_filename"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE")
    )
    filename: Mapped[str] = mapped_column(String(255))
    llm_input: Mapped[dict] = mapped_column(JSON)
    llm_output: Mapped[dict] = mapped_column(JSON)
    resume_data: Mapped[dict] = mapped_column(JSON)
    layout: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
