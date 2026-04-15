from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel

filename_type = Annotated[
    str, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)
]


class UserCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)
    email: str
    password: str
    invite_code: str


class UserCreateResponse(BaseModel):
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str


class JobEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    company: str
    role: str
    start_date: str
    end_date: str
    location: str | None = None
    bullets: list[str]


class EducationEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    school: str
    degree: str
    bullets: list[str]


class ProjectEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    title: str
    bullets: list[str]


class SkillEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    title: str
    text: str


class PersonalInfo(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    name: str
    email: str
    phonenumber: str
    extras: list[str] | None = None


class LLMInput(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    job_description: str
    user_instructions: str
    jobs: list[JobEntry]


class LLMOutput(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    summary: str
    jobs: list[JobEntry]


class UserPromptUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    prompt: str


class ResumeData(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    personal_info: PersonalInfo | None
    summary: str | None
    jobs: list[JobEntry] | None
    education: list[EducationEntry] | None
    projects: list[ProjectEntry] | None
    skills: list[SkillEntry] | None


class ResumeRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    filename: filename_type
    input: LLMInput


class ResumeMetadata(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    filename: filename_type
    created_at: datetime
    updated_at: datetime
