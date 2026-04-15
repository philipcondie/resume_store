"""update profile columns

Revision ID: e6aacd589321
Revises: c730c6c86290
Create Date: 2026-04-14 19:04:25.583086

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e6aacd589321'
down_revision: Union[str, Sequence[str], None] = 'c730c6c86290'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('user_profile', 'project_history', new_column_name='projects')
    op.alter_column('user_profile', 'job_history', new_column_name='jobs')
    op.alter_column('user_profile', 'education_history', new_column_name='education')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('user_profile', 'projects', new_column_name='project_history')
    op.alter_column('user_profile', 'education', new_column_name="education_history")
    op.alter_column('user_profile', 'jobs', new_column_name='job_history')
    # ### end Alembic commands ###
