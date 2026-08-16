import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

filename_type = Annotated[
    str, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)
]
url_scheme_pattern = re.compile(r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*):")


class LinkableText(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    text: str
    url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_string(cls, value: object) -> object:
        if isinstance(value, str):
            return {"text": value, "url": None}
        return value

    @field_validator("url", mode="before")
    @classmethod
    def normalize_url(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("URL must be a string")

        normalized = value.strip()
        if not normalized:
            return None
        if any(character.isspace() for character in normalized):
            raise ValueError("URL cannot contain whitespace")
        if normalized.startswith("//"):
            raise ValueError("URL must not be scheme-relative")

        scheme_match = url_scheme_pattern.match(normalized)
        if scheme_match:
            original_scheme = scheme_match.group("scheme")
            scheme = original_scheme.lower()
            if scheme not in {"http", "https"}:
                raise ValueError("URL must use http or https")
            normalized = f"{scheme}{normalized[len(original_scheme) :]}"
        else:
            normalized = f"https://{normalized}"

        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("URL must use http or https and include a hostname")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("URL must not include credentials")
        if scheme_match is None and "." not in parsed.hostname:
            raise ValueError("URL without a scheme must include a dotted hostname")
        try:
            parsed.port
        except ValueError as error:
            raise ValueError("URL contains an invalid port") from error
        return normalized


class UserCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)
    email: str
    password: str
    invite_code: str


class UserCreateResponse(BaseModel):
    email: str


class RefreshRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    refresh_token: str


class Token(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    access_token: str
    token_type: str
    refresh_token: str


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
    description: str = ""
    website_url: str | None = None
    github_url: str | None = None
    bullets: list[str]

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_title(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        title = normalized.get("title")
        if isinstance(title, LinkableText):
            normalized["title"] = title.text
            if "websiteUrl" not in normalized and "website_url" not in normalized:
                normalized["websiteUrl"] = title.url
        elif isinstance(title, dict):
            normalized["title"] = title.get("text", "")
            if "websiteUrl" not in normalized and "website_url" not in normalized:
                normalized["websiteUrl"] = title.get("url")
        return normalized

    @field_validator("website_url", "github_url", mode="before")
    @classmethod
    def normalize_project_url(cls, value: object) -> str | None:
        return LinkableText(text="", url=value).url


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
    extras: list[LinkableText] | None = None


class LLMInput(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    job_description: str
    user_instructions: str
    jobs: list[JobEntry] = Field(min_length=1)


class LLMOutput(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    summary: str
    jobs: list[JobEntry]


class UserPromptUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    prompt: str


class SectionName(StrEnum):
    summary = "summary"
    jobs = "jobs"
    education = "education"
    projects = "projects"
    skills = "skills"


class Panel(StrEnum):
    main = "main"
    left = "left"
    right = "right"
    sidebar = "sidebar"


class TemplateName(StrEnum):
    classic = "classic"
    sidebar = "sidebar"
    multipanel = "multipanel"


class SectionConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    name: SectionName
    enabled: bool
    ordering: int = Field(ge=0)
    panel: Panel


class TemplateConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    sections: list[SectionConfig]


class Templates(BaseModel):
    classic: TemplateConfig
    sidebar: TemplateConfig
    multipanel: TemplateConfig


class LayoutConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    selected_template: TemplateName
    templates: Templates


class ResumeStyling(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    color_text_name: str
    color_accent: str
    font_main: list[str]


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


class ResumeUpdateRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    filename: filename_type
    resume_data: ResumeData
    layout: LayoutConfig
    job_description: str
    styling: ResumeStyling


class ResumeResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    filename: filename_type
    resume_data: ResumeData
    layout: LayoutConfig
    job_description: str
    styling: ResumeStyling


class ResumeDuplicateRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    filename: filename_type


class ResumeMetadata(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: uuid.UUID
    filename: filename_type
    created_at: datetime
    updated_at: datetime


class ResumeListResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    resumes: list[ResumeMetadata]
    resume_count: int


class LayoutUpdateRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    layout: LayoutConfig


@dataclass
class RenderedResume:
    filename: str
    pdf: bytes
    page_count: int
