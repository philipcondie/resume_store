from pathlib import Path

DEFAULT_USER_PROMPT = (
    Path(__file__).parent.parent / "templates" / "default_user_prompt.j2"
).read_text()
