from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class UserCreate(BaseModel):
    email: str
    password: str


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
    location: str
    bullets: list[str]


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
