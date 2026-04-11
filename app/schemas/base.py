from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class UserCreate(BaseModel):
    email: str
    password: str


class UserCreateResponse(BaseModel):
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str


class JobEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)
    id: str
    company: str
    role: str
    start_date: str
    end_date: str
    location: str | None = None
    bullets: list[str]


class EducationEntry(BaseModel):
    id: str
    school: str
    degree: str
    bullets: list[str]


class ProjectEntry(BaseModel):
    id: str
    title: str
    bullets: list[str]


class SkillEntry(BaseModel):
    id: str
    title: str
    text: str


class PersonalInfo(BaseModel):
    name: str
    email: str
    phonenumber: str
    extras: list[str] | None = None


class LLMInput(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)
    job_description: str
    user_instructions: str
    jobs: list[JobEntry]


class LLMOutput(BaseModel):
    summary: str
    jobs: list[JobEntry]


class UserPromptUpdate(BaseModel):
    prompt: str
