from pathlib import Path

from app.schemas.base import SectionConfig, SectionName

DEFAULT_LAYOUT = [
    SectionConfig(name=SectionName.summary, enabled=True, ordering=0),
    SectionConfig(name=SectionName.jobs, enabled=True, ordering=1),
    SectionConfig(name=SectionName.education, enabled=True, ordering=2),
    SectionConfig(name=SectionName.projects, enabled=True, ordering=3),
    SectionConfig(name=SectionName.skills, enabled=True, ordering=4),
]

DEFAULT_USER_PROMPT = (
    Path(__file__).parent.parent / "templates" / "default_user_prompt.j2"
).read_text()
