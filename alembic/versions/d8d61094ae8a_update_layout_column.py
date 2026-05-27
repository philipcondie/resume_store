"""Update layout column

Revision ID: d8d61094ae8a
Revises: 160f5aa89bf8
Create Date: 2026-05-22 17:06:11.198007

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import json

SIDEBAR_MAP = {
    "summary": "main",
    "jobs": "main",
    "education": "sidebar",
    "projects": "sidebar",
    "skills": "sidebar"
}
MULTIPANEL_MAP = {
    "summary": "main",
    "jobs": "main",
    "education": "left",
    "projects": "right",
    "skills": "main"
}

# revision identifiers, used by Alembic.
revision: str = 'd8d61094ae8a'
down_revision: Union[str, Sequence[str], None] = '160f5aa89bf8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def transform_layout(old: list) -> dict:
    """Pure function to transform old layout shape into new shape"""
    classic = [{**item, "panel": "main"} for item in old]
    sidebar = [{**item, "panel": SIDEBAR_MAP[item["name"]]} for item in old]
    multipanel = [{**item, "panel": MULTIPANEL_MAP[item["name"]]} for item in old]
    return {
        "selected_template": "classic",
        "templates": {
            "classic": {"sections":classic},
            "sidebar": {"sections": sidebar},
            "multipanel": {"sections": multipanel}
        }
    }
    
    


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    for row in conn.execute(sa.text("SELECT id, layout FROM user_layout")):
        if "templates" in row.layout:
            continue
        conn.execute(
            sa.text("UPDATE user_layout SET layout = :l WHERE id = :id"),
            {"l": json.dumps(transform_layout(row.layout)), "id": row.id},
        )

    for row in conn.execute(sa.text("SELECT id, layout FROM resume")):
        if "templates" in row.layout:
            continue
        conn.execute(
            sa.text("UPDATE resume SET layout = :l WHERE id = :id"),
            {"l": json.dumps(transform_layout(row.layout)), "id": row.id},
        )


def downgrade() -> None:
    """Downgrade schema."""
    pass
