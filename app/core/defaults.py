from pathlib import Path

from app.schemas.base import (
    LayoutConfig,
    Panel,
    ResumeStyling,
    SectionConfig,
    SectionName,
    TemplateConfig,
    TemplateName,
    Templates,
)

DEFAULT_CLASSIC_LAYOUT = TemplateConfig(
    sections=[
        SectionConfig(
            name=SectionName.summary, enabled=True, ordering=0, panel=Panel.main
        ),
        SectionConfig(
            name=SectionName.jobs, enabled=True, ordering=1, panel=Panel.main
        ),
        SectionConfig(
            name=SectionName.education, enabled=True, ordering=2, panel=Panel.main
        ),
        SectionConfig(
            name=SectionName.projects, enabled=True, ordering=3, panel=Panel.main
        ),
        SectionConfig(
            name=SectionName.skills, enabled=True, ordering=4, panel=Panel.main
        ),
    ]
)

DEFAULT_SIDEBAR_LAYOUT = TemplateConfig(
    sections=[
        SectionConfig(
            name=SectionName.summary, enabled=True, ordering=0, panel=Panel.main
        ),
        SectionConfig(
            name=SectionName.jobs, enabled=True, ordering=1, panel=Panel.main
        ),
        SectionConfig(
            name=SectionName.education, enabled=True, ordering=2, panel=Panel.sidebar
        ),
        SectionConfig(
            name=SectionName.projects, enabled=True, ordering=3, panel=Panel.sidebar
        ),
        SectionConfig(
            name=SectionName.skills, enabled=True, ordering=4, panel=Panel.sidebar
        ),
    ]
)

DEFAULT_MULTIPANEL_LAYOUT = TemplateConfig(
    sections=[
        SectionConfig(
            name=SectionName.summary, enabled=True, ordering=0, panel=Panel.main
        ),
        SectionConfig(
            name=SectionName.jobs, enabled=True, ordering=1, panel=Panel.main
        ),
        SectionConfig(
            name=SectionName.education, enabled=True, ordering=2, panel=Panel.left
        ),
        SectionConfig(
            name=SectionName.projects, enabled=True, ordering=3, panel=Panel.right
        ),
        SectionConfig(
            name=SectionName.skills, enabled=True, ordering=4, panel=Panel.main
        ),
    ]
)

DEFAULT_TEMPLATES = Templates(
    classic=DEFAULT_CLASSIC_LAYOUT,
    sidebar=DEFAULT_SIDEBAR_LAYOUT,
    multipanel=DEFAULT_MULTIPANEL_LAYOUT,
)

DEFAULT_LAYOUT = LayoutConfig(
    selected_template=TemplateName.classic, templates=DEFAULT_TEMPLATES
)

DEFAULT_USER_PROMPT = (
    Path(__file__).parent.parent / "templates" / "default_user_prompt.j2"
).read_text()

DEFAULT_STYLING = ResumeStyling(
    color_text_name="#1A5C71",
    color_accent="#2A7F9E",
    font_main=["Open Sans", "Helvetica Neue", "Arial", "sans-serif"],
)
